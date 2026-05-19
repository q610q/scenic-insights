"""Dashboard endpoints — 全部走物化视图，<50ms。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_get_or_set
from app.config import settings
from app.deps import get_db
from app.schemas.dashboard import CityKPI, GlobalKPI, MonthlyTrend
from app.schemas.spot import HeatmapPoint, LevelDist, SpotMetric

router = APIRouter(prefix="/dashboard", tags=["大屏"])


# -----------------------------------------------------------------------------
# 1. 全局 KPI（首页 4 张卡片）
# -----------------------------------------------------------------------------
@router.get("/global-kpi", response_model=GlobalKPI, summary="全局 KPI（4 张卡片）")
async def global_kpi(db: AsyncSession = Depends(get_db)) -> GlobalKPI:
    async def _query():
        # 用 fact_comment 真实计数（不再 SUM dim 字段累加，避免跨 schema 重复夸大）
        row = (
            await db.execute(
                text("""
                    SELECT
                        (SELECT COUNT(*) FROM dim_scenic_spot)        AS spot_total,
                        (SELECT COUNT(*) FROM fact_comment)           AS real_comment_total,
                        (SELECT AVG(grade)::NUMERIC(3,2) FROM dim_scenic_spot
                            WHERE grade IS NOT NULL)                  AS avg_grade,
                        (SELECT COUNT(DISTINCT city) FROM dim_scenic_spot
                            WHERE city IS NOT NULL AND city <> '')    AS city_count
                """)
            )
        ).one()
        return dict(row._mapping)

    return await cache_get_or_set(
        "dashboard:global-kpi", _query, settings.CACHE_DASHBOARD_TTL
    )


# -----------------------------------------------------------------------------
# 2. 城市 KPI 列表
# -----------------------------------------------------------------------------
@router.get("/city-kpi", response_model=list[CityKPI], summary="城市维度 KPI")
async def city_kpi(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=200),
) -> list[CityKPI]:
    async def _query():
        rows = await db.execute(
            text("""
                SELECT city, province, spot_count, avg_grade,
                       total_real_comments, hot_spot_count
                FROM mv_city_summary
                WHERE city <> '未分类'
                ORDER BY total_real_comments DESC NULLS LAST
                LIMIT :n
            """),
            {"n": limit},
        )
        return [dict(r._mapping) for r in rows]

    return await cache_get_or_set(
        f"dashboard:city-kpi:{limit}", _query, settings.CACHE_DASHBOARD_TTL
    )


# -----------------------------------------------------------------------------
# 3. Top N 景区
# -----------------------------------------------------------------------------
@router.get("/spots/top", response_model=list[SpotMetric], summary="Top N 景区")
async def top_spots(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("comment_count_real", pattern="^(comment_count_real|grade|hot|avg_co_grade)$"),
) -> list[SpotMetric]:
    async def _query():
        rows = await db.execute(
            text(f"""
                SELECT id, name, city, level, tag, grade, hot,
                       comment_count_real, avg_co_grade,
                       grade_5_count, grade_4_count, grade_3_count,
                       grade_2_count, grade_1_count,
                       lon, lat
                FROM mv_spot_metrics
                ORDER BY {sort} DESC NULLS LAST
                LIMIT :n
            """),
            {"n": limit},
        )
        return [dict(r._mapping) for r in rows]

    return await cache_get_or_set(
        f"dashboard:top:{sort}:{limit}", _query, settings.CACHE_DASHBOARD_TTL
    )


# -----------------------------------------------------------------------------
# 4. 中国地图散点（ECharts 格式）
# -----------------------------------------------------------------------------
@router.get("/heatmap", response_model=list[HeatmapPoint], summary="地图散点 / 热力")
async def heatmap(db: AsyncSession = Depends(get_db)) -> list[HeatmapPoint]:
    async def _query():
        rows = await db.execute(
            text("""
                SELECT name, lon, lat, comment_count_real, grade
                FROM mv_spot_metrics
                WHERE lon IS NOT NULL AND lat IS NOT NULL
            """)
        )
        return [
            {
                "name": r.name,
                "value": [
                    r.lon, r.lat,
                    r.comment_count_real or 0,
                    float(r.grade) if r.grade else 0.0,
                ],
            }
            for r in rows
        ]

    return await cache_get_or_set(
        "dashboard:heatmap", _query, settings.CACHE_HEATMAP_TTL
    )


# -----------------------------------------------------------------------------
# 5. 等级分布饼图
# -----------------------------------------------------------------------------
@router.get("/level-dist", response_model=list[LevelDist], summary="景区等级分布")
async def level_dist(db: AsyncSession = Depends(get_db)) -> list[LevelDist]:
    async def _query():
        rows = await db.execute(
            text("""
                SELECT level, spot_count, total_comments, avg_grade
                FROM mv_level_dist
                ORDER BY level
            """)
        )
        return [dict(r._mapping) for r in rows]

    return await cache_get_or_set(
        "dashboard:level-dist", _query, settings.CACHE_DASHBOARD_TTL
    )


# -----------------------------------------------------------------------------
# 6. 月度评论趋势（某景区）
# -----------------------------------------------------------------------------
@router.get(
    "/spots/{spot_id}/monthly",
    response_model=list[MonthlyTrend],
    summary="某景区月度评论趋势",
)
async def monthly_trend(
    spot_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[MonthlyTrend]:
    rows = await db.execute(
        text("""
            SELECT ym, cnt, avg_grade
            FROM mv_comment_monthly
            WHERE spot_id = :sid
            ORDER BY ym
        """),
        {"sid": spot_id},
    )
    return [dict(r._mapping) for r in rows]


# -----------------------------------------------------------------------------
# 7. 评论关键词云（按景区 or 全局；用 PG simple 分词 + 字符过滤）
# -----------------------------------------------------------------------------
@router.get("/wordcloud", summary="评论关键词云（全局或单景区）")
async def wordcloud(
    db: AsyncSession = Depends(get_db),
    spot_id: int | None = Query(None, description="不传则全局采样"),
    limit: int = Query(80, ge=10, le=300),
) -> list[dict]:
    """从 fact_comment.content_tsv 抽取高频中文词作为词云数据。

    返回: [{name, value}] - ECharts wordcloud 格式
    """
    async def _query():
        # ts_stat 抽取词频；过滤掉单字符/英文/数字
        if spot_id is None:
            sql = """
                SELECT word AS name, ndoc AS value
                FROM ts_stat('SELECT content_tsv FROM fact_comment LIMIT 50000')
                WHERE word ~ '^[\\u4e00-\\u9fa5]{2,}$'
                ORDER BY ndoc DESC
                LIMIT :n
            """
            params = {"n": limit}
        else:
            sql = """
                SELECT word AS name, ndoc AS value
                FROM ts_stat(
                    'SELECT content_tsv FROM fact_comment WHERE spot_id = ' || :sid
                )
                WHERE word ~ '^[\\u4e00-\\u9fa5]{2,}$'
                ORDER BY ndoc DESC
                LIMIT :n
            """
            params = {"sid": spot_id, "n": limit}

        try:
            rows = await db.execute(text(sql), params)
            return [{"name": r.name, "value": int(r.value)} for r in rows]
        except Exception:
            # 兜底：直接 substring 切词（粗略），适用于 simple parser 无中文分词的场景
            fallback = """
                SELECT word AS name, sum(c) AS value FROM (
                    SELECT regexp_matches(content, '[\\u4e00-\\u9fa5]{2,4}', 'g') AS m,
                           count(*) AS c
                    FROM fact_comment
                    """ + ("WHERE spot_id = :sid" if spot_id else "") + """
                    GROUP BY m
                ) sub, unnest(m) AS word
                GROUP BY word
                ORDER BY value DESC
                LIMIT :n
            """
            params2 = {"n": limit}
            if spot_id is not None:
                params2["sid"] = spot_id
            rows = await db.execute(text(fallback), params2)
            return [{"name": r.name, "value": int(r.value)} for r in rows]

    cache_key = f"dashboard:wordcloud:{spot_id or 'all'}:{limit}"
    return await cache_get_or_set(cache_key, _query, settings.CACHE_HEATMAP_TTL)

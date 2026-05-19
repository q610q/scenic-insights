"""Spot CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_get_or_set
from app.config import settings
from app.deps import get_db
from app.schemas.spot import SpotBrief, SpotDetail

router = APIRouter(prefix="/spots", tags=["景区"])


@router.get("", response_model=list[SpotBrief], summary="景区分页列表（筛选）")
async def list_spots(
    response: Response,
    db: AsyncSession = Depends(get_db),
    city: str | None = Query(None),
    level: str | None = Query(None, pattern="^[1-5]A$"),
    tier: str | None = Query(None, pattern="^(high|medium|low|silent)$"),
    min_grade: float | None = Query(None, ge=0, le=5),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
) -> list[SpotBrief]:
    conds = []
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}
    if city:
        conds.append("city = :city")
        params["city"] = city
    if level:
        conds.append("level = :level")
        params["level"] = level
    if tier:
        conds.append("comment_tier = :tier")
        params["tier"] = tier
    if min_grade is not None:
        conds.append("grade >= :min_grade")
        params["min_grade"] = min_grade

    where = ("WHERE " + " AND ".join(conds)) if conds else ""

    # 统计总数（用于前端分页器）— 复用同一份 where 条件，剔除 limit/offset
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (
        await db.execute(
            text(f"SELECT COUNT(*) FROM dim_scenic_spot {where}"), count_params
        )
    ).scalar() or 0
    response.headers["X-Total-Count"] = str(total)

    rows = await db.execute(
        text(f"""
            SELECT id, name, level, city, grade, hot,
                   comment_count_real, comment_tier, lon, lat
            FROM dim_scenic_spot
            {where}
            ORDER BY comment_count_real DESC NULLS LAST, name
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    return [dict(r._mapping) for r in rows]


@router.get("/{spot_id}", response_model=SpotDetail, summary="景区详情")
async def get_spot(
    spot_id: int,
    db: AsyncSession = Depends(get_db),
) -> SpotDetail:
    async def _query():
        row = (
            await db.execute(
                text("""
                    SELECT id, name, level, tag, city, province, district,
                           location, phone, open_time_raw, intro, notice, tips,
                           grade, hot, total_comments_raw,
                           comment_count_all, comment_count_real, comment_count_default,
                           has_real_comments, comment_tier, lon, lat
                    FROM dim_scenic_spot
                    WHERE id = :sid
                """),
                {"sid": spot_id},
            )
        ).one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail=f"Spot {spot_id} not found")
        return dict(row._mapping)

    return await cache_get_or_set(
        f"spot:detail:{spot_id}", _query, settings.CACHE_SPOT_DETAIL_TTL
    )


@router.get("/{spot_id}/comment-distribution", summary="某景区评分分布（饼图）")
async def grade_dist(
    spot_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = (
        await db.execute(
            text("""
                SELECT grade_5_count, grade_4_count, grade_3_count,
                       grade_2_count, grade_1_count, avg_co_grade
                FROM mv_spot_metrics
                WHERE id = :sid
            """),
            {"sid": spot_id},
        )
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail=f"Spot {spot_id} not found")
    return dict(row._mapping)


@router.get("/cities/list", summary="所有城市列表（筛选器下拉用）")
async def list_cities(db: AsyncSession = Depends(get_db)) -> list[dict]:
    async def _query():
        rows = await db.execute(
            text("""
                SELECT city, spot_count, total_real_comments
                FROM mv_city_summary
                WHERE city <> '未分类'
                ORDER BY spot_count DESC
            """)
        )
        return [dict(r._mapping) for r in rows]

    return await cache_get_or_set("spots:cities", _query, 86400)

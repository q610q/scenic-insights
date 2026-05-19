-- =============================================================================
-- 04_materialized_views.sql — 大屏用物化视图
-- =============================================================================
-- 大屏 / 看板的所有聚合查询都走这里，不直接打 fact_comment。
-- 定时刷新由 APScheduler 触发 (FastAPI 后端)。
-- =============================================================================

-- -----------------------------------------------------------------------------
-- mv_spot_metrics — 景区综合指标（每行 = 1 景区）
-- -----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_spot_metrics CASCADE;

CREATE MATERIALIZED VIEW mv_spot_metrics AS
SELECT
    s.id,
    s.name,
    s.city,
    s.province,
    s.level,
    s.tag,
    s.grade,
    s.hot,
    s.lon,
    s.lat,
    s.geo_point,
    s.comment_tier,
    s.comment_count_real,
    COALESCE(c.real_avg,    NULL)::NUMERIC(3, 2)  AS avg_co_grade,
    COALESCE(c.grade_5_cnt, 0)                    AS grade_5_count,
    COALESCE(c.grade_4_cnt, 0)                    AS grade_4_count,
    COALESCE(c.grade_3_cnt, 0)                    AS grade_3_count,
    COALESCE(c.grade_2_cnt, 0)                    AS grade_2_count,
    COALESCE(c.grade_1_cnt, 0)                    AS grade_1_count,
    c.first_comment,
    c.last_comment
FROM dim_scenic_spot s
LEFT JOIN (
    SELECT
        spot_id,
        AVG(co_grade)::NUMERIC(3, 2)                 AS real_avg,
        COUNT(*) FILTER (WHERE co_grade = 5)         AS grade_5_cnt,
        COUNT(*) FILTER (WHERE co_grade = 4)         AS grade_4_cnt,
        COUNT(*) FILTER (WHERE co_grade = 3)         AS grade_3_cnt,
        COUNT(*) FILTER (WHERE co_grade = 2)         AS grade_2_cnt,
        COUNT(*) FILTER (WHERE co_grade = 1)         AS grade_1_cnt,
        MIN(co_time)                                 AS first_comment,
        MAX(co_time)                                 AS last_comment
    FROM fact_comment
    GROUP BY spot_id
) c ON c.spot_id = s.id;

CREATE UNIQUE INDEX ON mv_spot_metrics (id);
CREATE INDEX ON mv_spot_metrics (city, grade DESC);
CREATE INDEX ON mv_spot_metrics (comment_count_real DESC);
CREATE INDEX ON mv_spot_metrics (level);
CREATE INDEX ON mv_spot_metrics USING GIST (geo_point);


-- -----------------------------------------------------------------------------
-- mv_comment_monthly — 月度评论趋势 (spot_id × ym)
-- -----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_comment_monthly CASCADE;

CREATE MATERIALIZED VIEW mv_comment_monthly AS
SELECT
    spot_id,
    date_trunc('month', co_time)::DATE  AS ym,
    COUNT(*)                            AS cnt,
    AVG(co_grade)::NUMERIC(3, 2)        AS avg_grade
FROM fact_comment
GROUP BY spot_id, date_trunc('month', co_time);

CREATE UNIQUE INDEX ON mv_comment_monthly (spot_id, ym);
CREATE INDEX ON mv_comment_monthly (ym);


-- -----------------------------------------------------------------------------
-- mv_city_summary — 城市汇总（KPI 卡用）
-- -----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_city_summary CASCADE;

CREATE MATERIALIZED VIEW mv_city_summary AS
SELECT
    COALESCE(NULLIF(city, ''), '未分类') AS city,
    COALESCE(NULLIF(province, ''), '')    AS province,
    COUNT(DISTINCT id)                    AS spot_count,
    AVG(grade)::NUMERIC(3, 2)             AS avg_grade,
    SUM(comment_count_real)               AS total_real_comments,
    COUNT(*) FILTER (WHERE comment_tier IN ('high', 'medium')) AS hot_spot_count
FROM mv_spot_metrics
GROUP BY city, province;

CREATE UNIQUE INDEX ON mv_city_summary (city, province);


-- -----------------------------------------------------------------------------
-- mv_level_dist — 等级分布（首页饼图）
-- -----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_level_dist CASCADE;

CREATE MATERIALIZED VIEW mv_level_dist AS
SELECT
    COALESCE(level, '未评级') AS level,
    COUNT(*)                  AS spot_count,
    SUM(comment_count_real)   AS total_comments,
    AVG(grade)::NUMERIC(3, 2) AS avg_grade
FROM dim_scenic_spot
GROUP BY level
ORDER BY level NULLS LAST;

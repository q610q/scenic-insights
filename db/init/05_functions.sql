-- =============================================================================
-- 05_functions.sql — 工具函数（物化视图刷新等）
-- =============================================================================

-- 刷新所有物化视图（CONCURRENTLY 不阻塞读）
CREATE OR REPLACE FUNCTION refresh_all_mvs()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_spot_metrics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_comment_monthly;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_city_summary;
    REFRESH MATERIALIZED VIEW             mv_level_dist;   -- 无唯一索引
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_all_mvs IS '刷新所有大屏物化视图（CONCURRENTLY 优先）';


-- 取附近 N 公里景区（地图圈选）
CREATE OR REPLACE FUNCTION nearby_spots(
    p_lon  DOUBLE PRECISION,
    p_lat  DOUBLE PRECISION,
    p_km   DOUBLE PRECISION DEFAULT 50,
    p_lim  INT              DEFAULT 50
)
RETURNS TABLE (
    id   INT,
    name VARCHAR,
    city VARCHAR,
    level VARCHAR,
    grade NUMERIC,
    dist_km DOUBLE PRECISION
) AS $$
    SELECT
        s.id, s.name, s.city, s.level, s.grade,
        ST_DistanceSphere(
            s.geo_point,
            ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)
        ) / 1000.0 AS dist_km
    FROM dim_scenic_spot s
    WHERE s.geo_point IS NOT NULL
      AND ST_DWithin(
          s.geo_point::geography,
          ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography,
          p_km * 1000
      )
    ORDER BY dist_km
    LIMIT p_lim;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION nearby_spots IS '半径搜索（地图圈选用，需 PostGIS）';


-- 关键词搜索（trigram 模糊 + tsvector 全文）
CREATE OR REPLACE FUNCTION search_spots(
    p_q   VARCHAR,
    p_lim INT DEFAULT 20
)
RETURNS TABLE (
    id INT,
    name VARCHAR,
    city VARCHAR,
    grade NUMERIC,
    score REAL
) AS $$
    SELECT
        s.id, s.name, s.city, s.grade,
        GREATEST(
            similarity(s.name, p_q),
            ts_rank(s.intro_tsv, plainto_tsquery('simple', p_q)) * 0.5
        ) AS score
    FROM dim_scenic_spot s
    WHERE s.name % p_q
       OR s.intro_tsv @@ plainto_tsquery('simple', p_q)
    ORDER BY score DESC
    LIMIT p_lim;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION search_spots IS '景区关键词搜索（trgm 模糊 + tsvector 全文）';

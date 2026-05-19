-- =============================================================================
-- 03_indexes.sql — 索引（在数据导入后再创建以加速）
-- =============================================================================
-- 提示：导入流程会在大批量 INSERT 后调用本文件。
--       手动: psql -f 03_indexes.sql
-- =============================================================================

-- ----- dim_scenic_spot -----
CREATE INDEX IF NOT EXISTS idx_spot_geo
    ON dim_scenic_spot USING GIST (geo_point);

CREATE INDEX IF NOT EXISTS idx_spot_intro_tsv
    ON dim_scenic_spot USING GIN (intro_tsv);

CREATE INDEX IF NOT EXISTS idx_spot_name_trgm
    ON dim_scenic_spot USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_spot_city_grade
    ON dim_scenic_spot (city, grade DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_spot_level
    ON dim_scenic_spot (level)
    WHERE level IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_spot_tier
    ON dim_scenic_spot (comment_tier);

CREATE INDEX IF NOT EXISTS idx_spot_real_count
    ON dim_scenic_spot (comment_count_real DESC NULLS LAST);


-- ----- fact_comment (分区表，索引自动下推到每个分区) -----
CREATE INDEX IF NOT EXISTS idx_comment_spot_time
    ON fact_comment (spot_id, co_time DESC);

CREATE INDEX IF NOT EXISTS idx_comment_grade
    ON fact_comment (co_grade)
    WHERE co_grade IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_comment_tsv
    ON fact_comment USING GIN (content_tsv);

CREATE INDEX IF NOT EXISTS idx_comment_co_time
    ON fact_comment (co_time);

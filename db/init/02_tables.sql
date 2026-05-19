-- =============================================================================
-- 02_tables.sql — 表结构（维表 + 评论事实表分区表）
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 景点维表（~2000 行；含 silent 景区）
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS dim_scenic_spot CASCADE;
CREATE TABLE dim_scenic_spot (
    id                      SERIAL PRIMARY KEY,
    name                    VARCHAR(100) NOT NULL UNIQUE,
    level                   VARCHAR(4),
    tag                     VARCHAR(255),
    location                VARCHAR(255),
    province                VARCHAR(32),
    city                    VARCHAR(64),
    district                VARCHAR(64),
    phone                   VARCHAR(128),
    open_time_raw           VARCHAR(500),
    open_time               JSONB,
    intro                   TEXT,
    notice                  TEXT,
    tips                    TEXT,
    grade                   NUMERIC(3, 2),
    hot                     NUMERIC(4, 2),
    total_comments_raw      INT,
    comment_count_all       INT       DEFAULT 0,
    comment_count_real      INT       DEFAULT 0,
    comment_count_default   INT       DEFAULT 0,
    has_real_comments       BOOLEAN   DEFAULT FALSE,
    comment_tier            VARCHAR(8) CHECK (comment_tier IN ('high', 'medium', 'low', 'silent')),
    source_schemas          TEXT[],
    geo_point               GEOMETRY(Point, 4326),
    lon                     DOUBLE PRECISION,
    lat                     DOUBLE PRECISION,
    intro_tsv               tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple', coalesce(intro, '') || ' ' ||
                                  coalesce(notice, '') || ' ' ||
                                  coalesce(tag, ''))
        ) STORED,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE  dim_scenic_spot           IS '景点维表（多源融合，全景区无丢失）';
COMMENT ON COLUMN dim_scenic_spot.level     IS '景区等级 5A/4A/3A/2A/1A';
COMMENT ON COLUMN dim_scenic_spot.tag       IS '景点一句话标签（来自 Schema A TGA）';
COMMENT ON COLUMN dim_scenic_spot.hot       IS '热度 0-10（仅 Schema B 有）';
COMMENT ON COLUMN dim_scenic_spot.comment_tier IS '评论分层：high(>100)/medium(10-100)/low(1-9)/silent(0)';
COMMENT ON COLUMN dim_scenic_spot.geo_point IS 'PostGIS 几何点（WGS84）；从 lon/lat 触发器生成';


-- -----------------------------------------------------------------------------
-- 评论事实表（声明式分区，按 co_time 年）
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_comment CASCADE;
CREATE TABLE fact_comment (
    id              BIGSERIAL,
    spot_id         INT          NOT NULL REFERENCES dim_scenic_spot(id) ON DELETE CASCADE,
    co_name         VARCHAR(64),
    co_grade        SMALLINT CHECK (co_grade BETWEEN 1 AND 5),
    content         TEXT,
    content_hash    CHAR(32)     NOT NULL,
    ip_region       VARCHAR(32),
    co_time         DATE         NOT NULL,
    src_schema      CHAR(1),
    content_tsv     tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED,
    PRIMARY KEY (id, co_time),
    UNIQUE (content_hash, co_time)
) PARTITION BY RANGE (co_time);

COMMENT ON TABLE fact_comment IS '评论事实表（仅真实评，按年分区；含 simple 全文 tsvector）';


-- -----------------------------------------------------------------------------
-- 自动创建分区（覆盖 2010-2025，外加 default）
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    y INT;
BEGIN
    FOR y IN 2010..2025 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS fact_comment_%s '
            'PARTITION OF fact_comment '
            'FOR VALUES FROM (''%s-01-01'') TO (''%s-01-01'')',
            y, y, y + 1
        );
    END LOOP;
    -- 兜底：早期/异常时间
    EXECUTE 'CREATE TABLE IF NOT EXISTS fact_comment_default '
            'PARTITION OF fact_comment DEFAULT';
END $$;


-- -----------------------------------------------------------------------------
-- 触发器：lon/lat → geo_point 自动同步
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_dim_spot_set_geo()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.lon IS NOT NULL AND NEW.lat IS NOT NULL THEN
        NEW.geo_point := ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326);
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_dim_spot_geo
    BEFORE INSERT OR UPDATE OF lon, lat ON dim_scenic_spot
    FOR EACH ROW EXECUTE FUNCTION trg_dim_spot_set_geo();

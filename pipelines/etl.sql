-- =============================================================================
-- 旅游数据 ETL — DuckDB 单文件 SQL (v2: 景区不丢失)
-- =============================================================================
-- 关键设计修正:
--   旧: 评论过滤 → 评论去重 → 反推景区维表 (会丢 229 个景区)
--   新: CSV → 全量 staging (含 is_default 标记) → 景区维表全保留
--       → 仅真实评论写入 fact_comment (评论维度过滤，景区维度无损)
--
-- 输入: data/csv/*.csv (24 个文件, 2 种 schema, UTF-8)
-- 输出:
--   data/parquet/dim_spot.parquet              全部 ~950 景区
--   data/parquet/fact_comment/year=YYYY/...    仅真实评论（按年分区）
--
-- 阶段:
--   1. Schema A (1-14.csv)   → staging_a (含 is_default 标记)
--   2. Schema B (22-110.csv) → staging_b (含 is_default 标记)
--   3. 全量 UNION             → all_records
--   4. 真实评论去重           → comments_real (用于 fact)
--   5. 全景区聚合维表         → dim_spot   (含 real / default 评论计数)
--   6. 落 Parquet
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 阶段 1: Schema A 联合 (1-14.csv) → staging_a
-- 不在源头过滤评论；用 is_default 标记，下游分流
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE staging_a AS
SELECT
    trim(regexp_replace(SPOT, '^\?', ''))                       AS spot_name,
    regexp_extract(LEVEL, '[0-9]A', 0)                          AS level,
    trim(LOCATION)                                              AS location,
    TGA                                                         AS tag,
    TRY_CAST(GRADE AS DECIMAL(3, 2))                            AS spot_grade,
    TRY_CAST(regexp_extract(QTY, '\d+', 0) AS INTEGER)          AS spot_qty,
    INTRO                                                       AS intro,
    OPENTIME                                                    AS open_time_raw,
    NOTICE                                                      AS notice,
    ST                                                          AS tips,
    NULL::VARCHAR                                               AS phone,
    NULL::DECIMAL(4, 2)                                         AS hot,
    CO_NAME                                                     AS co_name,
    NULL::SMALLINT                                              AS co_grade,
    NULL::VARCHAR                                               AS ip_region,
    TRY_CAST(strptime(CO_TIME, '%Y/%m/%d') AS DATE)             AS co_time,
    COMMENT                                                     AS content,
    -- 关键：is_default 标记，便于下游过滤
    CASE
        WHEN COMMENT IS NULL                              THEN TRUE
        WHEN trim(COMMENT) LIKE '用户未点评%'              THEN TRUE
        WHEN trim(COMMENT) LIKE '%系统默认好评%'           THEN TRUE
        WHEN length(trim(COMMENT)) < 2                    THEN TRUE
        ELSE FALSE
    END                                                         AS is_default,
    'A'                                                         AS src_schema
FROM read_csv(
    [
        'data/csv/1.csv',  'data/csv/2.csv',  'data/csv/3.csv',  'data/csv/4.csv',
        'data/csv/5.csv',  'data/csv/6.csv',  'data/csv/7.csv',  'data/csv/8.csv',
        'data/csv/9.csv',  'data/csv/10.csv', 'data/csv/11.csv', 'data/csv/12.csv',
        'data/csv/13.csv', 'data/csv/14.csv'
    ],
    header = true,
    encoding = 'utf-8',
    null_padding = true,
    ignore_errors = true,
    quote = '"',
    escape = '"',
    all_varchar = true,
    parallel = false
)
WHERE SPOT IS NOT NULL AND length(trim(SPOT)) >= 2;


-- -----------------------------------------------------------------------------
-- 阶段 2: Schema B 联合 (22-110.csv) → staging_b
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE staging_b AS
SELECT
    trim(regexp_replace(SPOT, '^\?', ''))                              AS spot_name,
    NULL::VARCHAR                                                      AS level,
    trim(LOCATION)                                                     AS location,
    NULL::VARCHAR                                                      AS tag,
    TRY_CAST(GRADE AS DECIMAL(3, 2))                                   AS spot_grade,
    TRY_CAST(regexp_extract(QTY, '\d+', 0) AS INTEGER)                 AS spot_qty,
    INTRO                                                              AS intro,
    OPENTIME                                                           AS open_time_raw,
    NULL::VARCHAR                                                      AS notice,
    NULL::VARCHAR                                                      AS tips,
    PHONE                                                              AS phone,
    TRY_CAST(HOT AS DECIMAL(4, 2))                                     AS hot,
    CO_NAME                                                            AS co_name,
    TRY_CAST(regexp_extract(CO_GRADE, '\d', 0) AS SMALLINT)            AS co_grade,
    regexp_extract(CO_TIME, 'IP属地：([^"]+)', 1)                      AS ip_region,
    TRY_CAST(regexp_extract(CO_TIME, '\d{4}-\d{2}-\d{2}', 0) AS DATE)  AS co_time,
    COMMENT                                                            AS content,
    CASE
        WHEN COMMENT IS NULL                              THEN TRUE
        WHEN trim(COMMENT) LIKE '用户未点评%'              THEN TRUE
        WHEN trim(COMMENT) LIKE '%系统默认好评%'           THEN TRUE
        WHEN length(trim(COMMENT)) < 2                    THEN TRUE
        ELSE FALSE
    END                                                                AS is_default,
    'B'                                                                AS src_schema
FROM read_csv(
    [
        'data/csv/22.csv',  'data/csv/33.csv', 'data/csv/44.csv', 'data/csv/55.csv',
        'data/csv/66.csv',  'data/csv/77.csv', 'data/csv/88.csv', 'data/csv/99.csv',
        'data/csv/100.csv', 'data/csv/110.csv'
    ],
    header = true,
    encoding = 'utf-8',
    null_padding = true,
    ignore_errors = true,
    quote = '"',
    escape = '"',
    all_varchar = true,
    parallel = false
)
WHERE SPOT IS NOT NULL AND length(trim(SPOT)) >= 2;


-- -----------------------------------------------------------------------------
-- 阶段 3: 全量 UNION → all_records
-- 含全部评论（含默认评），含 is_default 标记
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE all_records AS
SELECT * FROM staging_a
UNION ALL
SELECT * FROM staging_b;


-- -----------------------------------------------------------------------------
-- 阶段 4: 真实评论去重 → comments_real (用于 fact 表)
-- 仅对 is_default = false 的评论去重
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE comments_real AS
WITH filtered AS (
    SELECT
        *,
        md5(
            coalesce(spot_name, '') || '|' ||
            coalesce(co_name, '')   || '|' ||
            coalesce(co_time::TEXT, '') || '|' ||
            left(coalesce(content, ''), 50)
        ) AS content_hash
    FROM all_records
    WHERE NOT is_default
      AND co_time IS NOT NULL
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT
        *,
        row_number() OVER (PARTITION BY content_hash ORDER BY src_schema) AS rn
    FROM filtered
)
WHERE rn = 1;


-- -----------------------------------------------------------------------------
-- 阶段 5: 构建景点维表 → dim_spot
-- 关键：从 all_records 全量聚合（不依赖评论过滤），保留全部 ~950 景区
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_spot AS
WITH agg AS (
    SELECT
        spot_name,
        max(level)                                        AS level,
        max(tag)                                          AS tag,
        max(phone)                                        AS phone,
        max(hot)                                          AS hot,
        max(spot_grade)                                   AS grade,
        max(spot_qty)                                     AS total_comments_raw,
        arg_max(location,      length(location))          AS location,
        arg_max(intro,         length(intro))             AS intro,
        arg_max(notice,        length(notice))            AS notice,
        arg_max(tips,          length(tips))              AS tips,
        arg_max(open_time_raw, length(open_time_raw))     AS open_time_raw,
        list_distinct(list(src_schema))                   AS source_schemas,
        count(*)                                          AS comment_count_all,
        count(*) FILTER (WHERE NOT is_default)            AS comment_count_real,
        count(*) FILTER (WHERE is_default)                AS comment_count_default
    FROM all_records
    GROUP BY spot_name
),
parsed AS (
    SELECT *,
        coalesce(
            regexp_extract(location, '^([^省市区县]{2,4}省)', 1),
            regexp_extract(location, '^(北京市|上海市|天津市|重庆市)', 1),
            regexp_extract(location, '^(内蒙古自治区|新疆维吾尔自治区|西藏自治区|广西壮族自治区|宁夏回族自治区)', 1),
            regexp_extract(location, '^(香港特别行政区|澳门特别行政区)', 1)
        ) AS province_raw,
        coalesce(
            regexp_extract(location, '(?:省|区)([^市州区]{2,8}市)', 1),
            regexp_extract(location, '(?:省|区)([^自治州]{2,6}自治州)', 1),
            regexp_extract(location, '^(北京|上海|天津|重庆)', 1)
        ) AS city_raw
    FROM agg
)
SELECT
    row_number() OVER (ORDER BY comment_count_real DESC, spot_name) AS id,
    spot_name                                         AS name,
    level,
    tag,
    phone,
    hot,
    grade,
    total_comments_raw,
    location,
    CASE
        WHEN province_raw IN ('北京市','上海市','天津市','重庆市')
            THEN regexp_replace(province_raw, '市$', '')
        WHEN length(province_raw) > 0
            THEN regexp_replace(province_raw, '(省|自治区|特别行政区)$', '')
        ELSE NULL
    END                                               AS province,
    CASE
        WHEN city_raw IN ('北京','上海','天津','重庆') THEN city_raw
        WHEN length(city_raw) > 0
            THEN regexp_replace(city_raw, '(市|自治州)$', '')
        ELSE NULL
    END                                               AS city,
    intro,
    notice,
    tips,
    open_time_raw,
    source_schemas,
    comment_count_all,
    comment_count_real,
    comment_count_default,
    (comment_count_real > 0)                          AS has_real_comments,
    CASE
        WHEN comment_count_real = 0           THEN 'silent'
        WHEN comment_count_real < 10          THEN 'low'
        WHEN comment_count_real < 100         THEN 'medium'
        ELSE                                       'high'
    END                                               AS comment_tier,
    NULL::DOUBLE                                      AS lon,
    NULL::DOUBLE                                      AS lat
FROM parsed;


-- -----------------------------------------------------------------------------
-- 阶段 5b: 城市坐标兜底（无 AMAP key 时使用，精度到城市级）
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE city_geo AS
SELECT * FROM (VALUES
    ('北京', 116.405, 39.905), ('上海', 121.473, 31.230),
    ('天津', 117.190, 39.125), ('重庆', 106.504, 29.533),
    ('武汉', 114.305, 30.593), ('宜昌', 111.290, 30.702),
    ('十堰', 110.788, 32.647), ('襄阳', 112.144, 32.042),
    ('荆州', 112.239, 30.335), ('黄冈', 114.879, 30.447),
    ('鄂州', 114.895, 30.391), ('恩施', 109.486, 30.283),
    ('咸宁', 114.328, 29.832), ('随州', 113.382, 31.690),
    ('荆门', 112.204, 31.035), ('黄石', 115.077, 30.220),
    ('孝感', 113.957, 30.926), ('仙桃', 113.454, 30.364),
    ('潜江', 112.896, 30.421), ('天门', 113.166, 30.653),
    ('神农架', 110.671, 31.745),
    ('广州', 113.264, 23.129), ('深圳', 114.057, 22.543),
    ('杭州', 120.155, 30.274), ('南京', 118.778, 32.061),
    ('成都', 104.066, 30.572), ('西安', 108.948, 34.263),
    ('长沙', 112.939, 28.228), ('郑州', 113.625, 34.747),
    ('合肥', 117.283, 31.860), ('福州', 119.296, 26.083),
    ('厦门', 118.082, 24.480), ('青岛', 120.355, 36.082),
    ('济南', 117.000, 36.660), ('沈阳', 123.432, 41.808),
    ('大连', 121.620, 38.917), ('哈尔滨', 126.535, 45.802),
    ('长春', 125.324, 43.820), ('昆明', 102.832, 24.880),
    ('贵阳', 106.713, 26.578), ('南宁', 108.366, 22.817),
    ('海口', 110.199, 20.044), ('三亚', 109.508, 18.252),
    ('南昌', 115.892, 28.676), ('太原', 112.549, 37.857),
    ('石家庄', 114.502, 38.045), ('呼和浩特', 111.752, 40.842),
    ('兰州', 103.834, 36.061), ('西宁', 101.778, 36.617),
    ('银川', 106.232, 38.486), ('乌鲁木齐', 87.617, 43.793),
    ('拉萨', 91.140, 29.645)
) AS t(city, lon, lat);

UPDATE dim_spot
SET lon = g.lon, lat = g.lat
FROM city_geo g
WHERE dim_spot.city = g.city
  AND dim_spot.lon IS NULL;


-- -----------------------------------------------------------------------------
-- 阶段 6a: 落地评论事实表 → 按年分区 Parquet（仅真实评论）
-- -----------------------------------------------------------------------------
COPY (
    SELECT
        c.content_hash,
        d.id              AS spot_id,
        d.name            AS spot_name,
        c.co_name,
        c.co_grade,
        c.content,
        c.ip_region,
        c.co_time,
        year(c.co_time)   AS year,
        c.src_schema
    FROM comments_real c
    JOIN dim_spot d ON d.name = c.spot_name
) TO 'data/parquet/fact_comment'
(FORMAT PARQUET, PARTITION_BY (year), OVERWRITE_OR_IGNORE 1, COMPRESSION 'zstd');


-- -----------------------------------------------------------------------------
-- 阶段 6b: 落地景点维表 → 单文件 Parquet
-- -----------------------------------------------------------------------------
COPY dim_spot
TO 'data/parquet/dim_spot.parquet'
(FORMAT PARQUET, OVERWRITE_OR_IGNORE 1, COMPRESSION 'zstd');

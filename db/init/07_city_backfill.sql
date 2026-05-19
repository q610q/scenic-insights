-- =============================================================================
-- 城市/省份回填 (idempotent, safe to re-run)
--
-- 背景：etl.sql 阶段5 的 city 正则要求 `(?:省|区)` 前缀，
-- 但原始 CSV 中 location 已省略省级（如 "武汉市江岸区..."），导致约 60% 提取失败。
--
-- 本脚本通过 city → province 字典扫描 location/name 字段补全，并归一化别名。
-- =============================================================================

BEGIN;

-- 0) 城市 → 省份字典（hubei + 全国热门 + 县级市）
CREATE TEMP TABLE _city_dict (city TEXT PRIMARY KEY, province TEXT) ON COMMIT DROP;

INSERT INTO _city_dict (city, province) VALUES
    -- 直辖市
    ('北京','北京'),('上海','上海'),('天津','天津'),('重庆','重庆'),
    -- 湖北地级
    ('武汉','湖北'),('宜昌','湖北'),('十堰','湖北'),('襄阳','湖北'),
    ('荆州','湖北'),('黄冈','湖北'),('鄂州','湖北'),('恩施','湖北'),
    ('咸宁','湖北'),('随州','湖北'),('荆门','湖北'),('黄石','湖北'),
    ('孝感','湖北'),('仙桃','湖北'),('潜江','湖北'),('天门','湖北'),('神农架','湖北'),
    -- 湖北县级市
    ('钟祥','湖北'),('丹江口','湖北'),('利川','湖北'),('当阳','湖北'),
    ('枝江','湖北'),('宜都','湖北'),('赤壁','湖北'),('麻城','湖北'),
    ('应城','湖北'),('安陆','湖北'),('汉川','湖北'),('大冶','湖北'),
    ('洪湖','湖北'),('石首','湖北'),('枣阳','湖北'),('广水','湖北'),
    ('武穴','湖北'),('老河口','湖北'),('京山','湖北'),('宜城','湖北'),
    -- 其他热门
    ('广州','广东'),('深圳','广东'),('杭州','浙江'),('南京','江苏'),
    ('成都','四川'),('西安','陕西'),('长沙','湖南'),('郑州','河南'),
    ('合肥','安徽'),('福州','福建'),('厦门','福建'),('青岛','山东'),
    ('济南','山东'),('沈阳','辽宁'),('大连','辽宁'),('哈尔滨','黑龙江'),
    ('长春','吉林'),('昆明','云南'),('贵阳','贵州'),('南宁','广西'),
    ('海口','海南'),('三亚','海南'),('南昌','江西'),('太原','山西'),
    ('石家庄','河北'),('呼和浩特','内蒙古'),('兰州','甘肃'),('西宁','青海'),
    ('银川','宁夏'),('乌鲁木齐','新疆'),('拉萨','西藏')
ON CONFLICT (city) DO NOTHING;

-- 1) 别名 / 错字归一化（保证幂等）
UPDATE dim_scenic_spot SET city = '襄阳' WHERE city IN ('襄樊','湖北襄樊','襄樊枣阳');
UPDATE dim_scenic_spot SET city = '黄冈' WHERE city IN ('黄岗','湖北黄冈');
UPDATE dim_scenic_spot SET city = '广水' WHERE city IN ('湖北广水');

-- 2) 清除非中文 city（脏数据）
UPDATE dim_scenic_spot SET city = NULL, province = NULL
WHERE city ~ '[^一-龥]';

-- 3) 字典扫描 location 子串回填（优先长字典名匹配，避免短名误中）
WITH matched AS (
    SELECT d.id, c.city AS new_city, c.province AS new_province
    FROM dim_scenic_spot d
    CROSS JOIN LATERAL (
        SELECT city, province FROM _city_dict
        WHERE d.location LIKE '%' || city || '%'
        ORDER BY length(city) DESC LIMIT 1
    ) c
    WHERE (d.city IS NULL OR d.city = '')
      AND d.location IS NOT NULL
)
UPDATE dim_scenic_spot d
SET city = m.new_city,
    province = COALESCE(NULLIF(d.province, ''), m.new_province)
FROM matched m WHERE d.id = m.id;

-- 4) 兜底：location 无 dict 词，但有中文 X市 模式（如冷门县级市）
UPDATE dim_scenic_spot
SET city = regexp_replace(
    (regexp_match(location, '([一-龥]{2,4})市'))[1],
    '市$', ''
)
WHERE (city IS NULL OR city = '')
  AND location IS NOT NULL
  AND location ~ '[一-龥]{2,4}市';

-- 5) 把"非中文打头"的脏值（如"距钟祥"）规范到 dict 内城市
WITH dirty AS (
    SELECT d.id, c.city AS clean_city, c.province AS clean_province
    FROM dim_scenic_spot d
    JOIN _city_dict c ON d.city LIKE '%' || c.city || '%'
    WHERE d.city IS NOT NULL AND d.city <> ''
      AND d.city NOT IN (SELECT city FROM _city_dict)
)
UPDATE dim_scenic_spot d
SET city = dr.clean_city,
    province = COALESCE(NULLIF(d.province, ''), dr.clean_province)
FROM dirty dr WHERE d.id = dr.id;

-- 6) 扫描 name 字段（当 location 无信息时，景区名常带城市）
WITH from_name AS (
    SELECT d.id, c.city AS new_city, c.province AS new_province
    FROM dim_scenic_spot d
    CROSS JOIN LATERAL (
        SELECT city, province FROM _city_dict
        WHERE d.name LIKE '%' || city || '%'
        ORDER BY length(city) DESC LIMIT 1
    ) c
    WHERE (d.city IS NULL OR d.city = '')
      AND d.name IS NOT NULL
)
UPDATE dim_scenic_spot d
SET city = n.new_city,
    province = COALESCE(NULLIF(d.province, ''), n.new_province)
FROM from_name n WHERE d.id = n.id;

-- 7) 根据 city 反推 province（如果 city 在字典里）
UPDATE dim_scenic_spot d
SET province = c.province
FROM _city_dict c
WHERE d.city = c.city
  AND (d.province IS NULL OR d.province = '');

COMMIT;

-- 8) 摘要
SELECT
  count(*) FILTER (WHERE city IS NULL OR city = '')   AS no_city,
  count(*) FILTER (WHERE city IS NOT NULL AND city <> '') AS has_city,
  count(*) FILTER (WHERE province IS NULL OR province = '') AS no_province,
  count(DISTINCT city) FILTER (WHERE city IS NOT NULL AND city <> '') AS unique_cities,
  count(*) AS total
FROM dim_scenic_spot;

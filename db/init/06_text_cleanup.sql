-- =============================================================================
-- 06_text_cleanup.sql — 长文本字段清洗
-- =============================================================================


CREATE OR REPLACE FUNCTION clean_long_text(t TEXT) RETURNS TEXT AS $$
DECLARE
    s TEXT;
BEGIN
    IF t IS NULL OR length(trim(t)) = 0 THEN
        RETURN NULL;
    END IF;

    s := t;
    -- 1) 全角空格 / NBSP / BOM → 普通空格
    s := translate(s, E'　 ﻿​', '    ');
    -- 2) Tab → 空格
    s := replace(s, E'\t', ' ');
    -- 3) 抓取页面占位
    s := regexp_replace(s, '(全文|展开全文|查看全文|收起)[?？]?', '', 'g');
    -- 4) 孤立的 ? / ？
    s := regexp_replace(s, '(^|[\s])[?？](?=\s|$)', E'\\1', 'g');
    -- 5) 独立的冗余段落标题
    s := regexp_replace(
        s,
        '(^|\n)[ ]*(介绍|入园公告|公告|小贴士|温馨提示|免费政策|优惠政策|开放时间|其他信息|周边推荐|交通|地图|门票政策)[ ]*(?=\n|$)',
        E'\\1', 'g'
    );
    -- 6) 装饰行
    s := regexp_replace(s, '(^|\n)[-=*·•]{3,}[ ]*(?=\n|$)', E'\\1', 'g');
    -- 7) 行内多空格
    s := regexp_replace(s, '[ ]{2,}', ' ', 'g');
    -- 8) 行首尾空白
    s := regexp_replace(s, '(^|\n)[ ]+', E'\\1', 'g');
    s := regexp_replace(s, '[ ]+(\n|$)', E'\\1', 'g');
    -- 9) 多换行 → 单换行（段间不留空行，更紧凑）
    s := regexp_replace(s, E'\n{2,}', E'\n', 'g');
    -- 10) 剥离孤立的 *xxx* 强调标记（保留内容，去掉星号）
    s := regexp_replace(s, E'\\*([^*\n]{1,120})\\*', E'\\1', 'g');
    -- 11) 在 "数字、" 前补换行（让政策/贴士条目独立成行；行首已是换行则不重复插入）
    s := regexp_replace(s, E'([^\n])(\\d+、)', E'\\1\n\\2', 'g');
    -- 12) 段落标题后跟换行 → 标题紧接内容（保持单换行即可，规则 9 已压缩）
    s := regexp_replace(
        s,
        E'(优待政策|免费政策|优惠政策|门票政策|服务设施|温馨提示|小贴士|入园公告|其他信息|开放时间|游玩贴士|退改规则)\n+',
        E'\\1\n', 'g'
    );
    -- 13) 整体 trim
    s := btrim(s, E' \n\t');

    IF length(s) = 0 THEN
        RETURN NULL;
    END IF;
    RETURN s;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- intro 字段专用：在首次出现"优待政策/服务设施/门票政策/温馨提示/小贴士"时截断
CREATE OR REPLACE FUNCTION clean_intro(t TEXT) RETURNS TEXT AS $$
DECLARE
    s TEXT;
    cut_pos INT;
    keywords TEXT[] := ARRAY[
        '优待政策', '服务设施', '门票政策', '温馨提示', '小贴士',
        '免费政策', '优惠政策', '入园公告', '其他信息',
        '游玩贴士', '退改规则', '订单使用说明'
    ];
    kw TEXT;
    p INT;
BEGIN
    s := clean_long_text(t);
    IF s IS NULL THEN RETURN NULL; END IF;

    cut_pos := length(s) + 1;
    FOREACH kw IN ARRAY keywords LOOP
        p := position(kw IN s);
        IF p > 0 AND p < cut_pos THEN
            cut_pos := p;
        END IF;
    END LOOP;

    IF cut_pos <= length(s) THEN
        s := substring(s, 1, cut_pos - 1);
        s := btrim(s, E' \n\t');
    END IF;

    IF length(s) = 0 THEN RETURN NULL; END IF;
    RETURN s;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


COMMENT ON FUNCTION clean_long_text IS '清洗长文本：空白/占位符/冗余标题';
COMMENT ON FUNCTION clean_intro      IS '清洗景区介绍：在"优待政策"等关键词处截断';


-- 应用到现有数据
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'dim_scenic_spot') THEN
        UPDATE dim_scenic_spot SET
            intro    = clean_intro(intro),
            notice   = clean_long_text(notice),
            tips     = clean_long_text(tips),
            tag      = clean_long_text(tag),
            location = clean_long_text(location);
        RAISE NOTICE 'Cleaned dim_scenic_spot.';
    END IF;
END $$;

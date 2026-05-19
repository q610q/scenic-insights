-- =============================================================================
-- 01_extensions.sql — 启用 PostgreSQL 扩展
-- =============================================================================
-- 镜像: postgis/postgis:16-3.4 默认包含 PostGIS 3.4。
-- pgvector / zhparser 需自定义镜像（见 docker/Dockerfile.pg 注释）。
-- =============================================================================

-- 空间索引与地理查询（PostGIS 3.4+）
CREATE EXTENSION IF NOT EXISTS postgis;

-- 模糊匹配 / 中文短语索引（GIN + trigram）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 双字索引（中文检索更稳，需手动安装 postgresql-16-bigm）
-- CREATE EXTENSION IF NOT EXISTS pg_bigm;

-- 向量检索（未来 RAG 用，需 pgvector/pgvector:pg16 镜像）
-- CREATE EXTENSION IF NOT EXISTS vector;

-- 中文全文（zhparser；postgis 镜像未自带）
-- CREATE EXTENSION IF NOT EXISTS zhparser;
-- CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);
-- ALTER TEXT SEARCH CONFIGURATION chinese
--   ADD MAPPING FOR n,v,a,i,e,l WITH simple;

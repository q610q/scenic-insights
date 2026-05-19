# =============================================================================
# pipelines/Dockerfile — 一次性 ETL 容器
# 用法 (compose):  docker compose --profile bootstrap up etl
# 用法 (手跑):     docker compose --profile bootstrap run --rm etl
# =============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系统依赖：psycopg 编译 + curl 调试
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 项目依赖（根 pyproject 装 duckdb/pyarrow/typer/rich/httpx/pydantic）
COPY pyproject.toml README.md ./
COPY pipelines ./pipelines
RUN pip install --upgrade pip \
 && pip install -e . \
 && pip install \
        'psycopg[binary]>=3.2.3' \
        'rapidfuzz>=3.10.0'

# 默认执行幂等 bootstrap：等 PG → 检查是否已灌 → ETL → load
CMD ["python", "-m", "pipelines.run", "bootstrap"]

# data/ 目录说明

本目录中的**所有原始数据与中间产物均不纳入 git**（见根 `.gitignore`）。
本文件描述目录约定，便于他人复现 ETL 流水线。

## 目录结构

```
data/
├── csv/        # 24 个原始 CSV，双 Schema（A: 14 文件 ~10.6M 行 / B: 10 文件 ~3.4M 行）
├── txt/        # 3001 个景区详情 TXT
├── excel/      # 可选：原始 Excel
├── parquet/    # ETL 中间产物（按年分区 fact_comment + dim_spot.parquet）
├── staging/    # DuckDB 临时表
└── etl.duckdb  # DuckDB 单文件存储
```

## 数据获取

> ⚠️ 原始数据集体积约 **1.2 GB**，不在公开发行范围。
> 内部交付时通过 OSS / 网盘单独发放；放置到本目录即可。

放置后目录大小预期：

| 子目录 | 大小级别 |
|--------|----------|
| `data/csv/` | ~1.16 GB |
| `data/txt/` | ~5 MB (3001 文件) |
| `data/excel/` | 可选 |
| `data/parquet/` | ETL 生成 ~150 MB |
| `data/etl.duckdb` | ETL 生成 ~80 MB |

## 一键流水线

```bash
# 1. 安装依赖（uv 或 pip）
uv sync   # 或 pip install -e .

# 2. 一键 ETL：CSV → 解析 → 模糊匹配 → Geocoding
python -m pipelines.run all

# 3. 灌库（先启 docker compose）
docker compose up -d postgres redis
python -m pipelines.run load
```

依赖环境变量：

| 变量 | 用途 | 默认 |
|------|------|------|
| `DATABASE_URL` | PG 连接 | `postgresql://travel:changeme@localhost:5432/travel_dw` |
| `AMAP_API_KEY` | Geocoding | 需自行申请：https://lbs.amap.com → Web 服务 |

## 数据质量基线

P1–P9 已验证的指标：

- 真实评论：149,354 条（去默认评）
- 景区：2,064 个（含 21 个 silent）
- Geocoding 覆盖率：99.0%（2043/2064）
- 精确坐标：1,575 unique points（最大堆叠 ≤17 spots）

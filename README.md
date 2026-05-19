# 旅游数据可视化平台

> 基于真实景区评论数据集（1.13 GB / ~1400 万行 CSV + 3001 份景点详情 TXT）的端到端数据可视化项目：DuckDB ETL → PostgreSQL → FastAPI → Vue 3 大屏。

## ✨ 项目能力

- **大屏**：4 KPI · 全国景区热力 · 等级饼图 · Top10 · 评分散点 · 关键词云
- **筛选探索**：城市/等级/评论档位/评分多维过滤 + 分页（X-Total-Count 真值）
- **景区详情**：基础信息 · 评分分布 · 月度趋势 · 评论游标分页
- **后端性能**：所有 dashboard 端点 p95 < 9ms（物化视图 + Redis 缓存）
- **前端性能**：60fps，element-plus 按需引入，gzip 首屏 ~355 KB

## 🧱 技术栈

| 层 | 技术 |
|---|---|
| ETL | DuckDB 1.x · Polars-style SQL · Parquet 按年分区 · rapidfuzz 模糊匹配 |
| 存储 | PostgreSQL 16 + PostGIS + pg_trgm + zhparser · 物化视图 · 声明式分区 |
| 缓存 | Redis 7 + aiocache |
| API | FastAPI 0.115 async · SQLAlchemy 2.0 async · Pydantic v2 · APScheduler |
| 前端 | Vue 3.5 · Vite 6 · ECharts 5 · element-plus 2.9 · Pinia · TypeScript |
| 地理编码 | 高德 Web API v3 |
| 部署 | Docker Compose（postgres + redis + api + web/nginx） |

## 🚀 快速开始

### 方式 A：Docker Compose 一键启动（推荐）

```bash
# 1. 准备环境变量
cp .env.example .env
# 编辑 .env 填入 AMAP_API_KEY（可选；不填则跳过 geocoding，热力图坐标为空）

# 2. 把原始数据放到 ./data/csv/ 和 ./data/txt/（约 1.2 GB，见 data/README.md）

# 3. 一键启动 + 灌库
docker compose up -d                        # 起 postgres/redis/api/web（schema 自动建）
docker compose --profile bootstrap up etl   # 跑 ETL 灌库（约 5-10 分钟；幂等：已灌则秒退）

# 4. 访问
open http://localhost          # 大屏
open http://localhost:8000/docs # API 文档
```

> **未放数据时**：步骤 3 的 `etl` 会以退出码 2 报错并提示数据缺失；
> 基础服务仍正常运行，大屏可访问但所有数据为空。
> 放好数据后重跑 `docker compose --profile bootstrap up etl` 即可。

### 方式 B：本地开发（前后端分离）

```bash
# 1. 启动 PG + Redis
docker compose up -d postgres redis

# 2. 后端
cd server
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 3. 前端
cd client
npm install
npm run dev    # 默认 :3000

# 4. ETL 在 host 直接跑（DuckDB 不进容器，更快）
uv run python -m pipelines.run all
uv run python -m pipelines.run load
```

## 📊 数据规模

| 表 | 行数 | 说明 |
|---|---|---|
| `dim_scenic_spot` | 2,064 | 景区维表，99.0% 有坐标 |
| `fact_comment` | 149,354 | 真实评论（按年分区 2010-2025） |
| `mv_spot_metrics` | 2,064 | 评分分布物化视图 |
| `mv_comment_monthly` | ~3,000 | 月度趋势物化视图 |
| `mv_city_summary` | 48 | 城市汇总 |
| 覆盖范围 | 36/37 城市 | 96% 数据集中在湖北省 |

## 🗂 项目结构

```
travel/
├── data/                  # 原始数据（gitignored, 1.2 GB）
├── pipelines/             # ETL 流水线（DuckDB → Parquet → PG）
│   ├── etl.sql            # 双 schema CSV 清洗 + dedup
│   ├── parse_txt.py       # TXT 详情解析
│   ├── geocode.py         # 高德 Geocoding
│   ├── load_to_pg.py      # DuckDB ATTACH PG 直灌
│   └── run.py             # CLI 入口
├── db/init/               # PG 容器启动时自动跑（建表 / 索引 / 物化视图）
├── server/                # FastAPI 后端
│   └── app/
│       ├── routers/       # 16 个端点（dashboard / spots / comments / search / geocode）
│       ├── services/      # 高德 API client
│       ├── cache.py       # Redis cache_get_or_set
│       └── scheduler.py   # APScheduler 每日 3 点刷物化视图
├── client/                # Vue 3 前端
│   └── src/
│       ├── views/         # Dashboard / Explore / SpotDetail
│       ├── components/charts/  # 9 个 ECharts 组件
│       ├── stores/        # Pinia
│       └── api/           # axios + 强类型
├── docker-compose.yml     # 4 service：postgres + redis + api + web
├── ARCHITECTURE.md        # 架构总览 + 关键决策记录
└── README.md              # 本文档
```

## 📡 API 速查

> 全部前缀 `/api/v1`，详见 http://localhost:8000/docs

| 端点 | 用途 |
|---|---|
| `GET /dashboard/global-kpi` | 4 个 KPI 总数 |
| `GET /dashboard/heatmap` | 全国景区热力点（2043 点） |
| `GET /dashboard/spots/top` | Top N 评论数景区 |
| `GET /dashboard/level-dist` | 景区等级分布 |
| `GET /dashboard/wordcloud` | 评论关键词云 |
| `GET /dashboard/spots/{id}/monthly` | 单景区月度趋势 |
| `GET /spots` | 分页列表（含 `X-Total-Count` header） |
| `GET /spots/{id}` | 景区详情 |
| `GET /spots/{id}/comment-distribution` | 评分分布 |
| `GET /spots/cities/list` | 城市选项（含 spot_count） |
| `GET /comments` | 评论游标分页（无 OFFSET） |
| `GET /search/spots` | 关键词搜索（PG zhparser） |
| `GET /search/nearby` | PostGIS 半径搜索 |
| `GET /geocode` | 高德代理（服务端缓存） |

## 🛠 ETL 命令

```bash
uv run python -m pipelines.run clean     # CSV → Parquet（DuckDB SQL）
uv run python -m pipelines.run txt       # TXT 详情解析
uv run python -m pipelines.run enrich    # rapidfuzz 模糊回填
uv run python -m pipelines.run geocode   # 高德坐标
uv run python -m pipelines.run load      # Parquet → PG
uv run python -m pipelines.run all       # 全流程（不含 load）
uv run python -m pipelines.run stats     # 数据质量摘要
```

## 🩺 故障排查

| 症状 | 处理 |
|---|---|
| `docker compose up` 后大屏白屏 | PG 是空的。先放数据到 `data/csv/` + `data/txt/`，再跑 `docker compose --profile bootstrap up etl` |
| `etl` 容器以退出码 2 退出 | `data/csv/` 没有 CSV。放好数据后重跑 `--profile bootstrap up etl`（幂等） |
| API `/healthz` 200 但 dashboard 全 0 | PG 还没数据，跑 `--profile bootstrap up etl` |
| 高德 geocoding 报 daily quota | 切换 key 或 sleep_sec 调大 |
| `127.0.0.1` 走代理 connection refused | Windows 上 curl 加 `--noproxy "*"` |
| Vite dev fps 远低于 prod | dev 模式 HMR 开销，正式测性能请用 `npm run build && preview` |

## 🔐 安全约定

- `.env` / `server/.env` 已 gitignore，包含真实 `AMAP_API_KEY`
- **服务端 Key（Web 服务类型）** 不可写入代码 / commit / 前端 bundle
- **前端 JSAPI Key**（如启用）必须先在高德控制台配置域名白名单

## 📐 架构决策

详见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

## 运行结果
<img width="1847" height="897" alt="11" src="https://github.com/user-attachments/assets/6053d8cd-b0e4-4479-afa0-e84a59f060a7" />

<img width="1868" height="898" alt="22" src="https://github.com/user-attachments/assets/7719392d-4e09-4c27-a2ec-1c6bb46aa7fc" />

<img width="1845" height="922" alt="33" src="https://github.com/user-attachments/assets/6fde6e07-e012-41c4-b4bd-52a3cfdc77f2" />


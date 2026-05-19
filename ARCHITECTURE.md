# 架构总览

## 数据流

```
┌────────────────┐   DuckDB SQL    ┌────────────┐   COPY     ┌──────────────┐
│ data/csv (1.1G)│ ──────────────► │  staging   │ ────────► │   Parquet    │
│ data/txt (3001)│                  │  dedup     │            │  按年分区     │
└────────────────┘                  │  dim_spot  │            └──────┬───────┘
                                    └────────────┘                   │
                                          ▲                          │ ATTACH postgresql
                                          │ rapidfuzz enrich         ▼
                                          │                  ┌───────────────┐
                                    ┌────────────┐           │  PostgreSQL   │
                                    │  dim_txt   │           │  + PostGIS    │
                                    └────────────┘           │  + pg_trgm    │
                                                             │  + zhparser   │
                                          AMap Geocoding ───►│  + 物化视图    │
                                                             └──────┬────────┘
                                                                    │
                                                  Redis cache  ┌────▼──────┐
                                                  ┌────────────│  FastAPI  │
                                                  │            │  (async)  │
                                                  │            └────┬──────┘
                                                  │                 │ JSON
                                                  │                 ▼
                                                  │           ┌──────────┐
                                                  └──────────►│  Vue 3   │
                                                              │  ECharts │
                                                              └──────────┘
```

## 关键决策

| 决策点 | 选择 | 原因 |
|---|---|---|
| ETL 引擎 | DuckDB SQL（替代 polars / pandas） | 单进程 SQL 表达力强；ATTACH postgresql 直灌；7.8s 处理 1400 万行 |
| 中间格式 | Parquet（按年分区） | 列存 zstd 压缩 + 谓词下推；DuckDB / PG 都原生读 |
| 存储 | PostgreSQL 16 + PostGIS + pg_trgm + zhparser | 替代 MySQL：分区 + 物化视图 + 中文分词 + 地理空间一体 |
| 评论分区 | 按 `year(co_time)` 声明式分区 2010-2025 | 跨年查询裁剪 + 维护单分区可剪除 |
| 后端框架 | FastAPI 0.115 async + SQLAlchemy 2.0 async + Pydantic v2 | 替代旧 Django + DRF：async I/O 极致性能 |
| Dashboard 策略 | 仅查物化视图，禁触 fact_comment 千万行 | p95 < 9ms 的关键 |
| 缓存 | Redis 7 + aiocache + 失效 TTL 分级 | dashboard 5min / detail 1h / heatmap 1h |
| 物化视图刷新 | APScheduler 每日 3 点 | 数据日级更新，无需实时 |
| 前端框架 | Vue 3.5 + Vite 6 + element-plus 2.9 + ECharts 5 + Pinia | 升级旧 Vue 2 项目；按需引入 element-plus 减体积 41% |
| 评论分页 | 游标 / cursor-based（next_cursor） | OFFSET 在百万级评论上慢；游标常数复杂度 |
| 地图缩放 | 浮动 +/⊙/− 按钮（roam: 'move'） | 滚轮让给页面滚动；通过 `userZoom` ref 驱动 `setOption` 保证 geo + scatter 同步 |
| 前端性能 | will-change + translateZ + contain | ChinaMap 滚动卡顿根因为 GPU 合成层释放，已治本 |
| 地理编码 | 高德 Web API + 二轮清洗（city_geo 兜底 → re-geocode） | 99.0% 坐标覆盖；服务端缓存 7 天 |

## 性能基准

| 接口 | p50 | p95 | 备注 |
|---|---|---|---|
| `/dashboard/global-kpi` | 1.7 ms | 4.0 ms | 0.1 KB |
| `/dashboard/city-kpi` | 1.6 ms | 2.2 ms | 2.3 KB |
| `/dashboard/spots/top` | 1.7 ms | 2.2 ms | 2.9 KB |
| `/dashboard/heatmap` | 8.0 ms | 8.7 ms | 138.6 KB |
| `/dashboard/level-dist` | 1.6 ms | 3.8 ms | 0.4 KB |
| `/dashboard/wordcloud` | 1.5 ms | 2.1 ms | 2.7 KB |

> 测试方法：httpx 20 次/端点（cache warm），单核本地

前端：Dashboard 首屏 gzip ~355 KB（element-plus 按需后），稳定 60 fps。

## 模块职责

### `pipelines/`
- 单一职责：把原始数据变成可灌库的 Parquet
- 不依赖任何运行时服务（PG/Redis）；只在 `load` 命令才连 PG
- CLI 用 typer，所有命令前自动 `load_env()`

### `db/init/`
- 容器启动时按 01-07 顺序自动跑
- 包含建表 / 索引 / 物化视图 / PG 函数 / 文本清洗 / 城市回填

### `server/`
- FastAPI lifespan 管理 engine + scheduler 生命周期
- 所有 dashboard 端点走物化视图 + Redis 缓存
- Cache key 规则：`{namespace}:{params_hash}`，失效靠 TTL 不靠主动失效

### `client/`
- Vite manualChunks：vue / echarts 单独成 chunk
- element-plus 通过 unplugin-vue-components 按需引入（不再有 ui chunk）
- ECharts：`shallowRef + markRaw` 持有实例（避免 Vue reactive 包裹）
- 全应用 china geojson 单例 + sessionStorage 缓存

## 安全边界

- `.env` 永远不入库（已 gitignore）
- 服务端高德 Key（Web 服务类型）由 pydantic-settings 加载，仅服务端持有
- `/api/v1/geocode` 是代理端点，对外暴露但 key 不外泄
- CORS 限制到 `localhost:3000` / `:5173` / `:80`（生产应缩到具体域名）

## 后续可扩展

| 方向 | 当前预留 | 工作量 |
|---|---|---|
| pgvector 向量检索 | `dim_spot.intro_vector` 字段已建 | embedding 注入 + 接口实现 |
| RAG 智能问答 | 维表 intro/notice/tips 干净长文本 | 选模型 + chunking 策略 |
| 全文搜索打分排序 | zhparser tokenizer 已启用 | 接 `/search/spots` 改用 ts_rank |
| 实时增量灌库 | 当前批处理日级 | Debezium / FDW / Kafka |
| 多租户 | 单 schema 单业务 | 加 `org_id` 列 + RLS |

## 版本

`v2-modern-stack` —— 当前架构版本号，DuckDB ETL + PostgreSQL + FastAPI + Vue 3。

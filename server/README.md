# Travel Data API

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 16 + Redis。

## 端点速查

| 路由 | 用途 |
|---|---|
| `GET /api/v1/dashboard/kpi`            | 城市级 KPI（KPI 卡） |
| `GET /api/v1/dashboard/spots/top`      | Top N 景区（Top 榜） |
| `GET /api/v1/dashboard/heatmap`        | 中国地图散点 |
| `GET /api/v1/dashboard/level-dist`     | 等级分布（饼图） |
| `GET /api/v1/dashboard/spots/{id}/monthly`  | 月度评论趋势 |
| `GET /api/v1/spots`                    | 景区分页列表 |
| `GET /api/v1/spots/{id}`               | 景区详情 |
| `GET /api/v1/comments`                 | 评论游标分页 |
| `GET /api/v1/search/spots?q=...`       | 关键词搜索 |
| `GET /api/v1/search/nearby?lon&lat&km` | 地理半径搜索 |
| `GET /api/v1/geocode?address=...`      | 高德 Geocoding 代理 |
| `GET /healthz`                         | 健康检查 |
| `GET /docs`                            | Swagger UI |

## 本地启动

```bash
cd server
pip install -e .
cp .env.example .env       # 编辑配置
uvicorn app.main:app --reload --port 8000
# 打开 http://localhost:8000/docs
```

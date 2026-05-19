# Travel Data Client (Vue 3 + ECharts)

## 快速开始

```bash
cd client
pnpm install              # 或 npm install
cp .env.development .env.local   # 按需修改 API target
pnpm dev                  # 启动 → http://localhost:3000
```

## 页面

| 路径 | 文件 | 用途 |
|---|---|---|
| `/` | `views/Dashboard.vue` | 数据大屏（KPI + 地图 + Top10 + 词云 + 趋势） |
| `/explore` | `views/Explore.vue` | 多维筛选（城市/等级/评分/关键字） |
| `/spot/:id` | `views/SpotDetail.vue` | 景区详情 + 评论列表 + 评分分布 |

## 中国地图数据

ECharts 中国地图需 GeoJSON。运行时从公共 CDN 拉取：
```ts
fetch('https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json')
```
（无需手动下载文件）

## 构建

```bash
pnpm build    # → dist/  (纯静态，可放 nginx / Vercel / CF Pages)
```

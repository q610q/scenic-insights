# ---- Stage 1: build Vue 3 SPA ----
FROM node:20-alpine AS builder

WORKDIR /app

# 仅 copy 依赖描述, 利用 docker 层缓存
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

# copy 源码并 build (产物在 /app/dist)
COPY . .
RUN npm run build

# ---- Stage 2: nginx serve + /api 反代到 api 容器 ----
FROM nginx:1.27-alpine

# 替换默认 vhost (静态 + /api proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/conf.d/default.conf.bak

# 拷贝 build 产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --spider -q http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

FROM node:18-alpine AS build

WORKDIR /app

# 先装依赖
COPY package.json package-lock.json ./
RUN npm ci

# 再复制代码并构建
COPY . .
RUN npm run build

# ========== 生产阶段：nginx 托管静态文件 + 反向代理 ==========
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# nginx 配置：静态文件直接返回，/api/ 等路径代理到后端
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Stage 1: Build the React/Vite app
FROM node:22-alpine AS build
WORKDIR /app

# 更快的缓存层：先只拷贝依赖清单
COPY package*.json ./

# 更可重复的安装方式
RUN npm ci

# 拷贝源代码并构建
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:stable-alpine
WORKDIR /usr/share/nginx/html

# 清空默认站点文件
RUN rm -rf ./*

# 从 build 阶段拷贝静态产物
COPY --from=build /app/dist .

# 使用自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

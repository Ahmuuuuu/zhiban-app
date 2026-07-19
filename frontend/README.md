
# 知伴前端

这是知伴项目的前端部分，基于 `Vue 3 + Vite`。

## 运行环境

- Node.js 18+
- npm 9+

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

默认会在本地开发地址启动。

## 构建发布

```bash
cd frontend
npm run build
```

构建产物会输出到 `frontend/dist/`。

## 接口地址

前端默认请求后端本地服务。  
如果后端不在当前机器或端口不同，可以设置：

```bash
$env:VITE_API_BASE_URL="http://127.0.0.1:2221"
npm run dev
```

## 目录说明

- `src/pages` 页面
- `src/components` 组件
- `src/api` 接口封装
- `src/router` 路由
- `src/stores` 状态管理

## 说明

如果你只是想把前端单独部署到服务器，先执行 `npm run build`，再把 `dist/` 里的文件交给 Nginx 或其他静态服务器即可。

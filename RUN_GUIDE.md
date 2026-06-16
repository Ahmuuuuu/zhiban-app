# 智伴 App 运行指南

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- Git

## 一、数据库

确保 MySQL 运行在本机 `3306`，创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS zhiban CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

表结构由 Tortoise ORM 启动时自动生成，无需手动建表。

## 二、后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（如尚未创建 .env）
# 参考 backend/.env 文件，关键变量：
#   database = mysql://root:你的密码@127.0.0.1:3306/zhiban
#   api_key = 你的LLM API Key
#   JWT_KEY = 自定义JWT密钥

# 启动（端口 2221）
uvicorn backend.src.main:app --host 0.0.0.0 --port 2221 --reload
```

### 可选：创建演示用户

```bash
cd backend
python setup_demo_user.py
```

创建用户 `1` / 密码 `11111111`，含完整学习画像和考试数据。

## 三、前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 `http://localhost:5173`，API 请求自动代理到后端 `127.0.0.1:2221`。

## 四、项目结构

```
zhiban-app/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── router/              # API 路由（14 个模块）
│   │   ├── service/             # 业务逻辑
│   │   ├── models/              # Tortoise ORM 模型（19 张表）
│   │   ├── ai_core/             # LangGraph 智能体 + Prompt 模板
│   │   └── utils/               # JWT / TTS / 知识库 / 工具函数
│   ├── static/                  # 静态文件（课件 HTML / 音频 / 封面）
│   ├── migrations/              # SQL 迁移脚本
│   ├── requirements.txt
│   └── .env                     # 环境变量（不提交）
├── frontend/
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── composables/         # 组合式 API
│   │   ├── router/              # Vue Router（Hash 模式）
│   │   ├── stores/              # Pinia 状态管理
│   │   └── assets/              # 样式 / 图片
│   ├── index.html
│   ├── vite.config.js           # Vite 配置（含 API 代理）
│   └── package.json
└── RUN_GUIDE.md
```

## 五、技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| ORM | Tortoise ORM + aiomysql |
| AI 编排 | LangGraph（Leader → Executor → Reviewer） |
| LLM | DeepSeek Chat API |
| TTS | Microsoft EdgeTTS |
| 前端框架 | Vue 3 + Vite |
| 状态管理 | Pinia |
| 路由 | Vue Router（Hash 模式） |
| 样式 | Tailwind CSS 4 + SCSS |
| 数学渲染 | KaTeX |
| 思维导图 | mind-elixir |

## 六、常见问题

**后端启动报数据库连接失败**：确认 MySQL 已启动，`.env` 中连接字符串正确。

**前端页面空白**：确认后端已启动在 2221 端口，前端 Vite 代理依赖后端运行。

**首次启动 BGE 模型下载慢**：后端启动时会下载 sentence-transformers 的 BGE 嵌入模型到本地缓存，仅首次需要。

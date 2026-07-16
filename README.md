# 知伴 Zhiban

知伴是一个面向学生的 AI 学习伙伴平台。它不是单纯的聊天机器人，而是围绕「学习画像 -> 学习路径 -> 知识资料 -> 多类型资源生成 -> 视频讲解 -> 练习反馈」构建的一套学习闭环。

项目目前以 Python/FastAPI 承担智能体、资源生成和知识库能力，以 Vue 3 承担前端交互体验。系统重点强化了个性化学习、流式资源生成、多智能体过程可视化和知识库参考能力。

## 核心能力

- **AI 对话学习伙伴**：支持自然语言问答、学习建议、资源生成请求识别，并结合用户画像给出更像朋友的回答。
- **学习画像**：根据用户的专业、年级、学习目标、对话行为和基础画像问答，逐步沉淀用户的学习特征。
- **学习路径规划**：用户完善专业年级后，系统可自动生成阶段化学习路径，并在节点推进后扩展后续任务。
- **多类型资源生成**：支持 Word/文档、PPT、思维导图、练习题、图片和学习视频等资源。
- **个性化学习视频**：视频由分段课件、TTS 音频和字幕高亮组成，请求后可优先生成画像结合学科的引入段，让用户尽快听到内容。
- **知识库 / RAG**：用户可上传私有资料，管理员可维护公共资料；系统通过向量检索把资料作为参考上下文，而不是默认强制引用。
- **资源中心**：支持公开资源浏览、预览、播放、下载、收藏、点赞和资料可见性管理。
- **智能体工作流可视化**：资源生成时展示需求规划、并行生成、质量审核、保存资源、完成等过程，便于用户理解系统正在做什么。
- **学习情况追踪**：沉淀学习记录、练习结果、路径进度、通知和画像雷达等数据。
- **管理后台**：用于用户、资源、公共资料和平台数据管理。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Vue 3, Vite, Pinia, Vue Router, SCSS/Tailwind, lucide-vue-next |
| 后端 | FastAPI, Uvicorn, Pydantic |
| 数据库 | MySQL 8, Tortoise ORM, aiomysql |
| 缓存/消息 | Redis 可选；不可用时 SSE 降级为单进程模式 |
| 智能体 | LangGraph, LangChain, OpenAI-compatible LLM API |
| 向量检索 | sentence-transformers, BGE 中文嵌入模型 |
| 资源生成 | python-docx, python-pptx, pdfminer.six, mind-elixir |
| 语音 | EdgeTTS / 讯飞 TTS 配置 |
| 定时任务 | APScheduler |

## 项目结构

```text
zhiban-app/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI 入口、路由注册、静态文件挂载
│   │   ├── router/              # API 路由
│   │   ├── service/             # 业务服务：聊天、资源、视频、路径、画像等
│   │   ├── models/              # Tortoise ORM 数据模型
│   │   ├── ai_core/             # 智能体图、LLM 配置、Prompt、工具
│   │   └── utils/               # 数据库、JWT、知识库、TTS、JSON 解析等工具
│   ├── static/                  # 生成文件、音频、视频、课件、图片等
│   ├── tests/
│   ├── requirements.txt
│   └── .env                     # 本地后端环境变量，不提交
├── frontend/
│   ├── src/
│   │   ├── pages/               # 页面
│   │   ├── components/          # 组件
│   │   ├── composables/         # 组合式逻辑
│   │   ├── api/                 # 前端请求封装
│   │   ├── router/              # 路由
│   │   └── stores/              # Pinia 状态
│   ├── package.json
│   └── vite.config.js
├── deploy/
├── docker-compose.yml
├── RUN_GUIDE.md                 # 更偏运行步骤的补充说明
└── README.md
```

## 本地运行

### 1. 准备环境

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- 可选：Redis

创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS zhiban CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 配置后端环境变量

本地开发时，后端默认读取 `backend/.env`。可以参考根目录 `.env.example` 创建：

```bash
copy .env.example backend\.env
```

关键配置：

```env
database=mysql://root:你的密码@127.0.0.1:3306/zhiban
api_key=你的大模型 API Key
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
JWT_KEY=至少 32 位的 JWT 密钥
ALGORITHM=HS256

SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=你的邮箱
SMTP_PASS=邮箱授权码

XF_APP_ID=
XF_API_KEY=
XF_API_SECRET=
```

说明：Docker 部署时使用根目录 `.env`；本地直接启动后端时使用 `backend/.env`。

### 3. 启动后端

在项目根目录执行：

```bash
pip install -r backend/requirements.txt
uvicorn backend.src.main:app --host 0.0.0.0 --port 2221 --reload
```

后端默认端口为 `2221`，Swagger 文档可访问：

```text
http://127.0.0.1:2221/docs
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在：

```text
http://127.0.0.1:5173
```

前端请求默认连接当前主机的 `2221` 端口；也可以通过 `VITE_API_BASE_URL` 指定后端地址：

```bash
$env:VITE_API_BASE_URL="http://127.0.0.1:2221"
npm run dev
```

## Docker 运行

根目录提供了 `docker-compose.yml`，会启动 MySQL、后端和前端：

```bash
copy .env.example .env
docker compose up --build
```

服务端口：

- 前端：`http://127.0.0.1`
- 后端：`http://127.0.0.1:2221`
- MySQL：`127.0.0.1:3306`

## 知识库策略

知伴的 RAG 设计目标是「参考增强」，不是「资料绑架」。

- 上传资料后，后端会抽取文本、切片、生成向量并写入数据库。
- 检索时会同时考虑用户私有资料和已公开/审核通过的公共资料。
- 系统默认把检索结果作为参考上下文，帮助回答更贴近课程资料。
- 当用户明确要求「只根据资料回答」时，才进入更严格的资料约束模式。
- 资料不足或命中质量不高时，应允许模型基于通用知识解释，并提醒资料可能不完整。

## 资源生成链路

资源生成由多智能体流程驱动：

```text
用户请求
  -> 需求规划
  -> 文档 / PPT / 思维导图 / 习题 / 视频等资源并行生成
  -> 质量审核
  -> 保存资源
  -> 前端卡片与智能体工作流同步更新
```

视频生成是当前项目的重要亮点：

- 视频请求后，优先生成「学科 + 用户画像」结合的开场引入。
- 文案、TTS 和片段制作按章节推进，尽量让用户尽早听到声音。
- 前端播放器根据片段完成状态控制可点击范围，未完成片段不会误点。
- 字幕高亮通过课件模板内注入的 karaoke word 样式实现。

## 开发注意事项

- 不要提交 `backend/.env`、根目录 `.env`、数据库文件、生成音视频和大模型缓存。
- `backend/static/` 下主要是运行期生成文件，清理前要确认是否仍被资源记录引用。
- BGE 模型首次加载可能较慢，后续会使用本地缓存。
- Redis 不可用时系统会降级，但多进程 SSE 推送能力会受影响。
- 学习路径资源生成和聊天资源生成都依赖任务 ID / 会话 ID 绑定，改前端任务队列时要避免不同会话串线。
- RAG 资料越多越需要控制检索 TopK、切片质量和引用策略，避免无关资料干扰回答。

## 常用命令

```bash
# 前端构建
cd frontend
npm run build

# 后端基础语法检查示例
python -m py_compile backend/src/utils/json_parser.py

# 启动后端
uvicorn backend.src.main:app --host 0.0.0.0 --port 2221 --reload
```

## 项目状态

这是一个持续迭代中的学习平台项目，当前重点已经从 Demo 形态转向真实可用体验：

- 更稳定的资源生成任务绑定
- 更快的视频首段语音体验
- 更清晰的智能体工作流展示
- 更合理的 RAG 参考策略
- 更完整的学习路径、资源中心和画像闭环


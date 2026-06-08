# 知伴 — 后端

基于 FastAPI + LangGraph 的 AI 学习平台后端，采用两层智能体架构（Brain 顶层调度 + 资源生成子图），支持学习路径规划、多类型学习资源生成、动态课件制作和个性化出题。

## 技术栈

| 层面 | 组件 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| ORM | Tortoise ORM + aiomysql |
| AI 编排 | LangGraph (StateGraph) |
| LLM | DeepSeek (via langchain-openai) |
| 向量检索 | sentence-transformers (BGE) |
| 语音合成 | EdgeTTS |
| 图片生成 | 讯飞 HiDream |
| 文档处理 | python-docx / python-pptx / pdfminer |
| 定时任务 | APScheduler |

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（复制 .env.example 为 .env 并填写）
#   database=mysql://user:pass@host:3306/dbname
#   DEEPSEEK_API_KEY=sk-xxx
#   DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
#   DEEPSEEK_MODEL=deepseek-chat
#   XF_APP_ID=xxx
#   XF_API_SECRET=xxx
#   XF_API_KEY=xxx
#   SECRET_KEY=xxx
#   JWT_ALGORITHM=HS256

# 3. 启动服务
uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档启动后访问 `http://127.0.0.1:8000/docs`。

## 目录结构

```
backend/
├── src/
│   ├── main.py                  # FastAPI 入口，路由注册，中间件
│   ├── ai_core/                 # AI 核心
│   │   ├── brain.py                 Brain — 顶层智能体 + 工具注册
│   │   ├── resource_graph.py        资源生成 LangGraph 子图
│   │   ├── llm_config.py            LLM 配置
│   │   ├── prompts/                 提示词模板 (YAML)
│   │   │   ├── chat/                    主聊天 system prompt
│   │   │   ├── resource/                文档/PPT/思维导图/习题/图片
│   │   │   ├── agent/                   Leader/Reviewer/专用审核员
│   │   │   └── path/                    学习路径规划
│   │   └── tools/                   工具实现 (20+ 工具)
│   ├── router/                   # API 路由 (17 个)
│   ├── service/                  # 业务逻辑层 (16 个)
│   ├── models/                   # Tortoise ORM 数据模型 (17 个)
│   ├── schemas/                  # Pydantic 请求/响应模型
│   ├── utils/                    # 工具模块
│   │   ├── database.py               Tortoise 初始化 + 模型注册
│   │   ├── jwt.py                    JWT 认证
│   │   ├── prompt_loader.py          提示词加载 + 变量填充
│   │   ├── json_parser.py            LLM JSON 输出解析
│   │   ├── knowledge_base.py         向量知识库 (BGE)
│   │   ├── pptx_generator.py         Markdown → PPTX 转换
│   │   ├── tts_utils.py              EdgeTTS 封装
│   │   ├── email_sender.py           SMTP 邮件发送
│   │   └── scheduler.py              定时任务
│   └── static/                   # 生成文件 (gitignored)
├── migrations/                  # SQL 迁移文件
├── requirements.txt
└── .env                         # 环境变量 (gitignored)
```

## 架构

### 两层智能体

```
用户消息 → Brain (顶层) → 工具调用 → resource_graph (子图)
                  │                        │
                  │ 上下文注入:              │ Leader → Executor×N → Reviewer×N
                  │ · 用户画像               │  ↑_______retry≤2___________|
                  │ · 六维雷达
                  │ · 课程体系               生成能力:
                  │ · 对话历史               · LLM 文本/习题/PPT markdown
                  │                          · 讯飞 HiDream 图片
                                             · EdgeTTS 语音
                                             · python-pptx 文档
```

### 资源生成管线

1. **Leader** — 分析主题，决定资源类型（用户可指定跳过 LLM）
2. **Executor** — `ThreadPoolExecutor` 并行生成每个类型，信号量限流 max=5
3. **Reviewer** — 每种类型独立审核（exercise 有专用逐题审核），未通过重试最多 2 次
4. 学习路径场景设置 `skip_review=True` 跳过审核加速生成

### 上下文注入链

每次对话自动注入三段上下文：

| 上下文 | 来源 | 示例 |
|--------|------|------|
| 用户背景 | `User.major/grade/university` | "专业：智能科学与技术、年级：大三" |
| 专业课程 | `User_picture.traits.curriculum_courses` | "机器学习、深度学习、NLP..." |
| 画像摘要 | `User_picture.traits` + 雷达图 + 学习指导 | 强项/弱项/知识点掌握度 |

## API 路由一览

| 路由前缀 | 文件 | 说明 |
|----------|------|------|
| `/user` | user_router.py | 用户注册/登录/信息管理 |
| `/chat` | chat_router.py | AI 对话（SSE 流式） |
| `/resource` | resource_router.py | 资源生成/列表/下载/点赞收藏 |
| `/exam` | exam_router.py | 题目生成/提交/判分 |
| `/image` | image_router.py | 图片生成 |
| `/knowledge` | knowledge_router.py | 知识库 CRUD + 搜索 |
| `/portrait` | portrait_router.py | 用户画像 |
| `/path` | path_router.py | 学习路径 CRUD |
| `/learning-path` | learning_path_router.py | 学习路径新接口 |
| `/presentation` | presentation_router.py | 动态课件生成 |
| `/video` | video_router.py | 视频资源 |
| `/study` | study_router.py | 学习统计/心跳 |
| `/annotation` | annotation_router.py | 资源笔记批注 |
| `/notification` | notification_router.py | 通知消息 |
| `/admin` | admin_router.py | 管理接口 |

## 数据模型

| 模型 | 表名 | 说明 |
|------|------|------|
| User | sys_user | 用户（JWT 认证） |
| ChatHistory | chat_history | 对话历史 |
| GeneratedResource | generated_resources | AI 生成的学习资源 |
| ResourceAnnotation | resource_annotations | 用户对资源的笔记批注 |
| ExamQuestion | exam_questions | 考题 |
| ExamRecord | exam_records | 考试记录 |
| KnowledgeMastery | knowledge_mastery | 知识点掌握度 |
| UserPicture | user_picture | 用户画像 |
| PortraitRadar | portrait_radar | 六维能力雷达 |
| KnowledgeBase | knowledge_base | 知识库文档 |
| AgentSkill | agent_skills | 自定义 Agent 技能 |
| ImageRecord | image_records | AI 生成的图片 |
| Path | learning_paths | 学习路径 |
| PathNode | learning_path_nodes | 路径节点 |
| UserPathProgress | user_path_progress | 用户路径进度 |
| Presentation | presentations | 动态课件 |
| Narration | narration_records | 语音旁白 |
| StudySession | study_sessions | 学习计时 |
| Notification | notifications | 通知 |
| CurriculumCourse | curriculum_courses | 大学课程体系 |
| EmailCode | email_verification_codes | 邮箱验证码 |
| GenerationTask | generation_tasks | 后台生成任务 |

## 开发约定

### 统一响应格式
```json
{"code": 200, "msg": "success", "data": {...}}
```

### 认证
所有需要登录的端点使用 `user_id: int = Depends(get_user_id_from_token)` 获取当前用户。

### 路由 → Service → Model 分层
- **Router** 只做参数解析和响应包装，不写业务逻辑
- **Service** 承载业务逻辑，使用静态方法
- **Model** 定义数据结构，不写查询逻辑

### 新增实体 Checklist
1. `migrations/add_xxx.sql` — 建表 SQL
2. `src/models/xxx_model.py` — Tortoise 模型
3. `src/schemas/xxx.py` — Pydantic schema
4. `src/service/xxx_service.py` — 业务逻辑
5. `src/router/xxx_router.py` — API 路由
6. `src/utils/database.py` — 注册模型模块路径
7. `src/main.py` — 注册路由

### AI 提示词管理
所有 prompt 存放在 `src/ai_core/prompts/` 下 YAML 文件，通过 `load_prompt(path)` 加载，`fill_prompt(template, **vars)` 填充变量。`{variable}` 占位符在填充时替换，未提供的变量保留原样传给 LLM。

# 模拟课堂端到端联调清单

检查时间：2026-08-17

## 当前检查结果

已通过：

- 前端构建：`npm.cmd run build` 通过。
- 后端模拟课堂相关 Python 文件：`py_compile` 通过。
- 前后端入口已连通：
  - 前端路由：`/mock-classroom`
  - 后端路由：`/mock-classroom`
  - 静态目录：`/static/mock-classroom`

当前阻塞：

- 项目根目录没有发现 `.venv`、`venv` 或 `env`。
- 当前默认 Python 环境没有安装后端依赖：`fastapi`、`tortoise-orm`、`httpx`、`python-dotenv`、`langchain-openai`、`ultralytics` 等。
- `backend/.env` 不存在，因此数据库、LLM、ASR 等配置还没有落到本地。

## 本地运行环境准备

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

如果只想先用 Docker 跑数据库和 Redis：

```powershell
docker compose up -d mysql redis
```

## backend/.env 最小配置

在 `backend/.env` 中配置，密钥值不要提交到 Git：

```text
database=mysql://root:123456@127.0.0.1:3306/zhiban
api_key=你的 LLM key
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
JWT_KEY=zhiban-jwt-secret
ALGORITHM=HS256
REDIS_URL=redis://127.0.0.1:6379/0

STUDY_ROOM_YOLO_ENABLED=true
STUDY_ROOM_YOLO_MODEL=yolo26n.pt

MOCK_CLASSROOM_ASR_ENABLED=true
MOCK_CLASSROOM_ASR_URL=https://api.openai.com/v1/audio/transcriptions
MOCK_CLASSROOM_ASR_API_KEY=你的 ASR key
MOCK_CLASSROOM_ASR_MODEL=whisper-1
MOCK_CLASSROOM_ASR_TIMEOUT_SECONDS=120
```

ASR 也可以只配置 `OPENAI_API_KEY`，系统会默认使用 OpenAI 兼容的 `/v1/audio/transcriptions` 地址。

## 启动命令

后端：

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="D:\知伴app"
uvicorn backend.src.main:app --host 127.0.0.1 --port 2221
```

前端：

```powershell
cd frontend
npm.cmd run dev
```

访问：

```text
http://127.0.0.1:5173/#/mock-classroom
```

## 手动端到端验证流程

1. 登录用户账号。
2. 进入“模拟课堂”。
3. 输入讲解主题和参考要点。
4. 检查摄像头和麦克风授权。
5. 点击开始讲课。
6. 讲 20-60 秒，确认右侧帧数量会变化。
7. 点击结束讲课。
8. 等待报告状态从“报告生成中”变成“报告已生成”。
9. 检查报告内容：
   - 综合分
   - 知识理解
   - 讲解熟练度
   - 表达状态
   - 文字稿或 ASR 状态提示
   - 优点、漏洞、建议
   - 镜头状态摘要

## 常见问题

- 如果报告显示未配置 ASR：检查 `MOCK_CLASSROOM_ASR_API_KEY` 或 `OPENAI_API_KEY`。
- 如果知识理解分偏占位：说明没有拿到有效文字稿，需要先确认音频上传和 ASR。
- 如果表达状态一直不准：先确认 YOLO 模型能加载，再检查摄像头画面是否太暗、脸部是否出画。
- 如果后端启动时卡在模型加载：首次加载 BGE/YOLO 可能较慢，Docker 镜像构建时也可能下载模型。
- 如果前端提示后端连接失败：确认后端在 `127.0.0.1:2221`，或设置 `VITE_API_BASE_URL`。

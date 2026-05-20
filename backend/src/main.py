from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
from pathlib import Path
from backend.src.utils.database import init_db, close_db
from backend.src.router.chat_router import router as chat_router
from backend.src.router.portrait_router import router as portrait_router
from backend.src.router.resource_router import router as resource_router
from backend.src.router.image_router import router as image_router
from backend.src.router.knowledge_router import router as knowledge_router
from backend.src.router.user_router import router as user_router
from backend.src.router.admin_router import router as admin_router
from backend.src.utils.jwt import create_access_token

app = FastAPI(
    title="AI聊天后端",
    description="Swagger接口文档",
    swagger_ui_init_oauth={},
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)

# 静态文件服务（图片生成等）
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "images").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def hello():
    return {"hello": "user"}


@app.post("/get_token")
async def get_token(user_id: int):
    return {"token": create_access_token(user_id)}


@app.on_event("startup")
async def startup():
    await init_db()
    # 预加载 BGE 模型，避免首次知识库操作时等待下载/加载
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _preload_bge_model)


def _preload_bge_model():
    from backend.src.utils.knowledge_base import _get_embed_model
    _get_embed_model()


@app.on_event("shutdown")
async def shutdown():
    await close_db()


app.include_router(user_router)
app.include_router(chat_router)
app.include_router(portrait_router)
app.include_router(resource_router)
app.include_router(image_router)
app.include_router(knowledge_router)
app.include_router(admin_router)

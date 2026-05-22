from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from backend.src.utils.database import init_db, close_db
from backend.src.router.chat_router import router as chat_router
from backend.src.router.portrait_router import router as portrait_router
from backend.src.router.resource_router import router as resource_router
from backend.src.router.image_router import router as image_router
from backend.src.router.knowledge_router import router as knowledge_router
from backend.src.router.user_router import router as user_router
from backend.src.router.admin_router import router as admin_router
from backend.src.router.exam_router import router as exam_router
from backend.src.router.path_router import router as path_router
from backend.src.router.learning_path_router import router as learning_path_router
app = FastAPI(
    title="AI聊天后端",
    description="Swagger接口文档",
    swagger_ui_init_oauth={},
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务（图片生成等）
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "images").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def hello():
    return {"hello": "user"}


@app.on_event("startup")
async def startup():
    await init_db()
    # 预加载 BGE 模型，避免首次知识库操作时等待下载/加载
    from backend.src.utils.knowledge_base import _get_embed_model_async
    await _get_embed_model_async()


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
app.include_router(exam_router)
app.include_router(path_router)
app.include_router(learning_path_router)

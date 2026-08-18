import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from tortoise import Tortoise

_DEFAULT_SQLITE_DB = Path(__file__).resolve().parents[2] / "dev.sqlite3"
# database.py 可能在 main.py 加载 .env 之前被其他模块导入，因此这里必须
# 自己加载项目配置，避免开发环境误退回 SQLite。
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
database = os.getenv("database") or f"sqlite://{_DEFAULT_SQLITE_DB.as_posix()}"
# 连接池参数：默认最小5、最大20
if "mysql://" in database and "minsize" not in database:
    sep = "&" if "?" in database else "?"
    database = f"{database}{sep}minsize=5&maxsize=20"

#幂等初始化连接数据库，防止数据库重复连接
_DB_INITIALIZED = False
_DB_INIT_LOCK = asyncio.Lock()

async def _ensure_generated_resource_visibility_column():
    import logging
    _log = logging.getLogger(__name__)
    conn = Tortoise.get_connection("default")
    for sql in [
        "ALTER TABLE generated_resources ADD COLUMN visibility VARCHAR(10) NOT NULL DEFAULT 'private'",
        "ALTER TABLE generated_images ADD COLUMN visibility VARCHAR(10) NOT NULL DEFAULT 'private'",
        "ALTER TABLE chat_history ADD COLUMN agent_id INT NULL",
        "ALTER TABLE user_agents ADD COLUMN is_system INT NOT NULL DEFAULT 0",
        # 学习路径服务于个体用户：存量数据统一置为私有
        "UPDATE learning_paths SET is_public = 0 WHERE is_public = 1",
    ]:
        try:
            await conn.execute_query(sql)
        except Exception:
            _log.debug("ALTER TABLE 跳过（列可能已存在）: %s", sql[:60])

async def _ensure_classroom_lesson_schema():
    """Keep the current classroom snapshot table aligned with the lesson protocol."""
    import logging
    _log = logging.getLogger(__name__)
    conn = Tortoise.get_connection("default")
    try:
        await conn.execute_query(
            "ALTER TABLE classroom_lessons MODIFY COLUMN schema_version "
            "VARCHAR(24) NOT NULL DEFAULT 'exercise-v2' COMMENT '课堂协议版本'"
        )
    except Exception:
        # SQLite and already-compatible MySQL schemas both land here harmlessly.
        _log.debug("课堂表协议版本迁移跳过", exc_info=True)

async def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED :
        return 
    async with _DB_INIT_LOCK:
        if _DB_INITIALIZED:
            return
        await Tortoise.init(
            db_url=database,
            modules={"models": ["backend.src.models.usermodel", "backend.src.models.chat_history_model", "backend.src.models.portraitmodel", "backend.src.models.portrait_radar_model", "backend.src.models.knowledgemodel", "backend.src.models.resource_model", "backend.src.models.agent_skill_model", "backend.src.models.image_model", "backend.src.models.exam_model", "backend.src.models.path_model", "backend.src.models.narration_model", "backend.src.models.study_model", "backend.src.models.study_room_model", "backend.src.models.mock_classroom_model", "backend.src.models.video_model", "backend.src.models.task_model", "backend.src.models.email_code_model", "backend.src.models.notification_model", "backend.src.models.curriculum_model", "backend.src.models.annotation_model", "backend.src.models.user_agent_model", "backend.src.models.memory_kv_model", "backend.src.models.memory_episode_model", "backend.src.models.memory_message_model", "backend.src.models.memory_summary_model", "backend.src.models.classroom_model"]}
        )
        await Tortoise.generate_schemas()
        await _ensure_generated_resource_visibility_column()
        await _ensure_classroom_lesson_schema()
        _DB_INITIALIZED = True

async def close_db():
    await Tortoise.close_connections()

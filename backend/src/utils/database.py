from pathlib import Path
from tortoise import Tortoise
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")

database = os.getenv("database")
# 连接池参数：默认最小5、最大20
if "mysql://" in database and "minsize" not in database:
    sep = "&" if "?" in database else "?"
    database = f"{database}{sep}minsize=5&maxsize=20"

#幂等初始化连接数据库，防止数据库重复连接
_DB_INITIALIZED = False

async def _ensure_generated_resource_visibility_column():
    import logging
    _log = logging.getLogger(__name__)
    conn = Tortoise.get_connection("default")
    for sql in [
        "ALTER TABLE generated_resources ADD COLUMN visibility VARCHAR(10) NOT NULL DEFAULT 'private'",
        "ALTER TABLE generated_images ADD COLUMN visibility VARCHAR(10) NOT NULL DEFAULT 'private'",
    ]:
        try:
            await conn.execute_query(sql)
        except Exception:
            _log.debug("ALTER TABLE 跳过（列可能已存在）: %s", sql[:60])

async def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED :
        return 
    await Tortoise.init(
        db_url=database,
        modules={"models": ["backend.src.models.usermodel", "backend.src.models.chat_history_model", "backend.src.models.portraitmodel", "backend.src.models.portrait_radar_model", "backend.src.models.knowledgemodel", "backend.src.models.resource_model", "backend.src.models.agent_skill_model", "backend.src.models.image_model", "backend.src.models.exam_model", "backend.src.models.path_model", "backend.src.models.narration_model", "backend.src.models.study_model", "backend.src.models.presentation_model", "backend.src.models.task_model", "backend.src.models.email_code_model", "backend.src.models.notification_model", "backend.src.models.curriculum_model", "backend.src.models.annotation_model"]}
    )
    await Tortoise.generate_schemas()
    await _ensure_generated_resource_visibility_column()
    _DB_INITIALIZED = True

async def close_db():
    await Tortoise.close_connections()

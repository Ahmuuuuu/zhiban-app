"""项目全局常量 — 路径、TTL、超时等统一管理"""

from pathlib import Path

# ── 项目根目录 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/ 的父目录

# ── 静态文件 ──
STATIC_DIR = PROJECT_ROOT / "backend" / "static"
IMAGES_DIR = STATIC_DIR / "images"
AUDIO_DIR = STATIC_DIR / "audio"
VIDEOS_DIR = STATIC_DIR / "videos"
PRESENTATIONS_DIR = STATIC_DIR / "presentations"
AVATARS_DIR = STATIC_DIR / "avatars"
PPT_DIR = STATIC_DIR / "ppt"
COVERS_DIR = STATIC_DIR / "covers"

# ── 环境变量文件 ──
ENV_FILE = PROJECT_ROOT / ".env"

# ── 缓存 TTL（秒） ──
TTS_CACHE_TTL = 604800     # 7 天
EMBED_CACHE_TTL = 86400    # 24 小时
TASK_CACHE_TTL_RUNNING = 30
TASK_CACHE_TTL_DONE = 300

# ── 超时（秒） ──
LLM_REQUEST_TIMEOUT = 120
TTS_TIMEOUT = 120
SSE_POLL_TIMEOUT = 60
REDIS_SOCKET_TIMEOUT = 10
REDIS_CONNECT_TIMEOUT = 5
SMTP_TIMEOUT = 10
EMAIL_CODE_EXPIRE_MINUTES = 10

# ── 清洗 ──
CLEANUP_AGE_SECONDS = 86400  # 1 天

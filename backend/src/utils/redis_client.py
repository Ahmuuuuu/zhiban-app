"""Redis 连接管理"""

import os
import logging
import redis.asyncio as redis

logger = logging.getLogger("redis")

_pool: redis.Redis | None = None


async def init_redis() -> None:
    """初始化 Redis 连接池"""
    global _pool
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        _pool = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await _pool.ping()
        logger.info("Redis 连接成功 %s", redis_url)
    except Exception:
        logger.warning("Redis 连接失败 %s，将跳过缓存功能", redis_url, exc_info=True)
        _pool = None


async def get_redis() -> redis.Redis | None:
    """获取 Redis 客户端（未连接时返回 None）"""
    return _pool


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Redis 连接已关闭")

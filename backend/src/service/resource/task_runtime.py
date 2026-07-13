"""Runtime helpers for background resource generation tasks."""

from __future__ import annotations

import json
import logging

from backend.src.utils.constants import TASK_CACHE_TTL_DONE, TASK_CACHE_TTL_RUNNING
from backend.src.utils.redis_client import (
    get_redis,
    notify_sse,
    replay_sse,
    subscribe_sse,
    unsubscribe_sse,
)

logger = logging.getLogger(__name__)


def task_channel(task_id: str) -> str:
    return f"task:{task_id}"


def subscribe_task_sse(task_id: str):
    return subscribe_sse(task_channel(task_id))


def unsubscribe_task_sse(task_id: str, q: list):
    unsubscribe_sse(task_channel(task_id), q)


async def notify_task_sse(task_id: str, data: dict):
    await notify_sse(task_channel(task_id), data)


async def cache_task_state(task_id: str, state: dict):
    try:
        r = await get_redis()
        ttl = TASK_CACHE_TTL_DONE if state.get("status") in ("success", "failed") else TASK_CACHE_TTL_RUNNING
        await r.setex(f"task:{task_id}:state", ttl, json.dumps(state, ensure_ascii=False))
    except Exception:
        logger.debug(
            "Task state cache failed task_id=%s status=%s; continuing without cache",
            task_id,
            state.get("status"),
        )


async def read_cached_task_state(task_id: str, user_id: int) -> dict | None:
    try:
        r = await get_redis()
        cached = await r.get(f"task:{task_id}:state")
        if not cached:
            return None
        state = json.loads(cached)
        if state.get("user_id") == user_id and state.get("status") in ("success", "failed"):
            return state
    except Exception:
        logger.debug("Task cache read failed task_id=%s; falling back to database", task_id)
    return None

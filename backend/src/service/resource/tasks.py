"""Generation task lifecycle for resource creation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from backend.src.models.task_model import GenerationTask
from backend.src.service.resource.metadata import normalize_ppt_theme_id
from backend.src.service.resource.task_runtime import (
    cache_task_state,
    get_redis,
    read_cached_task_state,
)

logger = logging.getLogger(__name__)

EnsureChatGroup = Callable[[int, int, bool], Awaitable[int]]
RunGenerationTask = Callable[..., Awaitable[None]]


def _json_loads_or(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _task_to_state(task: GenerationTask, user_id: int) -> dict:
    return {
        "task_id": task.task_id,
        "topic": task.topic,
        "resource_types": _json_loads_or(task.resource_types, []),
        "chat_group_id": task.chat_group_id,
        "status": task.status,
        "progress": task.progress,
        "progress_msg": task.progress_msg,
        "result": _json_loads_or(task.result, None),
        "error": task.error,
        "created_at": str(task.created_at),
        "updated_at": str(task.updated_at),
        "user_id": user_id,
    }


class ResourceTaskService:
    """Create, query, and recover background resource generation tasks."""

    @staticmethod
    async def create_task(
        topic: str,
        user_id: int,
        resource_types: list[str],
        chat_group_id: int = 0,
        answers: dict | None = None,
        bind_chat_history: bool = False,
        skip_review: bool = False,
        ppt_theme_id: str | None = None,
        save_to_chat_history: bool = True,
        *,
        ensure_chat_group_id: EnsureChatGroup,
        run_task: RunGenerationTask,
    ) -> dict:
        """Create a generation task with a short duplicate-submit Redis lock."""
        topic_value = topic or ""

        if topic_value and user_id:
            try:
                lock_seed = f"{topic_value.strip().lower()}::{normalize_ppt_theme_id(ppt_theme_id)}"
                lock_key = f"lock:task:{user_id}:{hashlib.md5(lock_seed.encode()).hexdigest()}"
                redis = await get_redis()
                locked = await redis.setnx(lock_key, "1")
                if not locked:
                    existing = await GenerationTask.filter(
                        user_id=user_id,
                        topic=topic_value.strip(),
                        status__in=["pending", "running"],
                    ).order_by("-created_at").first()
                    if existing:
                        return {
                            "task_id": existing.task_id,
                            "status": existing.status,
                            "chat_group_id": existing.chat_group_id,
                            "duplicated": True,
                        }
                else:
                    await redis.expire(lock_key, 30)
            except Exception:
                logger.debug("Redis task lock unavailable; creating task without duplicate guard")

        chat_group_id = await ensure_chat_group_id(user_id, chat_group_id, bind_chat_history)
        task_id = uuid.uuid4().hex
        task = await GenerationTask.create(
            task_id=task_id,
            user_id=user_id,
            topic=topic_value,
            resource_types=json.dumps(resource_types, ensure_ascii=False),
            chat_group_id=chat_group_id,
            status="pending",
        )
        asyncio.ensure_future(
            run_task(
                task.id,
                task_id,
                answers,
                skip_review=skip_review,
                ppt_theme_id=ppt_theme_id,
                save_to_chat_history=save_to_chat_history,
            )
        )
        return {"task_id": task_id, "status": "pending", "chat_group_id": chat_group_id}

    @staticmethod
    async def get_task(task_id: str, user_id: int) -> dict | None:
        cached_state = await read_cached_task_state(task_id, user_id)
        if cached_state:
            return cached_state

        task = await GenerationTask.filter(task_id=task_id, user_id=user_id).first()
        if not task:
            return None

        state = _task_to_state(task, user_id)
        asyncio.ensure_future(cache_task_state(task_id, state))
        return state

    @staticmethod
    async def list_tasks(user_id: int) -> list[dict]:
        tasks = await GenerationTask.filter(user_id=user_id).order_by("-created_at").limit(20).all()
        states = []
        for task in tasks:
            state = _task_to_state(task, user_id)
            state.pop("result", None)
            state.pop("updated_at", None)
            state.pop("user_id", None)
            states.append(state)
        return states

    @staticmethod
    async def init_tasks():
        abandoned = await GenerationTask.filter(status__in=["pending", "running"]).all()
        for task in abandoned:
            task.status = "failed"
            task.error = "服务重启，任务已中止"
            await task.save()

"""LLM 配置 + 优先级限流 — 前台请求优先于后台预生成，每用户每池独立并发"""
import asyncio
import threading
from pathlib import Path
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")

api_key = os.getenv("api_key")

_raw_llm = ChatOpenAI(
    model=os.getenv("AI_MODEL", "deepseek-chat"),
    api_key=api_key,
    base_url=os.getenv("AI_BASE_URL", "https://api.deepseek.com"),
    temperature=0.3,
    streaming=True,
    model_kwargs={"tool_choice": "auto"},
)

# 每用户每池并发上限
_PER_USER = {
    "ppt": 10,
    "document": 10,
    "path": 4,
    "leader": 2,
    "reviewer": 2,
    "thread": 3,
}
_DEFAULT_PER_USER = 3

_LLM_LOW_PRI_LIMIT = 2        # 有前台请求时，低优先级最多占 2 路

# 每用户每池并发池（异步）
_user_pool_async: dict[tuple[int, str], asyncio.Semaphore] = {}
_user_pool_async_lock = asyncio.Lock()

# 每用户每池并发池（同步 / 线程）
_user_pool_sync: dict[tuple[int, str], threading.BoundedSemaphore] = {}
_user_pool_sync_lock = threading.Lock()

# 优先级限流（全局）：有前台请求时，低优先级全局限流
_async_low = asyncio.Semaphore(_LLM_LOW_PRI_LIMIT)
_async_high_active = 0
_async_high_lock = asyncio.Lock()

_sync_low = threading.BoundedSemaphore(_LLM_LOW_PRI_LIMIT)
_sync_high_active = 0
_sync_high_lock = threading.Lock()


def _get_user_sync_sem(user_id: int, pool: str = "default") -> threading.BoundedSemaphore | None:
    if not user_id:
        return None
    key = (user_id, pool)
    if key in _user_pool_sync:
        return _user_pool_sync[key]
    with _user_pool_sync_lock:
        if key not in _user_pool_sync:
            limit = _PER_USER.get(pool, _DEFAULT_PER_USER)
            _user_pool_sync[key] = threading.BoundedSemaphore(limit)
        return _user_pool_sync[key]


class _PriorityLLM:
    """LLM 代理：每用户每池独立并发 + 全局优先级限流。"""

    def __getattr__(self, name):
        return getattr(_raw_llm, name)

    async def ainvoke(self, prompt, priority: str = "high", user_id: int = 0, pool: str = "default"):
        user_sem = None
        if user_id:
            key = (user_id, pool)
            if key not in _user_pool_async:
                async with _user_pool_async_lock:
                    if key not in _user_pool_async:
                        limit = _PER_USER.get(pool, _DEFAULT_PER_USER)
                        _user_pool_async[key] = asyncio.Semaphore(limit)
            user_sem = _user_pool_async[key]

        async def _call():
            if user_sem:
                async with user_sem:
                    return await _raw_llm.ainvoke(prompt)
            else:
                return await _raw_llm.ainvoke(prompt)

        global _async_high_active
        if priority == "high":
            async with _async_high_lock:
                _async_high_active += 1
            try:
                return await _call()
            finally:
                async with _async_high_lock:
                    _async_high_active -= 1
        else:
            async with _async_high_lock:
                throttled = _async_high_active > 0
            if throttled:
                async with _async_low:
                    return await _call()
            else:
                return await _call()

    def invoke(self, prompt, priority: str = "high", user_id: int = 0, pool: str = "default"):
        user_sem = _get_user_sync_sem(user_id, pool)

        def _call():
            if user_sem:
                with user_sem:
                    return _raw_llm.invoke(prompt)
            else:
                return _raw_llm.invoke(prompt)

        global _sync_high_active
        if priority == "high":
            with _sync_high_lock:
                _sync_high_active += 1
            try:
                return _call()
            finally:
                with _sync_high_lock:
                    _sync_high_active -= 1
        else:
            with _sync_high_lock:
                throttled = _sync_high_active > 0
            if throttled:
                with _sync_low:
                    return _call()
            else:
                return _call()


llm = _PriorityLLM()

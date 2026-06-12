"""LLM 配置 + 优先级限流 — 前台请求优先于后台预生成，每用户每池独立并发"""
import asyncio
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

_user_pool: dict[tuple[int, str], asyncio.Semaphore] = {}
_user_pool_lock = asyncio.Lock()

_low_pri_sem = asyncio.Semaphore(_LLM_LOW_PRI_LIMIT)
_high_active = 0
_high_lock = asyncio.Lock()


class _PriorityLLM:
    """LLM 代理：每用户每池独立并发 + 全局优先级限流。"""

    def __getattr__(self, name):
        return getattr(_raw_llm, name)

    async def ainvoke(self, prompt, priority: str = "high", user_id: int = 0, pool: str = "default"):
        user_sem = None
        if user_id:
            key = (user_id, pool)
            if key not in _user_pool:
                async with _user_pool_lock:
                    if key not in _user_pool:
                        limit = _PER_USER.get(pool, _DEFAULT_PER_USER)
                        _user_pool[key] = asyncio.Semaphore(limit)
            user_sem = _user_pool[key]

        async def _call():
            if user_sem:
                async with user_sem:
                    return await _raw_llm.ainvoke(prompt)
            else:
                return await _raw_llm.ainvoke(prompt)

        global _high_active
        if priority == "high":
            async with _high_lock:
                _high_active += 1
            try:
                return await _call()
            finally:
                async with _high_lock:
                    _high_active -= 1
        else:
            async with _high_lock:
                throttled = _high_active > 0
            if throttled:
                async with _low_pri_sem:
                    return await _call()
            else:
                return await _call()


llm = _PriorityLLM()

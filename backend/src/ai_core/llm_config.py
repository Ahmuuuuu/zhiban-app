"""LLM 配置 + 优先级限流 — 前台请求优先于后台预生成"""
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

_LLM_MAX_CONCURRENT = 5       # DeepSeek API 总并发上限
_LLM_LOW_PRI_LIMIT = 2        # 有前台请求时，低优先级最多占 2 路

_async_total = asyncio.Semaphore(_LLM_MAX_CONCURRENT)
_async_low = asyncio.Semaphore(_LLM_LOW_PRI_LIMIT)
_async_high_active = 0
_async_high_lock = asyncio.Lock()

_sync_total = threading.BoundedSemaphore(_LLM_MAX_CONCURRENT)
_sync_low = threading.BoundedSemaphore(_LLM_LOW_PRI_LIMIT)
_sync_high_active = 0
_sync_high_lock = threading.Lock()


class _PriorityLLM:
    """LLM 代理：按优先级限流。无前台请求时全速，有前台请求时限流后台。"""

    def __getattr__(self, name):
        return getattr(_raw_llm, name)

    async def ainvoke(self, prompt, priority: str = "high"):
        global _async_high_active
        if priority == "high":
            async with _async_high_lock:
                _async_high_active += 1
            try:
                async with _async_total:
                    return await _raw_llm.ainvoke(prompt)
            finally:
                async with _async_high_lock:
                    _async_high_active -= 1
        else:
            async with _async_high_lock:
                throttled = _async_high_active > 0
            if throttled:
                async with _async_low:
                    async with _async_total:
                        return await _raw_llm.ainvoke(prompt)
            else:
                async with _async_total:
                    return await _raw_llm.ainvoke(prompt)

    def invoke(self, prompt, priority: str = "high"):
        global _sync_high_active
        if priority == "high":
            with _sync_high_lock:
                _sync_high_active += 1
            try:
                with _sync_total:
                    return _raw_llm.invoke(prompt)
            finally:
                with _sync_high_lock:
                    _sync_high_active -= 1
        else:
            with _sync_high_lock:
                throttled = _sync_high_active > 0
            if throttled:
                with _sync_low:
                    with _sync_total:
                        return _raw_llm.invoke(prompt)
            else:
                with _sync_total:
                    return _raw_llm.invoke(prompt)


llm = _PriorityLLM()

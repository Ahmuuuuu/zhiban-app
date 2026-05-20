"""网页搜索工具 (DuckDuckGo)"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool


@tool
async def web_search(query: str):
    """搜索网页获取最新信息。在创建动作 skill 之前，必须先用此工具搜索真实的 API 接口和文档。
    也用于查找其他需要实时信息的内容。参数：query搜索关键词，建议包含 API、免费 等字眼"""
    import asyncio
    from ddgs import DDGS

    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_file)
    proxy = os.getenv("HTTP_PROXY", None)

    try:
        ddgs_kwargs = {}
        if proxy:
            ddgs_kwargs["proxy"] = proxy
        results = await asyncio.to_thread(
            lambda: list(DDGS(**ddgs_kwargs).text(query, max_results=5))
        )
        if not results:
            return f"未找到与「{query}」相关的结果"
        lines = [f"搜索「{query}」结果："]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', '')}\n   {r.get('body', '')}\n   {r.get('href', '')}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"搜索异常: {e}"

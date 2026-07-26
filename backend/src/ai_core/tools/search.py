import os
import re

import httpx
from langchain_core.tools import tool


def _normalize_searxng_url(value: str | None) -> str:
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        raw = "http://127.0.0.1:8080"
    if raw.endswith("/search"):
        return raw
    return f"{raw}/search"


def _format_results(query: str, results: list[dict]) -> str:
    if not results:
        return f"【WEB_SEARCH_NO_RESULTS】未找到与「{query}」相关的结果"

    lines = [f"搜索「{query}」结果："]
    for i, r in enumerate(results, 1):
        title = str(r.get("title") or "").strip()
        body = str(r.get("content") or r.get("body") or "").strip()
        url = str(r.get("url") or r.get("href") or "").strip()
        engine = str(r.get("engine") or "").strip()

        lines.append(f"{i}. {title}" if title else f"{i}.")
        if body:
            lines.append(f"   {body}")
        if url:
            lines.append(f"   {url}")
        if engine:
            lines.append(f"   来源：{engine}")

    return "\n".join(lines)


def _clean_query(query: str) -> str:
    text = str(query or "").strip()
    if not text:
        return ""

    parts = [part for part in text.split() if not re.fullmatch(r"!\S*", part)]
    return " ".join(parts).strip()


def _split_engines(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _query_variants(query: str) -> list[str]:
    variants = [query]
    if re.search(r"[\u4e00-\u9fff]", query) and len(query) <= 12:
        variants.extend([f"{query} 简介", f"{query} 百度百科"])
    return list(dict.fromkeys(v for v in variants if v))


def _format_unresponsive_engines(unresponsive: list) -> str:
    names: list[str] = []
    for item in unresponsive or []:
        if isinstance(item, (list, tuple)) and item:
            name = str(item[0]).strip()
            reason = str(item[1]).strip() if len(item) > 1 else ""
            if not name:
                continue
            names.append(f"{name}({reason})" if reason else name)
    return "、".join(dict.fromkeys(names))


async def _search_once(
    client: httpx.AsyncClient,
    searxng_url: str,
    query: str,
    engines: str | None,
) -> tuple[list[dict], list]:
    params = {"q": query, "format": "json", "categories": "general"}
    if engines:
        params["engines"] = engines
    resp = await client.get(searxng_url, params=params)
    if resp.status_code >= 400:
        body = resp.text[:300].replace("\n", " ").replace("\r", " ").strip()
        raise RuntimeError(f"SearXNG HTTP {resp.status_code}: {body}")
    payload = resp.json()
    results = payload.get("results", [])
    unresponsive = payload.get("unresponsive_engines", [])
    if not isinstance(results, list):
        results = []
    if not isinstance(unresponsive, list):
        unresponsive = []
    return results, unresponsive


async def _search_searxng(query: str) -> tuple[list[dict], str]:
    searxng_url = _normalize_searxng_url(os.getenv("SEARXNG_URL", "http://127.0.0.1:8080"))
    engines = os.getenv("SEARXNG_ENGINES", "360search,baidu,sogou,quark,chinaso").strip()
    query = _clean_query(query)
    if not query:
        return [], ""

    total_timeout = float(os.getenv("SEARXNG_TIMEOUT", "25"))
    connect_timeout = float(os.getenv("SEARXNG_CONNECT_TIMEOUT", "5"))
    timeout = httpx.Timeout(total_timeout, connect=connect_timeout)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        last_unresponsive: list = []
        for candidate in _query_variants(query):
            results, unresponsive = await _search_once(client, searxng_url, candidate, engines)
            if unresponsive:
                last_unresponsive = unresponsive
            if results:
                return results, ""

            results, unresponsive = await _search_once(client, searxng_url, candidate, None)
            if unresponsive:
                last_unresponsive = unresponsive
            if results:
                return results, ""

            for engine in _split_engines(engines):
                try:
                    results, unresponsive = await _search_once(client, searxng_url, candidate, engine)
                except httpx.RequestError:
                    continue
                if unresponsive:
                    last_unresponsive = unresponsive
                if results:
                    return results, ""

        return [], _format_unresponsive_engines(last_unresponsive)


@tool
async def web_search(query: str):
    """搜索网页获取最新信息。仅请求本地 SearXNG（默认 http://127.0.0.1:8080/search）。"""
    try:
        cleaned_query = _clean_query(query)
        results, suspended_note = await _search_searxng(cleaned_query)
        if suspended_note and not results:
            q = cleaned_query or str(query or "").strip()
            return f"【WEB_SEARCH_ENGINE_SUSPENDED】未找到与「{q}」相关的结果；当前受限引擎：{suspended_note}"
        return _format_results(cleaned_query or str(query or "").strip(), results)
    except httpx.RequestError as e:
        return f"搜索异常: {type(e).__name__}: {e!r}"
    except RuntimeError as e:
        return f"搜索异常: {e}"
    except Exception as e:
        return f"搜索异常: {type(e).__name__}: {e!r}"

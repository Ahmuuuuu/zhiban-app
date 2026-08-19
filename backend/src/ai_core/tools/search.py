import os
import re

import httpx
from langchain_core.tools import tool


def _normalize_searxng_url(value: str | None) -> str:
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        raw = "http://127.0.0.1:8888"
    if raw.endswith("/search"):
        return raw
    return f"{raw}/search"


def _zh(text: str) -> str:
    return text.encode("ascii").decode("unicode_escape")


def _format_results(query: str, results: list[dict]) -> str:
    if not results:
        return _zh(r"\u3010WEB_SEARCH_NO_RESULTS\u3011\u672a\u627e\u5230\u4e0e\u300c") + query + _zh(
            r"\u300d\u76f8\u5173\u7684\u7ed3\u679c"
        )

    lines = [_zh(r"\u641c\u7d22\u300c") + query + _zh(r"\u300d\u7ed3\u679c\uff1a")]
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
            lines.append(f"   {_zh(r'\u6765\u6e90\uff1a')}{engine}")

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
        variants.extend(
            [
                f"{query} {_zh(r'\u7b80\u4ecb')}",
                f"{query} {_zh(r'\u767e\u79d1')}",
            ]
        )
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
    return "\u3001".join(dict.fromkeys(names))


async def _search_once(
    client: httpx.AsyncClient,
    searxng_url: str,
    query: str,
    engines: str | None,
    extra_params: dict[str, str] | None = None,
) -> tuple[list[dict], list]:
    params = {"q": query, "format": "json", "categories": "general"}
    if engines:
        params["engines"] = engines
    if extra_params:
        params.update(extra_params)
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
    searxng_url = _normalize_searxng_url(os.getenv("SEARXNG_URL", "http://127.0.0.1:8888"))
    engines = os.getenv("SEARXNG_ENGINES", "360search,bing,baidu,sogou").strip()
    query = _clean_query(query)
    if not query:
        return [], ""

    total_timeout = float(os.getenv("SEARXNG_TIMEOUT", "12"))
    connect_timeout = float(os.getenv("SEARXNG_CONNECT_TIMEOUT", "3"))
    timeout = httpx.Timeout(total_timeout, connect=connect_timeout)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    engine_list = _split_engines(engines)
    attempts: list[str | None] = []
    attempts.extend(engine_list)
    if len(engine_list) > 1:
        attempts.append(engines)
    attempts.append(None)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        last_unresponsive: list = []
        last_error = ""
        for candidate in _query_variants(query):
            for engine_choice in attempts:
                try:
                    results, unresponsive = await _search_once(client, searxng_url, candidate, engine_choice)
                except (httpx.RequestError, RuntimeError) as e:
                    last_error = f"{type(e).__name__}: {e}"
                    continue
                if unresponsive:
                    last_unresponsive = unresponsive
                if results:
                    return results, ""

        note = _format_unresponsive_engines(last_unresponsive)
        if note:
            return [], note
        return [], last_error


async def _search_searxng_collect(query: str, max_results: int = 12) -> tuple[list[dict], str]:
    searxng_url = _normalize_searxng_url(os.getenv("SEARXNG_URL", "http://127.0.0.1:8888"))
    engines = os.getenv("SEARXNG_ENGINES", "360search,bing,baidu,sogou").strip()
    query = _clean_query(query)
    if not query:
        return [], ""

    try:
        limit = max(1, min(int(max_results or 12), 30))
    except (TypeError, ValueError):
        limit = 12

    total_timeout = float(os.getenv("SEARXNG_TIMEOUT", "12"))
    connect_timeout = float(os.getenv("SEARXNG_CONNECT_TIMEOUT", "3"))
    timeout = httpx.Timeout(total_timeout, connect=connect_timeout)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }

    collected: list[dict] = []
    seen_urls: set[str] = set()
    last_unresponsive: list = []
    last_error = ""

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        for candidate in _query_variants(query):
            for engine in _split_engines(engines):
                try:
                    results, unresponsive = await _search_once(client, searxng_url, candidate, engine)
                except (httpx.RequestError, RuntimeError) as e:
                    last_error = f"{type(e).__name__}: {e}"
                    continue
                if unresponsive:
                    last_unresponsive = unresponsive
                for item in results:
                    url = str(item.get("url") or item.get("href") or "").strip()
                    key = url or f"{item.get('engine', '')}:{item.get('title', '')}"
                    if not key or key in seen_urls:
                        continue
                    seen_urls.add(key)
                    collected.append(item)
                    if len(collected) >= limit:
                        return collected, ""

    if collected:
        return collected, ""
    note = _format_unresponsive_engines(last_unresponsive)
    if note:
        return [], note
    return [], last_error


async def search_recent_web_brief(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """快速获取近期公开资讯，供非阻塞的课堂等待页使用。

    只进行一次本地 SearXNG 请求，并使用独立短超时，避免等待页的资讯查询
    挤占课堂生成或被多个搜索引擎的重试链路拖慢。
    """
    cleaned_query = _clean_query(query)
    if not cleaned_query:
        return []
    try:
        limit = max(1, min(int(max_results), 4))
    except (TypeError, ValueError):
        limit = 3
    try:
        timeout_seconds = max(1.0, min(float(os.getenv("CLASSROOM_BRIEF_SEARCH_TIMEOUT", "4")), 8.0))
    except (TypeError, ValueError):
        timeout_seconds = 4.0

    timeout = httpx.Timeout(timeout_seconds, connect=min(2.0, timeout_seconds))
    headers = {
        "User-Agent": "ZhibanClassroom/1.0",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    searxng_url = _normalize_searxng_url(os.getenv("SEARXNG_URL", "http://127.0.0.1:8888"))
    engines = os.getenv("SEARXNG_ENGINES", "").strip() or None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            results, _ = await _search_once(
                client,
                searxng_url,
                cleaned_query,
                engines,
                extra_params={"time_range": "month"},
            )
    except (httpx.RequestError, RuntimeError, ValueError):
        return []

    briefs: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("href") or "").strip()
        title = " ".join(str(item.get("title") or "").split())
        if not title or not url or not re.match(r"^https?://", url, re.I) or url in seen_urls:
            continue
        seen_urls.add(url)
        briefs.append(
            {
                "title": title[:100],
                "summary": " ".join(str(item.get("content") or item.get("body") or "").split())[:180],
                "url": url,
                "source": str(item.get("engine") or item.get("source") or "公开来源").strip()[:32],
                "published_at": str(item.get("publishedDate") or item.get("published_at") or "").strip()[:32],
            }
        )
        if len(briefs) >= limit:
            break
    return briefs


@tool
async def web_search(query: str):
    """Search web pages through local SearXNG and return compact results."""
    try:
        cleaned_query = _clean_query(query)
        results, suspended_note = await _search_searxng(cleaned_query)
        q = cleaned_query or str(query or "").strip()
        if suspended_note and not results:
            return (
                _zh(r"\u3010WEB_SEARCH_ENGINE_SUSPENDED\u3011\u672a\u627e\u5230\u4e0e\u300c")
                + q
                + _zh(r"\u300d\u76f8\u5173\u7684\u7ed3\u679c\uff1b\u5f53\u524d\u53d7\u9650\u5f15\u64ce\uff1a")
                + suspended_note
            )
        return _format_results(q, results)
    except httpx.RequestError as e:
        return _zh(r"\u641c\u7d22\u5f02\u5e38: ") + f"{type(e).__name__}: {e!r}"
    except RuntimeError as e:
        return _zh(r"\u641c\u7d22\u5f02\u5e38: ") + str(e)
    except Exception as e:
        return _zh(r"\u641c\u7d22\u5f02\u5e38: ") + f"{type(e).__name__}: {e!r}"

"""Knowledge-base tools for the chat agent."""

import asyncio
import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool

from backend.src.ai_core.tools.search import _search_searxng_collect
from backend.src.utils.knowledge_base import (
    delete as kb_delete,
    ingest as kb_ingest,
    list_all as kb_list,
    search as kb_search,
    update as kb_update,
)


_SOURCE_FETCH_TIMEOUT = 8.0
_SOURCE_FETCH_MAX_BYTES = 8 * 1024 * 1024
_SOURCE_TEXT_MAX_CHARS = 120000
_SOURCE_TEXT_MIN_CHARS = 220

_ARTICLE_START_MARKERS = (
    'id="cnblogs_post_body"',
    "id='cnblogs_post_body'",
    'class="postBody"',
    "class='postBody'",
    'class="article-content"',
    "class='article-content'",
    'class="article_content"',
    "class='article_content'",
    'class="post-content"',
    "class='post-content'",
    'class="entry-content"',
    "class='entry-content'",
    "<article",
)

_ARTICLE_END_MARKERS = (
    'id="MySignature"',
    "id='MySignature'",
    'id="blog_post_info_block"',
    "id='blog_post_info_block'",
    'class="postDesc"',
    "class='postDesc'",
    'class="post-footer"',
    "class='post-footer'",
    "posted @",
    "上一篇：",
    "下一篇：",
)


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_depth += 1
        if tag.lower() in {"p", "br", "div", "section", "article", "li", "tr", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str):
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas"} and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "li", "tr", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        text = str(data or "").strip()
        if text:
            self._parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def _compact_text(value: str, max_chars: int = 1200) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_chars].rstrip()


def _normalize_source_url(value: str) -> str:
    return str(value or "").strip()


def _is_fetchable_source_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    lower_path = parsed.path.lower()
    return not lower_path.endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".zip", ".rar"))


def _extract_visible_text(markup: str) -> str:
    parser = _VisibleTextParser()
    try:
        parser.feed(markup)
    except Exception:
        return ""
    text = html.unescape(parser.get_text())
    lines = []
    seen = set()
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if len(line) < 2:
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines).strip()


def _slice_article_markup(markup: str) -> str:
    lower = markup.lower()
    start = -1
    for marker in _ARTICLE_START_MARKERS:
        idx = lower.find(marker.lower())
        if idx < 0:
            continue
        tag_start = lower.rfind("<", 0, idx)
        start = tag_start if tag_start >= 0 else idx
        break

    if start < 0:
        return markup

    end_candidates = []
    for marker in _ARTICLE_END_MARKERS:
        idx = lower.find(marker.lower(), start + 1)
        if idx > start:
            tag_start = lower.rfind("<", 0, idx)
            end_candidates.append(tag_start if tag_start > start else idx)
    end = min(end_candidates) if end_candidates else len(markup)
    return markup[start:end]


def _clean_source_text(text: str) -> str:
    lines: list[str] = []
    seen = set()
    noise = {
        "会员",
        "周边",
        "新闻",
        "博问",
        "闪存",
        "赞助商",
        "所有博客",
        "当前博客",
        "我的博客",
        "我的园子",
        "账号设置",
        "会员中心",
        "简洁模式",
        "退出登录",
        "注册",
        "登录",
        "刷新页面",
        "返回顶部",
        "公告",
    }
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or line in noise:
            continue
        if len(line) <= 2 and re.fullmatch(r"[\W_]+", line):
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines).strip()


def _clip_source_text(text: str, max_chars: int) -> tuple[str, bool]:
    text = str(text or "").strip()
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip(), True


async def _fetch_source_text(url: str) -> tuple[str, str]:
    url = _normalize_source_url(url)
    if not _is_fetchable_source_url(url):
        return "", "来源不是可直接抓取的网页"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.6",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    try:
        async with httpx.AsyncClient(
            timeout=_SOURCE_FETCH_TIMEOUT,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return "", f"来源网页返回 HTTP {resp.status_code}"
            content_type = resp.headers.get("content-type", "").lower()
            raw = resp.content[:_SOURCE_FETCH_MAX_BYTES]
            if "text/plain" in content_type:
                text = raw.decode(resp.encoding or "utf-8", errors="ignore")
            else:
                markup = raw.decode(resp.encoding or "utf-8", errors="ignore")
                text = _extract_visible_text(_slice_article_markup(markup))
    except Exception as exc:
        return "", f"来源网页抓取失败：{type(exc).__name__}"

    text = _clean_source_text(text)
    if len(text) < _SOURCE_TEXT_MIN_CHARS:
        return "", "来源网页正文过短或需要动态渲染"
    text, clipped = _clip_source_text(text, _SOURCE_TEXT_MAX_CHARS)
    if clipped:
        text = f"{text}\n\n[正文过长，已截取前 {_SOURCE_TEXT_MAX_CHARS} 字用于审核和入库]"
    return text, ""


_AUTO_STAGE_TRIGGERS = (
    "补库",
    "入库",
    "加入知识库",
    "添加到知识库",
    "放进知识库",
    "存到知识库",
    "提交审核",
    "待审核",
    "自动搜索资料",
    "自动搜资料",
    "联网补充",
    "补充知识库",
)


def _is_explicit_stage_request(user_request: str, topic: str) -> bool:
    text = f"{user_request or ''} {topic or ''}"
    return any(trigger in text for trigger in _AUTO_STAGE_TRIGGERS)


@tool
async def search_knowledge_base(query: str, user_id: str, top_k: int = 5):
    """从知识库检索资料。参数：query 用户问题或关键词，user_id 用户数字 ID，top_k 返回条数。"""
    return await kb_search(query, top_k, user_id=int(user_id))


@tool
async def ingest_document(title: str, content: str, user_id: str):
    """保存用户主动提供的学习资料到个人知识库。参数：title 标题，content 正文，user_id 用户数字 ID。"""
    return await kb_ingest(title, content, user_id=int(user_id))


def _format_web_reference(topic: str, result: dict, source_text: str = "", fetch_note: str = "") -> tuple[str, str]:
    title = _compact_text(result.get("title") or "联网资料", 120)
    body = _compact_text(result.get("content") or result.get("body") or "", 1200)
    url = _normalize_source_url(result.get("url") or result.get("href") or "")
    engine = _compact_text(result.get("engine") or "", 60)

    kb_title = f"[WEB待审核] {topic} - {title}"
    content_parts = [
        f"主题：{topic}",
        f"来源标题：{title}",
    ]
    if url:
        content_parts.append(f"来源链接：{url}")
    if engine:
        content_parts.append(f"搜索引擎：{engine}")
    content_parts.extend(
        [
            "状态说明：该资料由智能体联网检索自动暂存，需管理员审核后才能进入公共知识库。",
            "",
        ]
    )
    if source_text:
        content_parts.extend(["正文提取：", source_text])
    else:
        if fetch_note:
            content_parts.append(f"正文抓取说明：{fetch_note}")
        content_parts.extend(["搜索摘要：", body or title])
    return kb_title, "\n".join(content_parts)


@tool
async def search_web_and_stage_knowledge(topic: str, user_request: str, user_id: str, max_results: int = 5):
    """
    联网搜索资料并暂存到知识库待审核区。
    仅在用户明确要求“联网补充知识库、自动搜索资料入库、为课程补库”时使用。
    user_request 必须传入用户原话，用于防止普通搜索误入库。
    入库 visibility 固定为 pending，管理员审核通过后才会成为公共资料。
    """
    topic = _compact_text(topic, 80)
    if not topic:
        return "请先说明要补充到知识库的主题。"
    if not _is_explicit_stage_request(user_request, topic):
        return (
            "我可以联网搜索资料并提交到知识库待审核区，但这需要用户明确确认。"
            "请让用户回复类似“帮我为微机原理补库”或“把这些资料提交知识库审核”。"
        )

    try:
        limit = max(1, min(int(max_results or 5), 8))
    except Exception:
        limit = 5

    results, suspended_note = await _search_searxng_collect(topic, max_results=max(limit * 3, 12))
    if not results:
        extra = f"；当前受限引擎：{suspended_note}" if suspended_note else ""
        return f"未搜索到可暂存的资料：{topic}{extra}"

    candidates = []
    seen_urls = set()
    for result in results:
        url = _normalize_source_url(result.get("url") or result.get("href") or "")
        title = _compact_text(result.get("title") or "", 120)
        body = _compact_text(result.get("content") or result.get("body") or "", 1200)
        if not title and not body:
            continue
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        candidates.append(result)
        if len(candidates) >= limit:
            break

    fetch_tasks = [
        _fetch_source_text(_normalize_source_url(result.get("url") or result.get("href") or ""))
        for result in candidates
    ]
    fetched_sources = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    staged = []
    for result, fetched in zip(candidates, fetched_sources):
        url = _normalize_source_url(result.get("url") or result.get("href") or "")
        source_text = ""
        fetch_note = ""
        if isinstance(fetched, Exception):
            fetch_note = f"来源网页抓取失败：{type(fetched).__name__}"
        else:
            source_text, fetch_note = fetched

        kb_title, content = _format_web_reference(topic, result, source_text, fetch_note)
        msg = await kb_ingest(
            title=kb_title,
            content=content,
            user_id=int(user_id),
            visibility="pending",
            category="reference",
        )
        staged.append((kb_title, url, msg))

    if not staged:
        return f"搜索到了结果，但没有可暂存的有效摘要：{topic}"

    lines = [
        f"已为《{topic}》联网暂存 {len(staged)} 条参考资料，状态为待审核。",
        "管理员审核通过后，这些资料才会进入公共知识库。",
    ]
    for idx, (title, url, msg) in enumerate(staged, 1):
        lines.append(f"{idx}. {title}")
        if url:
            lines.append(f"   {url}")
        lines.append(f"   {msg}")
    return "\n".join(lines)


@tool
async def list_knowledge(user_id: str):
    """列出当前用户可见的知识库资料。参数：user_id 用户数字 ID。"""
    records = await kb_list(user_id=int(user_id))
    if not records:
        return "知识库中暂无资料"
    lines = ["知识库资料列表："]
    for i, r in enumerate(records, 1):
        label_map = {"public": "公开", "private": "私有", "pending": "待审核", "rejected": "已驳回"}
        label = label_map.get(r["visibility"], r["visibility"])
        lines.append(f"{i}. [{label}] {r['title']} (id: {r['doc_id']})")
        lines.append(f"   内容摘要：{r['content'][:120]}...")
    return "\n".join(lines)


@tool
async def update_knowledge(doc_id: str, user_id: str, title: str = None, content: str = None):
    """更新当前用户自己的知识库资料。参数：doc_id 资料 ID，title 新标题可选，content 新正文可选。"""
    return await kb_update(doc_id=doc_id, title=title, content=content, user_id=int(user_id), is_admin=False)


@tool
async def delete_knowledge(doc_id: str, user_id: str):
    """删除当前用户自己的私有知识库资料。参数：doc_id 资料 ID，user_id 用户数字 ID。"""
    return await kb_delete(doc_id=doc_id, user_id=int(user_id), is_admin=False)

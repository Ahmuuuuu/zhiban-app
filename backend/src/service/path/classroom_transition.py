"""Non-blocking transition content for the interactive classroom loading state."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from backend.src.ai_core.tools.search import search_recent_web_brief
from backend.src.models.path_model import LearningPath, PathNode
from backend.src.models.usermodel import User
from backend.src.service.portrait.service import parse_traits, trait_display

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 15 * 60
_transition_cache: dict[tuple[int, int], tuple[float, dict[str, Any]]] = {}
_transition_locks: dict[tuple[int, int], asyncio.Lock] = {}


def _clip(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _node_tags(raw: Any) -> list[str]:
    try:
        values = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        values = []
    if not isinstance(values, list):
        return []
    return [text for item in values if (text := _clip(item, 32))][:4]


def _learning_activities(topic: str, tags: list[str], cognition: str) -> list[dict[str, str]]:
    """不编造专业事实，只将节点自身的术语组织成可立即执行的预习动作。"""
    first = tags[0] if tags else topic
    second = tags[1] if len(tags) > 1 else topic
    activities = [
        {
            "title": f"给“{first}”下一句定义",
            "content": f"先不看资料，补全这句话：“{first} 是____，它用来____。”只写定义和用途，不举例。课堂生成后先对照核心概念修正。",
        },
        {
            "title": f"推断“{first}”与“{second}”的关系",
            "content": f"在纸上写“{first} → {second}”，并在箭头上填一个动词：决定、限制、转换或校验。先猜，再用课堂验证这条关系。",
        },
        {
            "title": "提前标出一个边界",
            "content": f"针对“{topic}”，写下一个你不敢完全确定的条件或步骤。课堂里的随堂练习会优先帮你核对这个疑点。",
        },
    ]
    if cognition == "visual":
        activities[1]["content"] = f"画两个方框：“{first}”和“{second}”，用一根箭头连起来，并在箭头上写“为什么会影响”。课堂会验证你的图。"
    elif cognition == "practical":
        activities[2]["content"] = f"为“{topic}”设一个最小输入，写出你预计的结果；不要追求算对，先让课堂帮你定位中间缺失的步骤。"
    elif cognition == "auditory":
        activities[0]["content"] = f"用自己的话读出这句：“{first} 是什么，它解决什么问题？”录不录音都可以，关键是发现自己在哪个词上停住。"
    return activities


async def _review_recent_news(
    topic: str,
    profile_focus: str,
    candidates: list[dict[str, str]],
    user_id: int,
) -> list[dict[str, str]]:
    """让低优先级 LLM 筛选搜索候选；失败时不把原始搜索结果直接展示给用户。"""
    if not candidates:
        return []

    try:
        from backend.src.ai_core.llm_config import llm
        from backend.src.utils.json_parser import parse_llm_json
        from backend.src.utils.prompt_loader import fill_prompt, load_prompt

        prompt = fill_prompt(
            load_prompt("classroom/transition_news"),
            topic=topic,
            profile_focus=profile_focus or "未提供，优先判断与当前知识点的直接关系",
            candidates_json=json.dumps(candidates, ensure_ascii=False),
        )
        started_at = time.perf_counter()
        response = await asyncio.wait_for(
            llm.ainvoke(prompt, priority="low", user_id=user_id, pool="transition"),
            timeout=18,
        )
        parsed = parse_llm_json(str(getattr(response, "content", "") or ""))
        items = parsed.get("items", []) if isinstance(parsed, dict) else []
        if not isinstance(items, list):
            return []

        candidate_by_url = {
            str(item.get("url") or "").strip(): item
            for item in candidates
            if str(item.get("url") or "").strip()
        }
        reviewed: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            source = candidate_by_url.get(url)
            if not source or url in seen_urls:
                continue
            title = _clip(source.get("title"), 100)
            summary = _clip(item.get("summary"), 180)
            if not title or not summary:
                continue
            seen_urls.add(url)
            reviewed.append(
                {
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "source": _clip(source.get("source") or "公开来源", 32),
                    "published_at": _clip(source.get("published_at"), 32),
                }
            )
            if len(reviewed) >= 3:
                break
        logger.info(
            "[ClassroomTransition] 近日资讯审核完成 user=%s candidates=%s results=%s elapsed=%.2fs",
            user_id,
            len(candidates),
            len(reviewed),
            time.perf_counter() - started_at,
        )
        return reviewed
    except Exception:
        logger.warning("[ClassroomTransition] 近日资讯审核失败 user=%s，丢弃原始候选", user_id, exc_info=True)
        return []


async def get_classroom_transition(path_id: int, node_id: int, user_id: int) -> dict[str, Any] | None:
    """Build waiting content: SearXNG candidates first, then low-priority LLM review."""
    node = await PathNode.filter(id=node_id, path_id=path_id).first()
    if not node:
        return None
    cache_key = (user_id, node_id)
    cached = _transition_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    lock = _transition_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        cached = _transition_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

        path, user = await asyncio.gather(
            LearningPath.filter(id=path_id).first(),
            User.filter(id=user_id).first(),
        )
        picture = await user.picture if user else None
        topic = _clip(node.topic, 80) or "当前知识点"
        tags = _node_tags(node.knowledge_tags)
        subject = _clip(getattr(path, "subject", ""), 48)
        major = _clip(getattr(user, "major", ""), 48)
        traits = parse_traits(getattr(picture, "traits", None)) if picture else {}
        interest = _clip(trait_display(traits, "interest"), 48)
        cognition = _clip(getattr(picture, "cognition", ""), 24) if picture else ""
        search_focus = interest or major or subject or topic
        query = f"{search_focus} 近期 动态" if search_focus else f"{topic} 近期 动态"
        search_started_at = time.perf_counter()
        candidates = await search_recent_web_brief(query, max_results=6)
        logger.info(
            "[ClassroomTransition] 近日资讯候选 path=%s node=%s user=%s query=%s candidates=%s elapsed=%.2fs",
            path_id,
            node_id,
            user_id,
            query,
            len(candidates),
            time.perf_counter() - search_started_at,
        )
        news = await _review_recent_news(topic, search_focus, candidates, user_id)
        payload = {
            "topic": topic,
            "news": news,
            "activities": _learning_activities(topic, tags, cognition),
            "profile_focus": search_focus,
        }
        _transition_cache[cache_key] = (time.monotonic(), payload)
        return payload

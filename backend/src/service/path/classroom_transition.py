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
_transition_tasks: dict[tuple[int, int], asyncio.Task[None]] = {}


def _clip(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _fallback_stories(
    topic: str,
    major: str,
    interest: str,
    learning_goal: str,
    cognition: str,
) -> list[dict[str, str]]:
    focus = interest or major or "你的专业方向"
    goal_text = learning_goal or "把知识真正用起来"
    stories = [
        {
            "title": "一个小问题的转弯",
            "content": f"你在做{focus}相关项目时，遇到一个看似简单却总出错的小问题。后来你没有继续堆代码，而是回到“{topic}”的定义，先把输入、规则和结果分开，问题很快露出了位置。",
        },
        {
            "title": "从会用到会解释",
            "content": f"为了{goal_text}，你把“{topic}”讲给一个完全不了解这门课的人听。讲到一半卡住的地方，往往正是你还没有真正理解的地方，这比背下结论更有价值。",
        },
        {
            "title": "换一种记忆入口",
            "content": f"今天学习“{topic}”时，你没有从长定义开始，而是先画出一条关系线，再用一句话解释它。{('这种先看结构再听解释的方式很适合你。' if cognition == 'visual' else '这种先动手验证再补概念的方式很适合你。' if cognition == 'practical' else '这种先读出来再整理概念的方式很适合你。' if cognition == 'auditory' else '把定义写下来再举例，会让它更牢固。')}",
        },
    ]
    return [{"title": _clip(item["title"], 40), "content": _clip(item["content"], 150)} for item in stories]


async def _review_transition_content(
    topic: str,
    profile_focus: str,
    candidates: list[dict[str, str]],
    user_id: int,
    major: str,
    grade: str,
    learning_goal: str,
    cognition: str,
    interest: str,
) -> dict[str, list[dict[str, str]]]:
    """一次低优先级调用同时整理新闻和画像故事；新闻失败时绝不直出原始候选。"""
    fallback = _fallback_stories(topic, major, interest, learning_goal, cognition)
    if not candidates:
        return {"news": [], "stories": fallback}

    try:
        from backend.src.ai_core.llm_config import llm
        from backend.src.utils.json_parser import parse_llm_json
        from backend.src.utils.prompt_loader import fill_prompt, load_prompt

        prompt = fill_prompt(
            load_prompt("classroom/transition_news"),
            topic=topic,
            profile_focus=profile_focus or "未提供，优先判断与当前知识点的直接关系",
            major=major or "未提供",
            grade=grade or "未提供",
            learning_goal=learning_goal or "未提供",
            cognition=cognition or "未提供",
            interest=interest or "未提供",
            candidates_json=json.dumps(candidates, ensure_ascii=False),
        )
        started_at = time.perf_counter()
        response = await asyncio.wait_for(
            llm.ainvoke(prompt, priority="low", user_id=user_id, pool="transition"),
            timeout=18,
        )
        parsed = parse_llm_json(str(getattr(response, "content", "") or ""))
        items = parsed.get("news", []) if isinstance(parsed, dict) else []
        if not isinstance(items, list):
            items = []

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
        stories_raw = parsed.get("stories", []) if isinstance(parsed, dict) else []
        stories: list[dict[str, str]] = []
        if isinstance(stories_raw, list):
            for item in stories_raw:
                if not isinstance(item, dict):
                    continue
                title = _clip(item.get("title"), 40)
                content = _clip(item.get("content"), 150)
                if title and content:
                    stories.append({"title": title, "content": content})
                if len(stories) >= 3:
                    break
        return {"news": reviewed, "stories": stories or fallback}
    except Exception:
        logger.warning("[ClassroomTransition] 过渡内容审核失败 user=%s，丢弃原始新闻并使用画像故事兜底", user_id, exc_info=True)
        return {"news": [], "stories": fallback}


async def _build_transition_context(path_id: int, node_id: int, user_id: int) -> dict[str, Any] | None:
    node = await PathNode.filter(id=node_id, path_id=path_id).first()
    if not node:
        return None
    path, user = await asyncio.gather(
        LearningPath.filter(id=path_id).first(),
        User.filter(id=user_id).first(),
    )
    picture = await user.picture if user else None
    topic = _clip(node.topic, 80) or "当前知识点"
    subject = _clip(getattr(path, "subject", ""), 48)
    major = _clip(getattr(user, "major", ""), 48)
    traits = parse_traits(getattr(picture, "traits", None)) if picture else {}
    interest = _clip(trait_display(traits, "interest"), 48)
    cognition = _clip(getattr(picture, "cognition", ""), 24) if picture else ""
    learning_goal = _clip(getattr(picture, "learning_goal", ""), 32) if picture else ""
    grade = _clip(getattr(user, "grade", ""), 24)
    search_focus = interest or major or subject or topic
    return {
        "path_id": path_id,
        "node_id": node_id,
        "user_id": user_id,
        "topic": topic,
        "major": major,
        "grade": grade,
        "interest": interest,
        "cognition": cognition,
        "learning_goal": learning_goal,
        "search_focus": search_focus,
    }


async def _refresh_transition_cache(cache_key: tuple[int, int], context: dict[str, Any]) -> None:
    """在后台补齐近日资讯，绝不阻塞课堂等待页的首屏。"""
    try:
        topic = context["topic"]
        search_focus = context["search_focus"]
        queries = list(dict.fromkeys(
            query
            for query in (
                f"{topic} 近期 最新进展",
                f"{search_focus} 近期 最新动态" if search_focus else "",
            )
            if query.strip()
        ))
        search_started_at = time.perf_counter()
        batches = await asyncio.gather(
            *(search_recent_web_brief(query, max_results=4) for query in queries),
            return_exceptions=True,
        )
        candidates: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            for item in batch:
                url = str(item.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(item)
                if len(candidates) >= 6:
                    break
            if len(candidates) >= 6:
                break
        logger.info(
            "[ClassroomTransition] 近日资讯候选 path=%s node=%s user=%s queries=%s candidates=%s elapsed=%.2fs",
            context["path_id"],
            context["node_id"],
            context["user_id"],
            " | ".join(queries),
            len(candidates),
            time.perf_counter() - search_started_at,
        )
        reviewed = await _review_transition_content(
            topic,
            search_focus,
            candidates,
            context["user_id"],
            context["major"],
            context["grade"],
            context["learning_goal"],
            context["cognition"],
            context["interest"],
        )
        _transition_cache[cache_key] = (time.monotonic(), {
            "topic": topic,
            "news": reviewed["news"],
            "stories": reviewed["stories"],
            "profile_focus": search_focus,
            "pending": False,
        })
    except Exception:
        logger.warning("[ClassroomTransition] 后台过渡内容生成失败 key=%s", cache_key, exc_info=True)
        fallback = _fallback_stories(
            context["topic"], context["major"], context["interest"], context["learning_goal"], context["cognition"]
        )
        _transition_cache[cache_key] = (time.monotonic(), {
            "topic": context["topic"],
            "news": [],
            "stories": fallback,
            "profile_focus": context["search_focus"],
            "pending": False,
        })


def _forget_transition_task(cache_key: tuple[int, int], task: asyncio.Task[None]) -> None:
    if _transition_tasks.get(cache_key) is task:
        _transition_tasks.pop(cache_key, None)


async def get_classroom_transition(path_id: int, node_id: int, user_id: int) -> dict[str, Any] | None:
    """Return profile stories immediately; asynchronously enrich with reviewed recent news."""
    cache_key = (user_id, node_id)
    cached = _transition_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    context = await _build_transition_context(path_id, node_id, user_id)
    if not context:
        return None

    fallback = _fallback_stories(
        context["topic"], context["major"], context["interest"], context["learning_goal"], context["cognition"]
    )
    payload = {
        "topic": context["topic"],
        "news": [],
        "stories": fallback,
        "profile_focus": context["search_focus"],
        "pending": True,
    }
    _transition_cache[cache_key] = (time.monotonic(), payload)
    task = asyncio.create_task(_refresh_transition_cache(cache_key, context), name=f"classroom-transition-{user_id}-{node_id}")
    _transition_tasks[cache_key] = task
    task.add_done_callback(lambda finished: _forget_transition_task(cache_key, finished))
    return payload

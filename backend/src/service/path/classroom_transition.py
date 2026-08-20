"""Non-blocking transition content for the interactive classroom loading state."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
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

_STORY_MODES = (
    "故障复现：从一个反常输出倒推最小触发条件。",
    "小实验：用电脑、纸笔或身边物品做一个可观察的微型验证。",
    "产品现场：把知识点放进用户真实操作流程，解决一个具体麻烦。",
    "代码评审：两种写法都能运行，但在边界条件下出现不同后果。",
    "资源受限：时间、内存、带宽或设备受限时，知识点改变了取舍。",
    "数据侦探：一条异常记录、一列数据或一个日志字段暴露了关键关系。",
    "接口误会：前后端或两个工具对同一个字段的理解不一致。",
    "反直觉预测：先猜结果，再通过一次运行或计算发现猜错在哪里。",
    "用户追问：用户只问了一句很短的话，却迫使你看清系统真正的规则。",
    "规模变化：样例很顺利，数据量或任务数量放大后出现新的问题。",
    "工具链插曲：编辑器、数据库、模型或脚本的一个小差异改变了结果。",
    "迁移场景：把当前知识点从课堂换到另一个专业或兴趣场景中验证。",
)


def _random_story_modes() -> str:
    selected = random.sample(_STORY_MODES, 3)
    return "\n".join(f"{index}. {mode}" for index, mode in enumerate(selected, 1))


def _candidate_news_fallback(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    """审核超时的最后兜底：只展示搜索结果原文中的事实，不补写新闻结论。"""
    fallback: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = _clip(item.get("title"), 100)
        if not url or not title or url in seen_urls:
            continue
        seen_urls.add(url)
        summary = _clip(item.get("summary") or item.get("content") or item.get("body"), 180)
        fallback.append({
            "title": title,
            "summary": summary or "搜索结果未提供摘要，请打开来源查看原文。",
            "url": url,
            "source": _clip(item.get("source") or item.get("engine") or "公开来源", 32),
            "published_at": _clip(item.get("published_at") or item.get("publishedDate"), 32),
        })
        if len(fallback) >= 3:
            break
    return fallback


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
    # 兜底内容也要有变化：按节点和画像稳定选择一组场景，避免每次都是同三句。
    seed = int(hashlib.sha1(f"{topic}|{focus}|{goal_text}".encode("utf-8")).hexdigest()[:8], 16)
    sets = [
        [
            ("凌晨的异常日志", f"你在做{focus}项目时，日志里只多出一个看似无关的“{topic}”值。把前后两次输入并排一放，真正的线索藏在那次变化里。你会先查哪一处？"),
            ("三分钟纸笔实验", f"拿纸写下“{topic}”里的三个关键量，再只改变其中一个。结果和直觉不一样的那一格，正好暴露了它们之间的关系。"),
            ("上线前的一个按钮", f"为了{goal_text}，你给{focus}工具加了一个小功能：它不只给结果，还显示“{topic}”参与了哪一步。用户第一次定位问题少绕了一圈。"),
        ],
        [
            ("那条不该出现的结果", f"测试{focus}应用时，只有一组输入触发了异常结果。你把它拆成几个更小的步骤，发现“{topic}”并不是答案，而是决定答案走哪条路的开关。"),
            ("把概念放进浏览器", f"打开一个空白页面，给“{topic}”只留一个输入和一个输出，再换两次输入观察变化。屏幕上的差异，比一段长解释更容易记住。"),
            ("同事只问了一句", f"你向同事演示{focus}项目时，对方问：“这里为什么要经过{topic}？”你删掉多余步骤后，流程反而更稳定了。"),
        ],
        [
            ("接口返回得太快", f"{focus}项目的接口突然返回成功，但页面内容是空的。沿着“{topic}”对应的数据流回看，原来完成和可用并不是同一件事。"),
            ("一张便签的预测", f"在便签上写下你认为“{topic}”下一步会发生什么，再实际运行一次。预测错的地方，可能比预测对的地方更值得保留。"),
            ("给流程加一道护栏", f"你想让{focus}工具更可靠，于是在{topic}最容易混淆的位置加了一条检查。它没有让代码变长多少，却让后面的排查有了落点。"),
        ],
    ]
    stories = sets[seed % len(sets)]
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
    story_modes: str,
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
            story_modes=story_modes,
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
    except Exception as exc:
        # 搜索候选已经过 SearXNG 的结构化过滤。LLM 审核超时不能把用户看到的资讯清空，
        # 降级时只保留候选原文的标题、摘要和链接，不生成任何额外事实。
        news = _candidate_news_fallback(candidates)
        logger.warning(
            "[ClassroomTransition] 过渡内容审核失败 user=%s error=%s fallback_news=%s",
            user_id,
            type(exc).__name__,
            len(news),
        )
        return {"news": news, "stories": fallback}


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
            _random_story_modes(),
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

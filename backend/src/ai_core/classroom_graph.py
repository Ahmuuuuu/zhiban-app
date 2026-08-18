"""
LangGraph 双智能体编排 — 互动课堂脚本生成
WriterAgent(导演规划 → 并行分幕) → ReviewerAgent(独立审核 → 带反馈重写)
"""
import asyncio
import json
import logging
import time
from typing import Any, TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.utils.json_parser import parse_llm_json
from backend.src.service.path.classroom import (
    _normalize_lesson,
    _GENERIC_CLASSROOM_PHRASES,
    _content_evidence_terms,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════
#  常量
# ═══════════════════════════════════════

# 固定四幕，顺序不可变（与 _fallback_lesson / 前端契约一致）
_SEGMENT_IDS = ("lead-in", "concept", "exercise", "feynman")

# 幕 id → segment.type（前端 isResourceScene/isQuizScene/isFeynmanScene 依赖）
_SEGMENT_TYPES = {
    "lead-in": "hook",
    "concept": "concept",
    "exercise": "exercise",
    "feynman": "feynman",
}

_MAX_REVIEW_RETRIES = 2        # Reviewer 未通过最多重写 2 次
_REVIEW_PASS_SCORE = 80        # 通过阈值：score >= 80 且结构契约通过
_MAX_SEGMENT_CONCURRENCY = 4   # 四幕并行生成
_REVIEW_FEEDBACK_MAX_LEN = 400 # 回灌给 writer 的总体意见截断，防止 prompt 膨胀

# 蓝图缺失时的幕默认 goal / focus（保证任何情况都产出"四幕齐全"蓝图）
_DEFAULT_GOALS = {
    "lead-in": "结合学生画像说明这个知识点与学生的关系",
    "concept": "讲清知识点的定义、结构、关系和使用边界",
    "exercise": "用一道真实练习检查概念、步骤或易错点",
    "feynman": "用自己的话反讲，并在右侧对话中补齐漏洞",
}
_DEFAULT_FOCUS = {
    "lead-in": "用户专业、年级、目标与该知识点的具体联系",
    "concept": "节点中的核心术语、公式、步骤、例子和易错点",
    "exercise": "节点测验中的题干、选项、答案和解析",
    "feynman": "三句话反讲任务、一个例子、一次右侧对话追问",
}


# ═══════════════════════════════════════
#  State
# ═══════════════════════════════════════

class ClassroomState(TypedDict):
    # ── 输入（generate_classroom_lesson 注入）──
    path_id: int
    node_id: int
    user_id: int
    subject: str
    topic: str
    summary: str
    knowledge_tags: list[str]
    quiz_config: dict[str, Any]
    quiz_snapshot: dict[str, Any]
    resources: list[dict[str, str]]
    portrait_context: str
    fallback_lesson: dict[str, Any]    # _fallback_lesson(...) 预计算结果，异常兜底用
    llm_priority: NotRequired[str]     # 默认 "high"
    max_retries: NotRequired[int]      # 默认 _MAX_REVIEW_RETRIES

    # ── Writer 输出 ──
    teaching_outline: NotRequired[dict[str, Any]]  # 导演产物；重写轮次复用，不重复规划
    raw_lesson: NotRequired[dict[str, Any]]        # 4 幕原始拼接（归一化前），Reviewer 审核对象
    lesson: NotRequired[dict[str, Any]]            # _normalize_lesson 归一化后的最终课堂

    # ── Reviewer 输出 ──
    review_passed: NotRequired[bool]
    review_score: NotRequired[float]
    review_feedback: NotRequired[str]              # 未通过时的总体意见
    review_issues: NotRequired[list[dict[str, Any]]]  # [{segment_id, category, message}]
    retry_count: NotRequired[int]


# ═══════════════════════════════════════
#  Writer — 导演规划 + 并行分幕
# ═══════════════════════════════════════

async def writer_node(state: ClassroomState) -> dict:
    """首次先规划教学主线，再并行生成四幕；重写轮次复用蓝图并带审核意见重写。"""
    started_at = time.perf_counter()
    path_id = state.get("path_id")
    node_id = state.get("node_id")
    retry_count = state.get("retry_count", 0)
    logger.info("[ClassroomWriter] 开始生成 path=%s node=%s retry=%s", path_id, node_id, retry_count)
    try:
        outline = state.get("teaching_outline")
        if outline is None:
            outline = await _plan_teaching_outline(state)
        raw_lesson = await _generate_segments(state, outline)
        lesson = _normalize_lesson(
            raw_lesson,
            state.get("fallback_lesson"),
            topic=state.get("topic", ""),
            summary=state.get("summary", ""),
            knowledge_tags=state.get("knowledge_tags", []),
            resources=state.get("resources", []),
        )
        logger.info(
            "[ClassroomWriter] 生成完成 path=%s node=%s retry=%s segments=%s elapsed=%.2fs",
            path_id,
            node_id,
            retry_count,
            len(raw_lesson.get("segments", [])),
            time.perf_counter() - started_at,
        )
        return {"teaching_outline": outline, "raw_lesson": raw_lesson, "lesson": lesson}
    except Exception:
        logger.exception("[ClassroomWriter] 生成失败 path=%s node=%s elapsed=%.2fs", path_id, node_id, time.perf_counter() - started_at)
        return {"lesson": {}, "raw_lesson": {}, "review_passed": False}


async def _plan_teaching_outline(state: ClassroomState) -> dict:
    """导演阶段：1 次 LLM 调用产出四幕蓝图和本节总结。解析失败时用默认蓝图。"""
    started_at = time.perf_counter()
    user_id_int = int(state.get("user_id", 0))
    llm_priority = state.get("llm_priority", "high")
    prompt_text = fill_prompt(
        load_prompt("classroom/writer_planner"),
        subject=state.get("subject", "未知"),
        topic=state.get("topic", ""),
        summary=state.get("summary", ""),
        knowledge_tags=json.dumps(state.get("knowledge_tags", []), ensure_ascii=False),
        quiz_config=json.dumps(state.get("quiz_config", {}), ensure_ascii=False),
        quiz_snapshot=json.dumps(state.get("quiz_snapshot", {}), ensure_ascii=False)[:900],
        resources_json=json.dumps(state.get("resources", []), ensure_ascii=False)[:2200],
        evidence_terms=json.dumps(
            _content_evidence_terms(
                state.get("topic", ""),
                state.get("summary", ""),
                *(state.get("knowledge_tags", []) or []),
                *[
                    value
                    for resource in (state.get("resources", []) or [])
                    if isinstance(resource, dict)
                    for value in (resource.get("title"), resource.get("summary"))
                ],
            ),
            ensure_ascii=False,
        ),
        portrait_context=state.get("portrait_context", "暂无画像数据"),
    )
    raw: dict = {}
    try:
        response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="classroom")
        parsed = parse_llm_json(response.content)
        if isinstance(parsed, dict):
            raw = parsed
    except Exception:
        logger.exception("[ClassroomWriter] 蓝图规划失败 path=%s node=%s", state.get("path_id"), state.get("node_id"))
    outline = _normalize_outline(raw, state)
    logger.info(
        "[ClassroomWriter] 蓝图完成 path=%s node=%s source=%s elapsed=%.2fs",
        state.get("path_id"),
        state.get("node_id"),
        "llm" if raw else "default",
        time.perf_counter() - started_at,
    )
    return outline


def _normalize_outline(raw: dict, state: ClassroomState) -> dict:
    """按 _SEGMENT_IDS 固定顺序重排/去重 segments，缺失的幕用默认 goal/focus/style 补齐。"""
    topic = state.get("topic", "当前知识点")
    default_segments = [
        {
            "id": sid,
            "goal": _DEFAULT_GOALS.get(sid, "完成本幕讲解"),
            "focus": _DEFAULT_FOCUS.get(sid, f"围绕 {topic} 展开"),
            "style": "清晰、分步、贴合画像",
        }
        for sid in _SEGMENT_IDS
    ]
    by_id: dict[str, dict] = {}
    segs = raw.get("segments") if isinstance(raw.get("segments"), list) else []
    for item in segs:
        if not isinstance(item, dict):
            continue
        sid = item.get("id")
        if sid not in _SEGMENT_TYPES:
            continue
        by_id[str(sid)] = {
            "goal": str(item.get("goal") or _DEFAULT_GOALS.get(sid, "")),
            "focus": str(item.get("focus") or _DEFAULT_FOCUS.get(sid, f"围绕 {topic} 展开")),
            "style": str(item.get("style") or "清晰、分步、贴合画像"),
        }
    merged = []
    for default in default_segments:
        merged.append(by_id.get(default["id"], default))
    takeaways = raw.get("key_takeaways") if isinstance(raw.get("key_takeaways"), list) else []
    return {
        "title": str(raw.get("title") or topic),
        "personal_summary": str(raw.get("personal_summary") or f"围绕 {topic} 完成一次互动课堂。"),
        "main_thread": str(raw.get("main_thread") or f"先分清{topic}要解决的问题，再拆开核心关系，用资料验证，最后反讲。"),
        "learning_summary": str(raw.get("learning_summary") or f"本节围绕“{topic}”理解核心概念，并用资料核对后完成一次反讲。"),
        "key_takeaways": [str(item) for item in takeaways if str(item).strip()][:4],
        "feynman_plan": raw.get("feynman_plan") if isinstance(raw.get("feynman_plan"), dict) else {},
        "segments": merged,
    }


async def _generate_segments(state: ClassroomState, outline: dict) -> dict:
    """前三幕并发生成，费曼幕等待前三幕后再生成。"""
    started_at = time.perf_counter()
    sem = asyncio.Semaphore(_MAX_SEGMENT_CONCURRENCY)
    issues = state.get("review_issues") or []
    global_feedback = state.get("review_feedback") or ""
    parallel_ids = _SEGMENT_IDS[:-1]
    logger.info(
        "[ClassroomWriter] 并行幕开始 path=%s node=%s scenes=%s",
        state.get("path_id"), state.get("node_id"), ",".join(parallel_ids),
    )
    parallel_segments = list(await asyncio.gather(*[
        _gen_segment(state, outline, sid, index, sem, issues, global_feedback)
        for index, sid in enumerate(parallel_ids)
    ]))
    logger.info(
        "[ClassroomWriter] 并行幕完成 path=%s node=%s valid=%s/%s elapsed=%.2fs",
        state.get("path_id"),
        state.get("node_id"),
        sum(bool(segment) for segment in parallel_segments),
        len(parallel_ids),
        time.perf_counter() - started_at,
    )
    feynman_started_at = time.perf_counter()
    logger.info("[ClassroomWriter] 费曼幕开始 path=%s node=%s", state.get("path_id"), state.get("node_id"))
    feynman = await _gen_segment(
        state,
        outline,
        _SEGMENT_IDS[-1],
        len(_SEGMENT_IDS) - 1,
        sem,
        issues,
        global_feedback,
        completed_segments=parallel_segments,
    )
    logger.info(
        "[ClassroomWriter] 费曼幕完成 path=%s node=%s valid=%s elapsed=%.2fs total=%.2fs",
        state.get("path_id"),
        state.get("node_id"),
        bool(feynman),
        time.perf_counter() - feynman_started_at,
        time.perf_counter() - started_at,
    )
    raw_segments = parallel_segments + [feynman]
    return {
        "title": outline.get("title", state.get("topic", "")),
        "personal_summary": outline.get("personal_summary", ""),
        "learning_summary": outline.get("learning_summary", ""),
        "key_takeaways": outline.get("key_takeaways", []),
        "segments": raw_segments,
    }


async def _gen_segment(
    state: ClassroomState,
    outline: dict,
    scene_id: str,
    index: int,
    sem: asyncio.Semaphore,
    issues: list[dict],
    global_feedback: str,
    completed_segments: list[dict] | None = None,
) -> dict:
    """生成单幕；费曼幕可接收前三幕的压缩结果。"""
    started_at = time.perf_counter()
    segs = outline.get("segments") or []
    info = segs[index] if index < len(segs) else {}
    feynman_plan = json.dumps(outline.get("feynman_plan") or {}, ensure_ascii=False)
    prompt_text = fill_prompt(
        load_prompt("classroom/writer_segment"),
        subject=state.get("subject", "未知"),
        topic=state.get("topic", ""),
        summary=state.get("summary", ""),
        knowledge_tags=json.dumps(state.get("knowledge_tags", []), ensure_ascii=False),
        portrait_context=state.get("portrait_context", "暂无画像数据"),
        resources_json=json.dumps(state.get("resources", []), ensure_ascii=False)[:1800],
        evidence_terms=json.dumps(
            _content_evidence_terms(
                state.get("topic", ""),
                state.get("summary", ""),
                *(state.get("knowledge_tags", []) or []),
                *[
                    value
                    for resource in (state.get("resources", []) or [])
                    if isinstance(resource, dict)
                    for value in (resource.get("title"), resource.get("summary"))
                ],
            ),
            ensure_ascii=False,
        ),
        scene_id=scene_id,
        scene_index=index + 1,
        scene_total=len(_SEGMENT_IDS),
        scene_goal=info.get("goal", ""),
        scene_focus=info.get("focus", ""),
        scene_style=info.get("style", ""),
        previous_scene_focus=_seg_focus(outline, index - 1),
        next_scene_focus=_seg_focus(outline, index + 1),
        main_thread=outline.get("main_thread", ""),
        feynman_plan=feynman_plan,
        completed_segments=_completed_segment_context(completed_segments),
        review_feedback=_feedback_for_segment(scene_id, issues, global_feedback),
        forbidden_phrases=json.dumps(_GENERIC_CLASSROOM_PHRASES, ensure_ascii=False),
    )
    user_id_int = int(state.get("user_id", 0))
    llm_priority = state.get("llm_priority", "high")
    try:
        async with sem:
            response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="classroom")
        parsed = parse_llm_json(response.content)
        if not isinstance(parsed, dict):
            logger.warning("[ClassroomWriter] 单幕返回非 JSON path=%s node=%s scene=%s elapsed=%.2fs", state.get("path_id"), state.get("node_id"), scene_id, time.perf_counter() - started_at)
            return {}
        parsed["id"] = scene_id
        parsed["type"] = _SEGMENT_TYPES.get(scene_id, scene_id)
        logger.info("[ClassroomWriter] 单幕完成 path=%s node=%s scene=%s elapsed=%.2fs", state.get("path_id"), state.get("node_id"), scene_id, time.perf_counter() - started_at)
        return parsed
    except Exception:
        logger.exception("[ClassroomWriter] 单幕生成失败 path=%s node=%s scene=%s elapsed=%.2fs", state.get("path_id"), state.get("node_id"), scene_id, time.perf_counter() - started_at)
        return {}


def _completed_segment_context(segments: list[dict] | None) -> str:
    """只把前三幕的关键内容交给费曼幕，避免把完整 JSON 塞进 prompt。"""
    if not segments:
        return "前三幕尚未完成；当前不是费曼幕时忽略此字段。"
    compact = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        compact.append({
            "id": segment.get("id", ""),
            "title": segment.get("title", ""),
            "teacher_speech": segment.get("teacher_speech") or segment.get("script", ""),
            "points": (segment.get("points") or segment.get("board_items") or [])[:4],
            "example": segment.get("example", ""),
            "question": (segment.get("question") or {}).get("prompt", ""),
        })
    return json.dumps(compact, ensure_ascii=False)[:5000] if compact else "前三幕没有返回可用内容。"


def _seg_focus(outline: dict, index: int) -> str:
    segs = outline.get("segments") or []
    if 0 <= index < len(segs):
        return str(segs[index].get("focus") or "")
    return ""


def _feedback_for_segment(segment_id: str, issues: list[dict], global_feedback: str) -> str:
    """把 issues 按 segment_id 过滤（None 视为全局）拼成该幕专属反馈，总体意见附加为末尾。"""
    parts: list[str] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        sid = issue.get("segment_id")
        if sid is None or str(sid) == segment_id:
            msg = str(issue.get("message") or "")
            if msg:
                parts.append(msg)
    if global_feedback:
        parts.append(f"[总体意见] {global_feedback}")
    return "\n".join(parts) if parts else ""


# ═══════════════════════════════════════
#  Reviewer — 独立审核（对象是归一化前的 raw_lesson）
# ═══════════════════════════════════════

async def reviewer_node(state: ClassroomState) -> dict:
    """一次调用审核完整 4 幕（raw_lesson）。未通过则回灌 feedback/issues。异常 fail-open。"""
    started_at = time.perf_counter()
    raw_lesson = state.get("raw_lesson") or state.get("lesson")
    if not raw_lesson or not isinstance(raw_lesson.get("segments"), list):
        return {"review_passed": True, "review_feedback": "", "retry_count": state.get("retry_count", 0)}

    user_id_int = int(state.get("user_id", 0))
    llm_priority = state.get("llm_priority", "high")
    prompt_text = fill_prompt(
        load_prompt("classroom/reviewer"),
        subject=state.get("subject", "未知"),
        topic=state.get("topic", ""),
        summary=state.get("summary", ""),
        portrait_context=state.get("portrait_context", "暂无画像数据"),
        lesson_json=json.dumps(raw_lesson, ensure_ascii=False)[:8000],
        forbidden_phrases=json.dumps(_GENERIC_CLASSROOM_PHRASES, ensure_ascii=False),
        pass_score=_REVIEW_PASS_SCORE,
    )
    try:
        response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="classroom")
        result = parse_llm_json(response.content)
        if not isinstance(result, dict):
            result = {}
    except Exception:
        logger.exception("[ClassroomReviewer] LLM 调用失败，fail-open path=%s node=%s", state.get("path_id"), state.get("node_id"))
        return {"review_passed": True, "review_feedback": "", "retry_count": state.get("retry_count", 0)}

    raw_passed, score, feedback, issues = _parse_review_result(result)
    passed = raw_passed and score >= _REVIEW_PASS_SCORE
    retry_count = state.get("retry_count", 0)
    next_retry_count = retry_count if passed else retry_count + 1
    logger.info(
        "[ClassroomReviewer] 审核完成 path=%s node=%s passed=%s score=%.1f issues=%s retry=%s elapsed=%.2fs",
        state.get("path_id"),
        state.get("node_id"),
        passed,
        score,
        len(issues),
        next_retry_count,
        time.perf_counter() - started_at,
    )
    return {
        "review_passed": passed,
        "review_score": score,
        "review_feedback": feedback[:_REVIEW_FEEDBACK_MAX_LEN] if not passed else "",
        "review_issues": issues if not passed else [],
        "retry_count": next_retry_count,
    }


def _parse_review_result(result: dict) -> tuple[bool, float, str, list[dict]]:
    """容错解析审核结果：passed 兼容 bool/str，score 取 float，issues 非 list 则置 []。"""
    passed = result.get("passed", False)
    if isinstance(passed, str):
        passed = passed.lower() in ("true", "yes", "1", "是", "pass", "通过")
    try:
        score = float(result.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    feedback = str(result.get("feedback") or "")
    issues = result.get("issues")
    if not isinstance(issues, list):
        issues = []
    return bool(passed), score, feedback, issues


# ═══════════════════════════════════════
#  Router / Graph
# ═══════════════════════════════════════

def should_continue(state: ClassroomState) -> str:
    if state.get("review_passed"):
        logger.info("[ClassroomGraph] 审核通过 path=%s node=%s", state.get("path_id"), state.get("node_id"))
        return "end"
    if state.get("retry_count", 0) >= state.get("max_retries", _MAX_REVIEW_RETRIES):
        logger.info("[ClassroomGraph] 已达最大重试次数，强制结束 path=%s node=%s", state.get("path_id"), state.get("node_id"))
        return "end"
    logger.info("[ClassroomGraph] 审核未通过，准备重试 path=%s node=%s retry=%s", state.get("path_id"), state.get("node_id"), state.get("retry_count", 0))
    return "writer"


def build_classroom_graph():
    workflow = StateGraph(ClassroomState)
    workflow.add_node("writer", writer_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_edge(START, "writer")
    workflow.add_edge("writer", "reviewer")
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {"writer": "writer", "end": END},
    )
    return workflow.compile()


classroom_graph = build_classroom_graph()

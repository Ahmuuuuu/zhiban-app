"""
LangGraph 双智能体编排 — 互动课堂脚本生成
WriterAgent(导演规划 → 并行分幕) → ReviewerAgent(独立审核 → 带反馈重写)
"""
import asyncio
import json
import logging
import re
import time
from typing import Any, TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.utils.json_parser import parse_llm_json
from backend.src.service.path.classroom import (
    _classroom_segment_narration_text,
    _normalize_lesson,
    _GENERIC_CLASSROOM_PHRASES,
    _content_evidence_terms,
    generate_classroom_audio,
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

# 审核不通过时只重写被点名的模块，最多进行一轮定向优化。
_MAX_REVIEW_RETRIES = 1
_REVIEW_PASS_SCORE = 80        # 通过阈值：score >= 80 且结构契约通过
_MAX_SEGMENT_CONCURRENCY = 4   # 四幕并行生成
_REVIEW_FEEDBACK_MAX_LEN = 400 # 回灌给 writer 的总体意见截断，防止 prompt 膨胀
_TTS_PREWARM_CONCURRENCY = 2
_tts_prewarm_sem = asyncio.Semaphore(_TTS_PREWARM_CONCURRENCY)
_tts_prewarm_tasks: set[asyncio.Task] = set()

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

_SCENE_RESPONSIBILITIES = {
    "lead-in": "结合学生画像或学习目标，说明该知识点与学生的具体关系。",
    "concept": "讲清知识点的定义、结构、关系、公式、步骤或边界。",
    "exercise": "说明现有练习将检查的知识点、判断依据或易错点。",
    "feynman": "给出具体反讲任务，要求学生在右侧对话框作答。",
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
    trace_id: NotRequired[str]         # 一次课堂请求的日志关联标识

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
    trace_id = state.get("trace_id", "-")
    logger.info("[ClassroomWriter] 开始生成 trace=%s path=%s node=%s retry=%s", trace_id, path_id, node_id, retry_count)
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
            "[ClassroomWriter] 生成完成 trace=%s path=%s node=%s retry=%s segments=%s elapsed=%.2fs",
            trace_id,
            path_id,
            node_id,
            retry_count,
            len(raw_lesson.get("segments", [])),
            time.perf_counter() - started_at,
        )
        return {"teaching_outline": outline, "raw_lesson": raw_lesson, "lesson": lesson}
    except Exception:
        logger.exception("[ClassroomWriter] 生成失败 trace=%s path=%s node=%s elapsed=%.2fs", trace_id, path_id, node_id, time.perf_counter() - started_at)
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
        logger.info("[ClassroomWriter] 蓝图请求模型 trace=%s path=%s node=%s", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"))
        response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="classroom")
        parsed = parse_llm_json(response.content)
        if isinstance(parsed, dict):
            raw = parsed
    except Exception:
        logger.exception("[ClassroomWriter] 蓝图规划失败 trace=%s path=%s node=%s", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"))
    outline = _normalize_outline(raw, state)
    logger.info(
        "[ClassroomWriter] 蓝图完成 trace=%s path=%s node=%s source=%s elapsed=%.2fs",
        state.get("trace_id", "-"),
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
    """首轮生成四幕；审核后的定向优化只重写被点名的幕。"""
    started_at = time.perf_counter()
    sem = asyncio.Semaphore(_MAX_SEGMENT_CONCURRENCY)
    issues = state.get("review_issues") or []
    global_feedback = state.get("review_feedback") or ""
    retry_count = state.get("retry_count", 0)
    previous_raw = state.get("raw_lesson") if isinstance(state.get("raw_lesson"), dict) else {}
    previous_by_id = {
        str(segment.get("id")): segment
        for segment in previous_raw.get("segments", [])
        if isinstance(segment, dict) and str(segment.get("id")) in _SEGMENT_IDS
    }
    targeted_ids = {
        str(issue.get("segment_id"))
        for issue in issues
        if isinstance(issue, dict) and str(issue.get("segment_id")) in _SEGMENT_IDS
    }
    is_targeted_retry = retry_count > 0 and len(previous_by_id) == len(_SEGMENT_IDS) and bool(targeted_ids)

    if retry_count > 0 and not is_targeted_retry:
        logger.warning(
            "[ClassroomWriter] 审核未给出可定位模块，不重写整课 path=%s node=%s retry=%s",
            state.get("path_id"), state.get("node_id"), retry_count,
        )
        return previous_raw

    parallel_ids = _SEGMENT_IDS[:-1]
    logger.info(
        "[ClassroomWriter] 并行幕开始 trace=%s path=%s node=%s scenes=%s mode=%s",
        state.get("trace_id", "-"),
        state.get("path_id"), state.get("node_id"), ",".join(parallel_ids),
        "targeted" if is_targeted_retry else "initial",
    )
    parallel_jobs = [
        _gen_segment(state, outline, sid, index, sem, issues, global_feedback)
        for index, sid in enumerate(parallel_ids)
        if not is_targeted_retry or sid in targeted_ids
    ]
    generated_parallel = await asyncio.gather(*parallel_jobs) if parallel_jobs else []
    generated_by_id = {str(segment.get("id")): segment for segment in generated_parallel if isinstance(segment, dict)}
    parallel_segments = [generated_by_id.get(sid) or previous_by_id.get(sid, {}) for sid in parallel_ids]
    logger.info(
        "[ClassroomWriter] 并行幕完成 trace=%s path=%s node=%s valid=%s/%s elapsed=%.2fs",
        state.get("trace_id", "-"),
        state.get("path_id"),
        state.get("node_id"),
        sum(bool(segment) for segment in parallel_segments),
        len(parallel_ids),
        time.perf_counter() - started_at,
    )
    feynman_started_at = time.perf_counter()
    should_rewrite_feynman = not is_targeted_retry or _SEGMENT_IDS[-1] in targeted_ids
    if should_rewrite_feynman:
        logger.info("[ClassroomWriter] 费曼幕开始 trace=%s path=%s node=%s", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"))
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
    else:
        feynman = previous_by_id.get(_SEGMENT_IDS[-1], {})
        logger.info("[ClassroomWriter] 费曼幕复用 path=%s node=%s", state.get("path_id"), state.get("node_id"))
    logger.info(
        "[ClassroomWriter] 费曼幕完成 trace=%s path=%s node=%s valid=%s elapsed=%.2fs total=%.2fs",
        state.get("trace_id", "-"),
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
    queue_started_at = time.perf_counter()
    try:
        logger.info("[ClassroomWriter] 单幕等待并发槽 trace=%s path=%s node=%s scene=%s", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"), scene_id)
        async with sem:
            logger.info("[ClassroomWriter] 单幕请求模型 trace=%s path=%s node=%s scene=%s queue_wait=%.2fs", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"), scene_id, time.perf_counter() - queue_started_at)
            response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="classroom")
        parsed = parse_llm_json(response.content)
        if not isinstance(parsed, dict):
            logger.warning("[ClassroomWriter] 单幕返回非 JSON trace=%s path=%s node=%s scene=%s elapsed=%.2fs", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"), scene_id, time.perf_counter() - started_at)
            return {}
        parsed["id"] = scene_id
        parsed["type"] = _SEGMENT_TYPES.get(scene_id, scene_id)
        narration_text = _classroom_segment_narration_text(parsed)
        if narration_text:
            task = asyncio.create_task(
                _prewarm_segment_audio(
                    user_id=user_id_int,
                    path_id=int(state.get("path_id", 0)),
                    node_id=int(state.get("node_id", 0)),
                    scene_id=scene_id,
                    text=narration_text,
                )
            )
            _tts_prewarm_tasks.add(task)
            task.add_done_callback(_tts_prewarm_tasks.discard)
        logger.info("[ClassroomWriter] 单幕完成 trace=%s path=%s node=%s scene=%s chars=%s elapsed=%.2fs", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"), scene_id, len(str(parsed.get("teacher_speech") or parsed.get("script") or "")), time.perf_counter() - started_at)
        return parsed
    except Exception:
        logger.exception("[ClassroomWriter] 单幕生成失败 trace=%s path=%s node=%s scene=%s elapsed=%.2fs", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"), scene_id, time.perf_counter() - started_at)
        return {}


async def _prewarm_segment_audio(
    user_id: int,
    path_id: int,
    node_id: int,
    scene_id: str,
    text: str,
) -> None:
    """分幕生成后立即预热语音；失败不影响课堂正文和审核。"""
    try:
        async with _tts_prewarm_sem:
            await generate_classroom_audio(text, user_id)
        logger.info(
            "[ClassroomTTS] 预热完成 path=%s node=%s scene=%s chars=%s",
            path_id,
            node_id,
            scene_id,
            len(text),
        )
    except Exception:
        logger.exception(
            "[ClassroomTTS] 预热失败 path=%s node=%s scene=%s",
            path_id,
            node_id,
            scene_id,
        )


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
    """四个审核智能体并行检查分幕；只把问题回灌给对应模块。"""
    started_at = time.perf_counter()
    trace_id = state.get("trace_id", "-")
    raw_lesson = state.get("raw_lesson") or state.get("lesson")
    if not raw_lesson or not isinstance(raw_lesson.get("segments"), list):
        logger.warning("[ClassroomReviewer] 审核跳过：课堂为空 trace=%s path=%s node=%s", trace_id, state.get("path_id"), state.get("node_id"))
        return {"review_passed": False, "review_score": 0, "review_feedback": "课堂结构为空", "review_issues": [], "retry_count": state.get("retry_count", 0)}

    segments_by_id = {
        str(segment.get("id")): segment
        for segment in raw_lesson.get("segments", [])
        if isinstance(segment, dict) and str(segment.get("id")) in _SEGMENT_IDS
    }
    missing_ids = [scene_id for scene_id in _SEGMENT_IDS if scene_id not in segments_by_id]
    if missing_ids:
        issues = [{"segment_id": scene_id, "category": "structure", "message": "缺少课堂模块"} for scene_id in missing_ids]
        retry_count = state.get("retry_count", 0)
        can_retry = retry_count < state.get("max_retries", _MAX_REVIEW_RETRIES)
        logger.warning(
            "[ClassroomReviewer] 结构审核失败 trace=%s path=%s node=%s missing=%s retry=%s can_retry=%s",
            trace_id,
            state.get("path_id"),
            state.get("node_id"),
            ",".join(missing_ids),
            retry_count,
            can_retry,
        )
        return {
            "review_passed": False,
            "review_score": 0,
            "review_feedback": "课堂模块不完整",
            "review_issues": issues if can_retry else [],
            "retry_count": retry_count + 1 if can_retry else retry_count,
        }

    structural_issues: list[dict[str, Any]] = []
    for scene_id, segment in segments_by_id.items():
        script = str(segment.get("teacher_speech") or segment.get("script") or "").strip()
        board_items = segment.get("board_items") if isinstance(segment.get("board_items"), list) else []
        points = segment.get("points") if isinstance(segment.get("points"), list) else []
        question = segment.get("question") if isinstance(segment.get("question"), dict) else {}
        if not str(segment.get("title") or "").strip() or len(script) < 30 or len(board_items) < 2 or len(points) < 2 or len(str(question.get("prompt") or "").strip()) < 6:
            structural_issues.append({"segment_id": scene_id, "category": "structure", "message": "讲稿、要点或互动问题不完整"})
    concept_issue = _concept_definition_contract_issue(
        segments_by_id.get("concept", {}),
        state.get("knowledge_tags", []),
    )
    if concept_issue:
        structural_issues.append(concept_issue)
    if structural_issues:
        retry_count = state.get("retry_count", 0)
        can_retry = retry_count < state.get("max_retries", _MAX_REVIEW_RETRIES)
        logger.warning(
            "[ClassroomReviewer] 展示契约失败 trace=%s path=%s node=%s scenes=%s retry=%s can_retry=%s",
            trace_id,
            state.get("path_id"),
            state.get("node_id"),
            ",".join(str(item.get("segment_id")) for item in structural_issues),
            retry_count,
            can_retry,
        )
        return {
            "review_passed": False,
            "review_score": 0,
            "review_feedback": "课堂结构不完整",
            "review_issues": structural_issues if can_retry else [],
            "retry_count": retry_count + 1 if can_retry else retry_count,
        }

    user_id_int = int(state.get("user_id", 0))
    llm_priority = state.get("llm_priority", "high")
    logger.info("[ClassroomReviewer] 并行审核开始 trace=%s path=%s node=%s scenes=%s", trace_id, state.get("path_id"), state.get("node_id"), ",".join(_SEGMENT_IDS))

    async def review_scene(scene_id: str) -> tuple[str, bool, float, str, list[dict]]:
        review_started_at = time.perf_counter()
        prompt_text = fill_prompt(
            load_prompt("classroom/reviewer_segment"),
            subject=state.get("subject", "未知"),
            topic=state.get("topic", ""),
            summary=state.get("summary", ""),
            knowledge_tags=json.dumps(state.get("knowledge_tags", []), ensure_ascii=False),
            resources_json=json.dumps(state.get("resources", []), ensure_ascii=False)[:1800],
            evidence_terms=json.dumps(
                _content_evidence_terms(
                    state.get("topic", ""),
                    state.get("summary", ""),
                    *(state.get("knowledge_tags", []) or []),
                ),
                ensure_ascii=False,
            ),
            scene_id=scene_id,
            scene_responsibility=_SCENE_RESPONSIBILITIES[scene_id],
            segment_json=json.dumps(segments_by_id[scene_id], ensure_ascii=False)[:2600],
        )
        try:
            logger.info("[ClassroomReviewer] 单幕请求模型 trace=%s path=%s node=%s scene=%s", trace_id, state.get("path_id"), state.get("node_id"), scene_id)
            response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="classroom")
            result = parse_llm_json(response.content)
            if not isinstance(result, dict):
                result = {}
            raw_passed, score, feedback, issues = _parse_review_result(result)
            normalized_issues = [
                {"segment_id": scene_id, "category": str(issue.get("category") or "quality"), "message": str(issue.get("message") or feedback or "需要优化当前模块")}
                for issue in issues if isinstance(issue, dict)
            ]
            passed = raw_passed and score >= _REVIEW_PASS_SCORE
            if not passed and not normalized_issues:
                normalized_issues = [{"segment_id": scene_id, "category": "quality", "message": feedback or "当前模块未达到审核要求"}]
            logger.info(
                "[ClassroomReviewer] 单幕审核完成 trace=%s path=%s node=%s scene=%s passed=%s score=%.1f issues=%s elapsed=%.2fs",
                trace_id,
                state.get("path_id"),
                state.get("node_id"),
                scene_id,
                passed,
                score,
                len(normalized_issues),
                time.perf_counter() - review_started_at,
            )
            return scene_id, passed, score, feedback, normalized_issues
        except Exception:
            logger.exception("[ClassroomReviewer] 分幕审核失败，保留当前幕 trace=%s path=%s node=%s scene=%s elapsed=%.2fs", trace_id, state.get("path_id"), state.get("node_id"), scene_id, time.perf_counter() - review_started_at)
            return scene_id, True, 0.0, "", []

    scene_reviews = await asyncio.gather(*(review_scene(scene_id) for scene_id in _SEGMENT_IDS))
    passed = all(item[1] for item in scene_reviews)
    score = min((item[2] for item in scene_reviews), default=0.0)
    feedback = "\n".join(item[3] for item in scene_reviews if item[3])[:_REVIEW_FEEDBACK_MAX_LEN]
    issues = [issue for item in scene_reviews for issue in item[4]]
    retry_count = state.get("retry_count", 0)
    actionable_issues = [
        issue for issue in issues
        if isinstance(issue, dict) and str(issue.get("segment_id")) in _SEGMENT_IDS
    ]
    can_retry = not passed and retry_count < state.get("max_retries", _MAX_REVIEW_RETRIES) and bool(actionable_issues)
    next_retry_count = retry_count + 1 if can_retry else retry_count
    logger.info(
        "[ClassroomReviewer] 审核完成 trace=%s path=%s node=%s passed=%s score=%.1f issues=%s targeted=%s retry=%s elapsed=%.2fs",
        trace_id,
        state.get("path_id"),
        state.get("node_id"),
        passed,
        score,
        len(issues),
        ",".join(str(item.get("segment_id")) for item in actionable_issues) or "none",
        next_retry_count,
        time.perf_counter() - started_at,
    )
    return {
        # 没有精确模块的问题时不允许全课重写，保留当前完整课堂。
        "review_passed": passed or not can_retry,
        "review_score": score,
        "review_feedback": feedback[:_REVIEW_FEEDBACK_MAX_LEN] if not passed else "",
        "review_issues": actionable_issues if can_retry else [],
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


def _concept_definition_contract_issue(segment: dict, knowledge_tags: list[Any]) -> dict | None:
    """拦截把例子、结论或数值当作概念定义的核心讲解。"""
    if not isinstance(segment, dict):
        return {"segment_id": "concept", "category": "concept_definition", "message": "核心概念模块缺失"}

    speech = str(segment.get("teacher_speech") or segment.get("script") or "").strip()
    opening = speech[:190]
    definition_pattern = re.compile(
        r"(?:^|[。；;，,])[^。；;，,]{0,30}?(?:是(?:一种|指|用来|用于)|指的是|用于|表示的是)"
    )
    definition_count = len(definition_pattern.findall(opening))
    if definition_count < 1:
        return {
            "segment_id": "concept",
            "category": "concept_definition",
            "message": "核心概念必须先用“X 是一种…/X 指…/X 用于…”明确下定义，不能直接从例子、数值或结果开始。",
        }

    targets: list[str] = []
    for tag in knowledge_tags if isinstance(knowledge_tags, list) else []:
        term = str(tag or "").strip()
        if 2 <= len(term) <= 32 and term not in targets:
            targets.append(term)
    required_definitions = 2 if len(targets) >= 2 else 1
    if definition_count < required_definitions:
        return {
            "segment_id": "concept",
            "category": "concept_definition",
            "message": "核心概念包含多个术语时，需分别定义至少两个术语，再讲它们的关系和例子。",
        }
    return None


# ═══════════════════════════════════════
#  Router / Graph
# ═══════════════════════════════════════

def should_continue(state: ClassroomState) -> str:
    if state.get("review_passed"):
        logger.info("[ClassroomGraph] 审核通过或无需全课重写，结束 trace=%s path=%s node=%s", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"))
        return "end"
    issues = state.get("review_issues") or []
    if issues:
        logger.info("[ClassroomGraph] 定向优化模块 trace=%s path=%s node=%s scenes=%s", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"), ",".join(str(item.get("segment_id")) for item in issues))
        return "writer"
    logger.warning("[ClassroomGraph] 审核未通过但无可修复模块，结束 trace=%s path=%s node=%s", state.get("trace_id", "-"), state.get("path_id"), state.get("node_id"))
    return "end"


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

"""
LangGraph 多智能体编排 — 学习资源生成
LeaderAgent → [ExecutorAgent × N 多线程并行] → ReviewerAgent
"""
import asyncio
import concurrent.futures
import json
import logging
import threading
from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

# 资源类型 → 默认 prompt 路径
PROMPT_MAP = {
    "document": "resource/document",
    "ppt": "resource/ppt",
    "mindmap": "resource/mindmap",
    "exercise": "resource/exam",
    "case": "resource/document",
    "reading": "resource/document",
    "image": "resource/image_prompt",
}


# ═══════════════════════════════════════
#  State
# ═══════════════════════════════════════

class ResourceState(TypedDict):
    user_id: str
    topic: str
    resource_types: list[str]
    portrait_context: str
    kb_context: str
    learning_guidance: str
    user_notes: str
    custom_prompts: dict
    generated_resources: dict
    review_feedback: str
    review_passed: bool
    retry_count: int
    exam_question_types: str
    exam_count: str
    exam_difficulty: str
    reviewer_questions: list[dict]
    file_urls: NotRequired[dict[str, str]]
    answers: NotRequired[dict]
    skip_review: NotRequired[bool]


# ═══════════════════════════════════════
#  Nodes
# ═══════════════════════════════════════

async def leader_node(state: ResourceState) -> dict:
    """LeaderAgent: 分析需求，决定生成哪些资源类型（用户已指定则跳过 LLM）"""
    requested = state.get("resource_types") or []
    if requested:
        return {"resource_types": requested}

    topic = state["topic"]
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    guidance = state.get("learning_guidance", "")
    prompt_text = fill_prompt(load_prompt("agent/leader"), topic=topic, portrait_context=portrait, kb_context=kb, learning_guidance=guidance)

    try:
        response = await llm.ainvoke(prompt_text)
    except Exception as e:
        logger.exception("LeaderAgent LLM 调用失败")
        return {"resource_types": ["document"]}

    try:
        plan = parse_llm_json(response.content)
    except json.JSONDecodeError:
        plan = {"resource_types": ["document"], "topic": topic, "outline": response.content.strip()}

    resource_types = plan.get("resource_types", ["document"])
    return {"resource_types": resource_types}


async def executor_node(state: ResourceState) -> dict:
    """多线程并行生成（ThreadPoolExecutor），信号量限流。
    PPT 走 LLM 生成 markdown；image 走两阶段：LLM prompt → ImageService 生图。
    """
    topic = state["topic"]
    resource_types = state.get("resource_types", ["document"])
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    guidance = state.get("learning_guidance", "")
    custom_prompts = state.get("custom_prompts", {}) or {}
    feedback = state.get("review_feedback", "")

    # 从追问答案提取聚焦方向和深度，注入 prompt 实现按需生成
    answers = state.get("answers", {}) or {}
    focus_guidance = _build_focus_guidance(answers)

    # 预先构建每个类型的 prompt（同步，快）
    prompts: dict[str, str] = {}
    for rt in resource_types:
        custom = custom_prompts.get(rt, "")
        if custom.strip():
            template = custom
        else:
            prompt_path = PROMPT_MAP.get(rt, "resource/document")
            template = load_prompt(prompt_path)
        base = fill_prompt(
            template,
            topic=topic,
            resource_type=rt,
            portrait_context=portrait,
            kb_context=kb,
            learning_guidance=guidance,
            user_notes=state.get("user_notes", ""),
            feedback=feedback,
            count=state.get("exam_count", "5"),
            question_types=state.get("exam_question_types", "single_choice, multi_choice, true_false"),
            difficulty=state.get("exam_difficulty", "medium"),
        )
        prompts[rt] = base + focus_guidance if focus_guidance else base

    user_id = state.get("user_id", "0")
    semaphore = threading.Semaphore(5)
    max_workers = min(len(resource_types), 5)

    def gen_one_sync(rt: str) -> tuple[str, str]:
        """同步 LLM 调用，运行在线程池中实现真正多线程并行"""
        with semaphore:
            try:
                if rt == "ppt":
                    return _generate_ppt_sync(topic, portrait, guidance, user_id)
                if rt == "image":
                    return _generate_image_sync(prompts[rt], user_id, loop)
                response = llm.invoke(prompts[rt])
                return rt, response.content
            except Exception as e:
                logger.exception(f"Executor [{rt}] 调用失败")
                return rt, f"[生成失败: {e}]"

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [loop.run_in_executor(pool, gen_one_sync, rt) for rt in resource_types]
        results = await asyncio.gather(*futures)

    retry = state.get("retry_count", 0)
    if feedback:
        retry += 1

    # 分离普通资源和 file_urls（image 类型返回特殊 key）
    generated = {}
    file_urls = {}
    for rt, content in results:
        if rt.startswith("image:"):
            actual_rt = rt.replace("image:", "")
            generated[actual_rt] = content.get("prompt", "")
            if content.get("url"):
                file_urls[actual_rt] = content["url"]
        else:
            generated[rt] = content

    return {
        "generated_resources": generated,
        "file_urls": file_urls,
        "retry_count": retry,
        "review_feedback": "",
    }


def _generate_image_sync(prompt_text: str, user_id: str, loop) -> tuple[str, dict]:
    """两阶段图片生成：LLM 产出 prompt → ImageService 生图（线程内同步调用）"""
    try:
        response = llm.invoke(prompt_text)
        image_prompt = response.content.strip()
    except Exception as e:
        logger.exception("图片 prompt 生成失败")
        return ("image:error", {"prompt": "", "url": ""})

    try:
        from backend.src.service.image_service import ImageService
        image_prompt = image_prompt[:900]
        future = asyncio.run_coroutine_threadsafe(
            ImageService.generate(image_prompt, user_id, aspect_ratio="16:9", img_count=2),
            loop
        )
        images = future.result(timeout=120)
        if images and len(images) > 0:
            return ("image:image", {"prompt": image_prompt, "url": images[0].get("url", "")})
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")

    return ("image:image", {"prompt": image_prompt, "url": ""})


def _generate_ppt_sync(topic: str, portrait: str, guidance: str, user_id: str) -> tuple[str, str]:
    """PPT 生成：LLM 生成 markdown 内容（线程内同步调用）"""
    try:
        prompt_path = PROMPT_MAP.get("ppt", "resource/ppt")
        template = load_prompt(prompt_path)
        fallback_prompt = fill_prompt(
            template, topic=topic, resource_type="ppt",
            portrait_context=portrait, kb_context="",
            learning_guidance=guidance, feedback="",
        )
        response = llm.invoke(fallback_prompt)
        return ("ppt", response.content)
    except Exception as e:
        logger.exception(f"PPT 生成失败")
        return ("ppt", f"[生成失败: {e}]")


def _parse_review_response(raw: str) -> dict:
    """解析 reviewer 返回的 JSON，容错处理。
    支持新格式（逐题）和旧格式（整批），统一返回含 questions 字段的 dict。"""
    try:
        result = parse_llm_json(raw)
        if not isinstance(result, dict):
            return {"passed": True, "score": 70, "feedback": raw, "questions": []}
        # exercise 新格式：包含逐题结果
        if "questions" in result and isinstance(result["questions"], list):
            return {
                "passed": result.get("overall_passed", True),
                "score": result.get("overall_score", 70),
                "feedback": result.get("overall_feedback", ""),
                "questions": result["questions"],
            }
        # 旧格式兼容（其他资源类型）
        return {
            "passed": result.get("passed", True),
            "score": result.get("score", 70),
            "feedback": result.get("feedback", ""),
            "questions": [],
        }
    except json.JSONDecodeError:
        return {"passed": True, "score": 70, "feedback": raw, "questions": []}


# 资源类型 → 专用审核员
_REVIEWER_MAP = {
    "document": "agent/reviewer_document",
    "case": "agent/reviewer_document",
    "reading": "agent/reviewer_document",
    "ppt": "agent/reviewer_ppt",
    "exercise": "agent/reviewer_exam",
    "mindmap": "agent/mindmap_reviewer",
    "image": "agent/reviewer_image",
}


async def reviewer_node(state: ResourceState) -> dict:
    """ReviewerAgent: 每种资源类型由专用审核员独立审查，并行执行"""
    generated = state.get("generated_resources", {})

    async def review_one(rt: str, content: str) -> dict:
        # API 生成的图片跳过文本审核（PPT 为 LLM 生成，需审核）
        file_urls = state.get("file_urls", {})
        if rt != "ppt" and file_urls.get(rt):
            return {"passed": True, "score": 100, "feedback": "API 生成，自动通过"}
        reviewer_path = _REVIEWER_MAP.get(rt, "agent/reviewer_document")
        if not content:
            return {"passed": True, "score": 100, "feedback": ""}
        try:
            content_snippet = content[:3000]
            prompt_text = fill_prompt(
                load_prompt(reviewer_path),
                content=content_snippet,
                topic=state.get("topic", ""),
                kb_context=state.get("kb_context", "暂无相关知识库资料"),
            )
            response = await llm.ainvoke(prompt_text)
            result = _parse_review_response(response.content)
            logger.info(f"[审核] {rt}: passed={result.get('passed')} score={result.get('score')}")
            return result
        except Exception as e:
            logger.exception(f"[审核] {rt} 失败")
            return {"passed": True, "score": 0, "feedback": f"审核异常: {e}"}

    tasks = [review_one(rt, content) for rt, content in generated.items()]
    if not tasks:
        return {"review_passed": True, "review_feedback": ""}

    results = await asyncio.gather(*tasks)

    # 汇总
    feedback_parts = []
    all_passed = True
    question_results = []
    for (rt, _), result in zip(generated.items(), results):
        passed = result.get("passed", False)
        if isinstance(passed, str):
            passed = passed.lower() in ("true", "yes", "1", "是", "pass")
        if not passed:
            all_passed = False
            feedback_parts.append(f"[{rt}] {result.get('feedback', '')}")
        # 收集 per-question 审核结果（exercise 类型）
        for q in result.get("questions", []):
            question_results.append(q)

    return {
        "review_passed": all_passed,
        "review_feedback": "\n".join(feedback_parts),
        "reviewer_questions": question_results,
    }


def _build_focus_guidance(answers: dict) -> str:
    """从追问答案提取聚焦方向和深度，构建 prompt 约束指令。
    无 answers 时返回空字符串，不影响常规生成。
    """
    if not answers:
        return ""

    # 提取所有 focus 值
    focus_vals: list[str] = []
    for key, val in answers.items():
        if key.startswith("focus") or key == "focus":
            if isinstance(val, list):
                focus_vals.extend(str(v) for v in val)
            elif val:
                focus_vals.append(str(val))

    depth = answers.get("depth", "")
    if not focus_vals and not depth:
        return ""

    parts: list[str] = ["\n\n【学习方向与深度约束 — 必须严格遵守】"]
    if focus_vals:
        kw = "、".join(focus_vals)
        parts.append(f"- 聚焦主题：{kw}")
        parts.append("- 仅生成上述方向的内容，不要展开无关话题")
    if depth:
        depth_map = {
            "overview": "- 深度：5分钟快速概览，只讲核心概念和关键结论，省略推导和案例",
            "standard": "- 深度：标准讲解，涵盖原理和应用，适量举例",
            "deep": "- 深度：逐页详解，包含完整推导、案例分析和深入讨论",
        }
        parts.append(depth_map.get(depth, f"- 深度：{depth}"))

    parts.append("- 请根据以上约束减少内容体量，精简字数，不要为凑篇幅而添加无关信息")
    return "\n".join(parts)


# ═══════════════════════════════════════
#  Router
# ═══════════════════════════════════════

def should_continue(state: ResourceState) -> str:
    if state.get("review_passed"):
        return "end"
    if state.get("retry_count", 0) >= 2:
        return "end"
    return "executor"


def should_review(state: ResourceState) -> str:
    """跳过审核可省掉一轮 LLM 调用，适用于学习路径等对质量要求不极端的场景"""
    if state.get("skip_review"):
        return "end"
    return "reviewer"


# ═══════════════════════════════════════
#  Graph
# ═══════════════════════════════════════

def build_graph():
    workflow = StateGraph(ResourceState)

    workflow.add_node("leader", leader_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.add_edge(START, "leader")
    workflow.add_edge("leader", "executor")
    workflow.add_conditional_edges(
        "executor",
        should_review,
        {"reviewer": "reviewer", "end": END},
    )
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {"executor": "executor", "end": END},
    )

    return workflow.compile()


resource_graph = build_graph()

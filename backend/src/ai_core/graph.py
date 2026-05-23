"""
LangGraph 多智能体编排 — 学习资源生成
LeaderAgent → [ExecutorAgent × N 多线程并行] → ReviewerAgent
"""
import asyncio
import json
import logging
from typing import TypedDict

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
}


# ═══════════════════════════════════════
#  State
# ═══════════════════════════════════════

class ResourceState(TypedDict):
    user_id: str
    topic: str
    resource_types: list[str]           # ["document", "ppt"]
    portrait_context: str
    kb_context: str
    custom_prompts: dict                # {"document": "用户定制prompt", ...}
    generated_resources: dict           # {"document": "内容", "ppt": "内容"}
    review_feedback: str
    review_passed: bool
    retry_count: int
    # exam 参数（exercise 类型使用）
    exam_question_types: str            # "single_choice, multi_choice, true_false"
    exam_count: str                     # "5"
    exam_difficulty: str                # "medium"
    # reviewer 逐题结果
    reviewer_questions: list[dict]      # [{index, passed, score, feedback}, ...]


# ═══════════════════════════════════════
#  Nodes
# ═══════════════════════════════════════

async def leader_node(state: ResourceState) -> dict:
    """LeaderAgent: 分析需求，决定生成哪些资源类型"""
    topic = state["topic"]
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    prompt_text = fill_prompt(load_prompt("agent/leader"), topic=topic, portrait_context=portrait, kb_context=kb)

    try:
        response = await llm.ainvoke(prompt_text)
    except Exception as e:
        logger.exception("LeaderAgent LLM 调用失败")
        return {"resource_types": state.get("resource_types", ["document"])}

    try:
        plan = parse_llm_json(response.content)
    except json.JSONDecodeError:
        plan = {"resource_types": ["document"], "topic": topic, "outline": response.content.strip()}

    # 用户已指定资源类型则尊重用户选择，否则由 Leader 决定
    requested = state.get("resource_types", ["document"])
    if requested != ["document"]:
        resource_types = requested
    else:
        resource_types = plan.get("resource_types", ["document"])

    return {"resource_types": resource_types}


async def executor_node(state: ResourceState) -> dict:
    """多 Executor 并行生成 — 线程池 + 信号量限流"""
    topic = state["topic"]
    resource_types = state.get("resource_types", ["document"])
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    custom_prompts = state.get("custom_prompts", {}) or {}
    feedback = state.get("review_feedback", "")

    # 预先构建每个类型的 prompt（同步，快）
    prompts: dict[str, str] = {}
    for rt in resource_types:
        custom = custom_prompts.get(rt, "")
        if custom.strip():
            template = custom
        else:
            prompt_path = PROMPT_MAP.get(rt, "resource/document")
            template = load_prompt(prompt_path)
        prompts[rt] = fill_prompt(
            template,
            topic=topic,
            resource_type=rt,
            portrait_context=portrait,
            kb_context=kb,
            feedback=feedback,
            count=state.get("exam_count", "5"),
            question_types=state.get("exam_question_types", "single_choice, multi_choice, true_false"),
            difficulty=state.get("exam_difficulty", "medium"),
        )

    # 信号量限制最大并发数，防止 DeepSeek 限流
    semaphore = asyncio.Semaphore(5)

    async def gen_one(rt: str) -> tuple[str, str]:
        async with semaphore:
            try:
                response = await llm.ainvoke(prompts[rt])
                return rt, response.content
            except Exception as e:
                logger.exception(f"Executor [{rt}] LLM 调用失败")
                return rt, f"[生成失败: {e}]"

    results = await asyncio.gather(*(gen_one(rt) for rt in resource_types))

    retry = state.get("retry_count", 0)
    if feedback:
        retry += 1

    return {
        "generated_resources": dict(results),
        "retry_count": retry,
        "review_feedback": "",
    }


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
}


async def reviewer_node(state: ResourceState) -> dict:
    """ReviewerAgent: 每种资源类型由专用审核员独立审查，并行执行"""
    generated = state.get("generated_resources", {})

    async def review_one(rt: str, content: str) -> dict:
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
            passed = passed.lower() == "true"
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


# ═══════════════════════════════════════
#  Router
# ═══════════════════════════════════════

def should_continue(state: ResourceState) -> str:
    if state.get("review_passed"):
        return "end"
    if state.get("retry_count", 0) >= 2:
        return "end"
    return "executor"


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
    workflow.add_edge("executor", "reviewer")
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {"executor": "executor", "end": END},
    )

    return workflow.compile()


resource_graph = build_graph()

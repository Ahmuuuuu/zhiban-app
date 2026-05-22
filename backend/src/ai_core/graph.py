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
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        plan = json.loads(content)
    except json.JSONDecodeError:
        plan = {"resource_types": ["document"], "topic": topic, "outline": content}

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
            count="5",
            question_types="single_choice",
            difficulty="medium",
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
    """解析 reviewer 返回的 JSON，容错处理"""
    try:
        result = parse_llm_json(raw)
        return result if isinstance(result, dict) else {"passed": True, "score": 70, "feedback": raw}
    except json.JSONDecodeError:
        return {"passed": True, "score": 70, "feedback": raw}


async def reviewer_node(state: ResourceState) -> dict:
    """ReviewerAgent: 内容审核 + 思维导图结构审核，并行执行"""
    generated = state.get("generated_resources", {})

    mindmap_content = generated.get("mindmap", "")
    reviewable = {rt: c for rt, c in generated.items() if rt != "mindmap"}

    async def review_content() -> dict:
        """审核文档/PPT/题目等内容"""
        if not reviewable:
            return {"passed": True, "score": 100, "feedback": ""}
        try:
            parts = []
            for rt, content in reviewable.items():
                parts.append(f"## [{rt}]\n{content[:2000]}...")
            combined = "\n\n".join(parts)
            prompt_text = fill_prompt(load_prompt("agent/reviewer"), content=combined)
            response = await llm.ainvoke(prompt_text)
            return _parse_review_response(response.content)
        except Exception as e:
            logger.exception("内容审核 LLM 调用失败")
            return {"passed": True, "score": 0, "feedback": f"审核服务异常: {e}"}

    async def review_mindmap() -> dict:
        """审核思维导图结构"""
        if not mindmap_content:
            return {"passed": True, "score": 100, "feedback": ""}
        try:
            prompt_text = fill_prompt(
                load_prompt("agent/mindmap_reviewer"),
                mindmap_content=mindmap_content[:3000],
            )
            response = await llm.ainvoke(prompt_text)
            return _parse_review_response(response.content)
        except Exception as e:
            logger.exception("思维导图结构审核 LLM 调用失败")
            return {"passed": True, "score": 0, "feedback": f"审核服务异常: {e}"}

    # 并行审核
    content_result, mindmap_result = await asyncio.gather(
        review_content(), review_mindmap()
    )

    content_passed = content_result.get("passed", False)
    mindmap_passed = mindmap_result.get("passed", False)
    if isinstance(content_passed, str):
        content_passed = content_passed.lower() == "true"
    if isinstance(mindmap_passed, str):
        mindmap_passed = mindmap_passed.lower() == "true"

    # 汇总 feedback
    feedback_parts = []
    if not content_passed:
        feedback_parts.append(f"[内容审核] {content_result.get('feedback', '')}")
    if not mindmap_passed:
        feedback_parts.append(f"[结构审核] {mindmap_result.get('feedback', '')}")

    return {
        "review_passed": content_passed and mindmap_passed,
        "review_feedback": "\n".join(feedback_parts),
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

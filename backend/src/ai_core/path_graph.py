"""
LangGraph 多智能体编排 — 个性化学习路径生成
LeaderAgent(规划大纲) → ExecutorAgent(并行分组生成节点) → ReviewerAgent(审核)
"""
import asyncio
import json
import logging
import time
from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

# 每组最多生成的节点数（并行分组）
_GROUP_SIZE = 4


# ═══════════════════════════════════════
#  State
# ═══════════════════════════════════════

class PathState(TypedDict):
    user_id: str
    subject: str
    difficulty: str
    node_count: int
    portrait_context: str
    mastery_context: str
    kb_context: str
    learning_guidance: str
    # Leader 输出
    topic_outline: NotRequired[list[dict]]
    # Executor 输出
    nodes: NotRequired[list[dict]]
    # Reviewer 输出
    review_passed: NotRequired[bool]
    review_feedback: NotRequired[str]
    retry_count: NotRequired[int]
    llm_priority: NotRequired[str]


# ═══════════════════════════════════════
#  Leader — 路径大纲规划
# ═══════════════════════════════════════

async def leader_node(state: PathState) -> dict:
    """分析画像 + 学科 → 产出 topic_outline"""
    t0 = time.perf_counter()
    prompt_text = fill_prompt(
        load_prompt("path/leader"),
        subject=state["subject"],
        difficulty=state.get("difficulty", "medium"),
        node_count=str(state.get("node_count", 0)),
        portrait_context=state.get("portrait_context", "暂无画像数据"),
        mastery_context=state.get("mastery_context", "暂无掌握度数据"),
        kb_context=state.get("kb_context", "暂无相关知识库"),
        learning_guidance=state.get("learning_guidance", ""),
    )

    user_id_int = int(state.get("user_id", 0))
    llm_priority = state.get("llm_priority", "high")

    try:
        response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="path")
        result = parse_llm_json(response.content)
        if not isinstance(result, dict):
            result = {}
    except Exception:
        logger.exception("[PathLeader] LLM 调用失败")
        return {}

    topic_outline = result.get("topic_outline", [])
    node_count = result.get("node_count", len(topic_outline))
    difficulty = result.get("difficulty", state.get("difficulty", "medium"))

    logger.info(f"[PathLeader] 规划完成 node_count={node_count} 耗时={time.perf_counter() - t0:.1f}s")
    return {
        "topic_outline": topic_outline,
        "node_count": node_count,
        "difficulty": difficulty,
    }


# ═══════════════════════════════════════
#  Executor — 并行分组生成节点详情
# ═══════════════════════════════════════

async def executor_node(state: PathState) -> dict:
    """将 topic_outline 分组，并行调用 LLM 生成每组的节点详情"""
    t0 = time.perf_counter()
    topic_outline = state.get("topic_outline", [])
    if not topic_outline:
        logger.warning("[PathExecutor] topic_outline 为空")
        return {"nodes": []}

    subject = state["subject"]
    difficulty = state.get("difficulty", "medium")
    portrait_context = state.get("portrait_context", "")
    feedback = state.get("review_feedback", "")
    total_nodes = len(topic_outline)
    user_id_int = int(state.get("user_id", 0))
    llm_priority = state.get("llm_priority", "high")

    # 将 topic_outline 分成每组最多 _GROUP_SIZE 个
    groups: list[list[dict]] = []
    for i in range(0, total_nodes, _GROUP_SIZE):
        groups.append(topic_outline[i:i + _GROUP_SIZE])

    async def generate_group(group_idx: int, group: list[dict]) -> list[dict]:
        """为某一组节点生成详细信息"""
        group_start = group_idx * _GROUP_SIZE + 1
        group_end = group_start + len(group) - 1
        group_topics = json.dumps(
            [{"order_index": group_start + j, "topic": n["topic"], "cognitive_level": n.get("cognitive_level", "理解")}
             for j, n in enumerate(group)],
            ensure_ascii=False,
        )
        outline_json = json.dumps(topic_outline, ensure_ascii=False)

        prompt_text = fill_prompt(
            load_prompt("path/executor"),
            subject=subject,
            difficulty=difficulty,
            group_start=str(group_start),
            group_end=str(group_end),
            total_nodes=str(total_nodes),
            topic_outline=outline_json,
            group_topics=group_topics,
            portrait_context=portrait_context,
            feedback=feedback,
        )

        try:
            response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="path")
            nodes = parse_llm_json(response.content)
            if isinstance(nodes, list):
                logger.info(f"[PathExecutor] 组{group_idx+1} 生成 {len(nodes)} 个节点")
                return nodes
            logger.warning(f"[PathExecutor] 组{group_idx+1} 返回非列表: {type(nodes)}")
            return []
        except Exception:
            logger.exception(f"[PathExecutor] 组{group_idx+1} 生成失败")
            return []

    # 并行执行所有分组
    results = await asyncio.gather(*[
        generate_group(i, g) for i, g in enumerate(groups)
    ])

    # 合并所有节点，按 order_index 排序
    all_nodes: list[dict] = []
    for group_nodes in results:
        all_nodes.extend(group_nodes)
    all_nodes.sort(key=lambda n: n.get("order_index", 0))

    logger.info(f"[PathExecutor] 全部节点生成完成 total={len(all_nodes)} 耗时={time.perf_counter() - t0:.1f}s")
    return {"nodes": all_nodes}


# ═══════════════════════════════════════
#  Reviewer — 路径质量审核
# ═══════════════════════════════════════

async def reviewer_node(state: PathState) -> dict:
    """审核完整路径的连贯性、前置依赖、知识点覆盖"""
    t0 = time.perf_counter()
    nodes = state.get("nodes", [])
    if not nodes:
        return {"review_passed": True, "review_feedback": ""}

    subject = state["subject"]
    difficulty = state.get("difficulty", "medium")
    user_id_int = int(state.get("user_id", 0))
    llm_priority = state.get("llm_priority", "high")
    nodes_json = json.dumps(nodes, ensure_ascii=False)

    prompt_text = fill_prompt(
        load_prompt("path/reviewer"),
        subject=subject,
        difficulty=difficulty,
        nodes_json=nodes_json,
    )

    try:
        response = await llm.ainvoke(prompt_text, priority=llm_priority, user_id=user_id_int, pool="path")
        result = parse_llm_json(response.content)
        if not isinstance(result, dict):
            result = {}
    except Exception:
        logger.exception("[PathReviewer] LLM 调用失败")
        return {"review_passed": True, "review_feedback": ""}

    passed = result.get("passed", False)
    if isinstance(passed, str):
        passed = passed.lower() in ("true", "yes", "1", "是", "pass")
    score = result.get("score", 0)
    feedback = result.get("feedback", "")
    issues = result.get("issues", [])

    logger.info(f"[PathReviewer] passed={passed} score={score} issues={len(issues)} 耗时={time.perf_counter() - t0:.1f}s")
    return {
        "review_passed": passed,
        "review_feedback": feedback if not passed else "",
    }


# ═══════════════════════════════════════
#  Router
# ═══════════════════════════════════════

def should_continue(state: PathState) -> str:
    if state.get("review_passed"):
        return "end"
    if state.get("retry_count", 0) >= 2:
        logger.info("[PathGraph] 已达最大重试次数，强制结束")
        return "end"
    return "executor"


# ═══════════════════════════════════════
#  Graph
# ═══════════════════════════════════════

def build_path_graph():
    workflow = StateGraph(PathState)

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


path_graph = build_path_graph()

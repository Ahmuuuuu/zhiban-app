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


_COGNITIVE_LEVELS = ["记忆", "理解", "应用", "分析", "评价", "创造"]


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_topic_outline(raw, subject: str, node_count: int = 0) -> list[dict]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic") or item.get("title") or "").strip()
        if not topic or topic in seen:
            continue
        seen.add(topic)
        level = str(item.get("cognitive_level") or _COGNITIVE_LEVELS[min(index - 1, len(_COGNITIVE_LEVELS) - 1)])
        normalized.append({
            "topic": topic,
            "module": str(item.get("module") or item.get("category") or subject).strip(),
            "cognitive_level": level,
            "learning_goal": str(item.get("learning_goal") or f"理解并掌握{topic}").strip(),
            "prerequisite_topics": item.get("prerequisite_topics") if isinstance(item.get("prerequisite_topics"), list) else [],
            "key_points": item.get("key_points") if isinstance(item.get("key_points"), list) else [topic],
            "micro_example": str(item.get("micro_example") or f"完成一个关于{topic}的小练习").strip(),
        })
        if node_count and len(normalized) >= node_count:
            break
    return normalized


def _fallback_topic_outline(subject: str, node_count: int = 0) -> list[dict]:
    target = max(8, min(18, _safe_int(node_count, 12) or 12))
    templates = [
        ("学习目标与知识地图", "概念奠基"),
        ("核心概念与基本术语", "概念奠基"),
        ("基础结构与表示方法", "概念奠基"),
        ("基本规则与操作流程", "方法操作"),
        ("典型方法一：基础应用", "方法操作"),
        ("典型方法二：组合应用", "方法操作"),
        ("关键例题与解题步骤", "案例应用"),
        ("常见错误与辨析", "误区辨析"),
        ("小型综合任务", "综合迁移"),
        ("阶段复盘与知识迁移", "综合迁移"),
        ("进阶应用场景", "案例应用"),
        ("最终综合练习", "综合迁移"),
    ]
    outline = []
    for index in range(target):
        name, module = templates[index % len(templates)]
        topic = f"{subject}：{name}"
        outline.append({
            "topic": topic,
            "module": module,
            "cognitive_level": _COGNITIVE_LEVELS[min(index, len(_COGNITIVE_LEVELS) - 1)],
            "learning_goal": f"围绕「{subject}」掌握{name}，并能完成对应检查任务",
            "prerequisite_topics": [outline[-1]["topic"]] if outline else [],
            "key_points": [subject, name, module],
            "micro_example": f"用一个小例子检查「{name}」是否掌握",
        })
    return outline


async def parse_or_repair_leader_result(raw_text: str, state: dict, *, retry_llm: bool = True) -> dict:
    """Parse Path Leader JSON; repair once, then fall back to a stable outline."""
    subject = str(state.get("subject") or "通用学习")
    requested_count = _safe_int(state.get("node_count"), 0)
    difficulty = str(state.get("difficulty") or "medium")
    user_id_int = _safe_int(state.get("user_id"), 0)
    llm_priority = state.get("llm_priority", "high")

    try:
        result = parse_llm_json(raw_text)
        if not isinstance(result, dict):
            result = {}
    except Exception as parse_error:
        logger.warning("[PathLeader] JSON 解析失败，尝试修复: %s", parse_error)
        result = {}
        if retry_llm:
            repair_prompt = (
                "你是 JSON 修复器。请只修复下面内容为合法 JSON，不要新增解释文字，不要使用 markdown。\n"
                "要求：第一个字符必须是 {，最后一个字符必须是 }；保留原有 topic_outline 结构；无法确定的字段用合理短文本补齐。\n\n"
                f"原始内容：\n{str(raw_text or '')[:6000]}"
            )
            try:
                repaired = await llm.ainvoke(repair_prompt, priority=llm_priority, user_id=user_id_int, pool="path")
                parsed = parse_llm_json(repaired.content)
                if isinstance(parsed, dict):
                    result = parsed
            except Exception:
                logger.exception("[PathLeader] JSON 修复失败，使用本地兜底大纲")

    topic_outline = _normalize_topic_outline(result.get("topic_outline"), subject, requested_count)
    if not topic_outline:
        logger.warning("[PathLeader] topic_outline 为空，使用本地兜底大纲 subject=%s", subject)
        topic_outline = _fallback_topic_outline(subject, requested_count)

    node_count = _safe_int(result.get("node_count"), len(topic_outline)) or len(topic_outline)
    node_count = max(1, min(node_count, len(topic_outline)))
    return {
        "topic_outline": topic_outline[:node_count],
        "node_count": node_count,
        "difficulty": str(result.get("difficulty") or difficulty),
    }


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
        result = await parse_or_repair_leader_result(response.content, state)
    except Exception:
        logger.exception("[PathLeader] LLM 调用失败")
        result = await parse_or_repair_leader_result("", state, retry_llm=False)

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
            [
                {
                    **n,
                    "order_index": group_start + j,
                    "topic": n["topic"],
                    "cognitive_level": n.get("cognitive_level", "理解"),
                }
                for j, n in enumerate(group)
            ],
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

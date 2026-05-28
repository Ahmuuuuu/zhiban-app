"""
LangGraph 多智能体编排 — 学习资源生成
LeaderAgent → [ExecutorAgent × N 多线程并行] → ReviewerAgent
"""
import asyncio
import json
import logging
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


# ═══════════════════════════════════════
#  Nodes
# ═══════════════════════════════════════

async def leader_node(state: ResourceState) -> dict:
    """LeaderAgent: 分析需求，决定生成哪些资源类型"""
    topic = state["topic"]
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    guidance = state.get("learning_guidance", "")
    prompt_text = fill_prompt(load_prompt("agent/leader"), topic=topic, portrait_context=portrait, kb_context=kb, learning_guidance=guidance)

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
    """多 Executor 并行生成 — 线程池 + 信号量限流。
    image 类型走两阶段：LLM 生成 prompt → ImageService.generate() 生图。
    """
    topic = state["topic"]
    resource_types = state.get("resource_types", ["document"])
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    guidance = state.get("learning_guidance", "")
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
            learning_guidance=guidance,
            feedback=feedback,
            count=state.get("exam_count", "5"),
            question_types=state.get("exam_question_types", "single_choice, multi_choice, true_false"),
            difficulty=state.get("exam_difficulty", "medium"),
        )

    # 信号量限制最大并发数，防止 DeepSeek 限流
    semaphore = asyncio.Semaphore(5)

    async def gen_one(rt: str, user_id: str) -> tuple[str, str]:
        async with semaphore:
            try:
                # ppt 类型：rich query → 讯飞智文 API
                if rt == "ppt":
                    return await _generate_ppt(topic, portrait, guidance, user_id)
                # image 类型：两阶段生成
                if rt == "image":
                    return await _generate_image(prompts[rt], user_id)
                # 其他类型：单次 LLM 调用
                response = await llm.ainvoke(prompts[rt])
                return rt, response.content
            except Exception as e:
                logger.exception(f"Executor [{rt}] 调用失败")
                return rt, f"[生成失败: {e}]"

    user_id = state.get("user_id", "0")
    results = await asyncio.gather(*(gen_one(rt, user_id) for rt in resource_types))

    retry = state.get("retry_count", 0)
    if feedback:
        retry += 1

    # 分离普通资源和 file_urls
    generated = {}
    file_urls = {}
    for rt, content in results:
        if rt.startswith("image:"):
            # image 类型返回特殊 key，解析 file_url
            actual_rt = rt.replace("image:", "")
            generated[actual_rt] = content.get("prompt", "")
            if content.get("url"):
                file_urls[actual_rt] = content["url"]
        elif rt.startswith("ppt:"):
            # ppt:api 类型：content 是本地文件路径
            actual_rt = rt.replace("ppt:", "")
            generated[actual_rt] = f"PPT 已通过讯飞智文生成：{topic}"
            if content and isinstance(content, str) and content.endswith(".pptx"):
                file_urls[actual_rt] = content
        else:
            generated[rt] = content

    return {
        "generated_resources": generated,
        "file_urls": file_urls,
        "retry_count": retry,
        "review_feedback": "",
    }


async def _generate_image(prompt_text: str, user_id: str) -> tuple[str, dict]:
    """两阶段图片生成：LLM 产出 prompt → ImageService 生图"""
    # Phase 1: LLM 生成图像描述
    from backend.src.ai_core.llm_config import llm
    try:
        response = await llm.ainvoke(prompt_text)
        image_prompt = response.content.strip()
    except Exception as e:
        logger.exception("图片 prompt 生成失败")
        return ("image:error", {"prompt": "", "url": ""})

    # Phase 2: 调 ImageService 生图（阻塞轮询，不阻塞事件循环）
    try:
        from backend.src.service.image_service import ImageService
        images = await ImageService.generate(image_prompt, user_id, aspect_ratio="16:9", img_count=1)
        if images and len(images) > 0:
            return ("image:image", {"prompt": image_prompt, "url": images[0].get("url", "")})
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")

    return ("image:image", {"prompt": image_prompt, "url": ""})


async def _generate_ppt(topic: str, portrait: str, guidance: str, user_id: str) -> tuple[str, str]:
    """PPT 生成：rich query → 讯飞智文 API → PPTX，失败降级为 LLM + python-pptx"""
    # 构造 rich query
    query_parts = [f"请生成一份关于「{topic}」的详细 PPT。"]
    if portrait and "暂无" not in portrait:
        query_parts.append(f"目标受众：{portrait[:300]}")
    if guidance:
        query_parts.append(f"教学要求：{guidance[:300]}")
    query_parts.append(
        "要求：内容丰富、每页要点充足，适合课堂教学。"
        "请自动配图，包含架构图、流程图等 visual 元素。"
        "生成至少 10 页以上。"
    )
    query = "\n".join(query_parts)

    # Phase 1: 调讯飞智文 API
    try:
        from backend.src.service.ppt_service import PptService
        local_path = await PptService.generate(query, is_figure=True)
        logger.info(f"PPT 讯飞生成完成: {local_path}")
        return ("ppt:api", local_path)
    except Exception as e:
        logger.warning(f"讯飞智文 API 调用失败，降级为 LLM + python-pptx: {e}")
        # Phase 2: 降级 — LLM 生成 markdown + python-pptx
        try:
            prompt_path = PROMPT_MAP.get("ppt", "resource/ppt")
            template = load_prompt(prompt_path)
            fallback_prompt = fill_prompt(
                template, topic=topic, resource_type="ppt",
                portrait_context=portrait, kb_context="",
                learning_guidance=guidance, feedback="",
            )
            response = await llm.ainvoke(fallback_prompt)
            return ("ppt", response.content)
        except Exception as e2:
            logger.exception(f"PPT 降级生成也失败")
            return ("ppt", f"[生成失败: {e2}]")


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
        # API 生成的 PPT/图片跳过文本审核
        file_urls = state.get("file_urls", {})
        if file_urls.get(rt):
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

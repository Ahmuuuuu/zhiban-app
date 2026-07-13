"""Context assembly for resource generation."""

from __future__ import annotations

import asyncio
import logging
import time

from backend.src.ai_core.llm_config import llm
from backend.src.models.agent_skill_model import AgentSkill
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.service.portrait.service import format_portrait
from backend.src.service.resource.metadata import normalize_ppt_theme_id
from backend.src.utils.chat_utils import allocate_chat_group_id
from backend.src.utils.knowledge_base import search as kb_search
from backend.src.utils.prompt_loader import fill_prompt, load_prompt

logger = logging.getLogger(__name__)


def infer_rag_mode(answers: dict | None = None, user_notes: str = "") -> str:
    answers = answers or {}
    raw_mode = str(answers.get("rag_mode") or answers.get("knowledge_mode") or "").strip().lower()
    if raw_mode in {"strict", "source_only", "knowledge_only"}:
        return "strict"
    if raw_mode in {"reference", "assist", "auto"}:
        return "reference"

    note = str(user_notes or "")
    strict_markers = ("只根据", "仅根据", "不要扩展", "不扩展", "严格按照资料", "只用上传资料", "按这份资料")
    if any(marker in note for marker in strict_markers):
        return "strict"
    return "reference"


async def extract_topic_from_chat(user_id: int, chat_group_id: int) -> str:
    """Extract a learning topic from a chat group."""
    records = await ChatHistory.filter(
        user__id=user_id,
        chat_group_id=chat_group_id,
    ).order_by("created_at").all()

    if not records:
        return "通用学习"

    conversation = "\n".join(
        f"用户：{record.req}\nAI：{record.res[:200]}" for record in records
    )
    prompt = fill_prompt(load_prompt("resource/topic_extract"), conversation=conversation)
    response = await llm.ainvoke(prompt)
    return response.content.strip()


async def ensure_chat_group_id(user_id: int, chat_group_id: int = 0) -> int:
    """Return a valid chat_group_id; zero means no chat binding."""
    return chat_group_id if chat_group_id and chat_group_id > 0 else 0


async def ensure_generation_chat_group_id(
    user_id: int,
    chat_group_id: int = 0,
    bind_chat_history: bool = False,
) -> int:
    if chat_group_id and chat_group_id > 0:
        return chat_group_id
    if bind_chat_history:
        return await allocate_chat_group_id(user_id)
    return 0


async def make_generation_state(
    topic: str,
    user_id: int,
    resource_types: list[str],
    chat_group_id: int = 0,
    exam_question_types: str = "single_choice, multi_choice, true_false",
    exam_count: int = 5,
    exam_difficulty: str = "medium",
    answers: dict | None = None,
    skip_review: bool = False,
    user_notes: str = "",
    ppt_prompt_key: str = "ppt",
    llm_priority: str = "high",
    ppt_theme_id: str | None = None,
) -> dict:
    t0 = time.perf_counter()
    rag_mode = infer_rag_mode(answers, user_notes)
    chat_group_id = await ensure_chat_group_id(user_id, chat_group_id)
    t_init = time.perf_counter()

    if not topic and chat_group_id > 0:
        topic = await extract_topic_from_chat(user_id, chat_group_id)

    from backend.src.service.portrait.service import PortraitRadarService, build_learning_guidance

    portrait_context = "暂无画像数据"
    learning_guidance = ""

    user_task = User.filter(id=user_id).first()
    guidance_task = build_learning_guidance(user_id)
    kb_task = kb_search(topic, top_k=3, user_id=user_id)
    skills_task = AgentSkill.filter(user_id=user_id, enabled=True).all()

    user, learning_guidance, kb_result, skills = await asyncio.gather(
        user_task, guidance_task, kb_task, skills_task, return_exceptions=True
    )
    t_gather = time.perf_counter()

    if isinstance(learning_guidance, Exception):
        logger.exception("学习指导生成失败 user_id=%s", user_id)
        learning_guidance = ""

    if isinstance(kb_result, Exception):
        logger.exception("知识库搜索失败 topic=%s", topic)
        kb_result = "暂无相关知识库资料"

    if isinstance(skills, Exception):
        logger.exception("Skills 查询失败 user_id=%s", user_id)
        skills = []

    base_portrait_parts = []
    if user and not isinstance(user, Exception):
        if user.major:
            base_portrait_parts.append(f"专业：{user.major}")
        if user.grade:
            base_portrait_parts.append(f"年级：{user.grade}")

    if user and not isinstance(user, Exception):
        picture = await user.picture
        if picture:
            try:
                radar_data = await PortraitRadarService.get(user_id)
            except Exception:
                radar_data = None
            portrait_context = "\n".join(
                format_portrait(picture, show_missing=False, radar_data=radar_data)
            )
        elif base_portrait_parts:
            portrait_context = "【用户画像】\n" + "；".join(base_portrait_parts)
    elif base_portrait_parts:
        portrait_context = "【用户画像】\n" + "；".join(base_portrait_parts)
    t_portrait = time.perf_counter()

    kb_context = "暂无相关知识库资料"
    if kb_result and not isinstance(kb_result, Exception) and "暂无" not in str(kb_result):
        kb_context = kb_result

    custom_prompts = {}
    for skill in skills:
        if skill.resource_type in resource_types and skill.system_prompt:
            custom_prompts[skill.resource_type] = skill.system_prompt

    t_total = time.perf_counter() - t0
    logger.info(
        "make_generation_state total=%.2fs chat=%.2fs gather=%.2fs portrait=%.2fs topic=%s types=%s",
        t_total,
        t_init - t0,
        t_gather - t_init,
        t_portrait - t_gather,
        topic,
        resource_types,
    )

    return {
        "user_id": str(user_id),
        "topic": topic,
        "resource_types": resource_types,
        "chat_group_id": chat_group_id,
        "portrait_context": portrait_context,
        "kb_context": kb_context,
        "learning_guidance": learning_guidance,
        "custom_prompts": custom_prompts,
        "generated_resources": {},
        "review_feedback": "",
        "review_passed": False,
        "retry_count": 0,
        "exam_question_types": exam_question_types,
        "exam_count": str(exam_count),
        "exam_difficulty": exam_difficulty,
        "answers": answers or {},
        "rag_mode": rag_mode,
        "skip_review": skip_review,
        "user_notes": user_notes,
        "ppt_prompt_key": ppt_prompt_key,
        "llm_priority": llm_priority,
        "ppt_theme_id": normalize_ppt_theme_id(ppt_theme_id),
    }

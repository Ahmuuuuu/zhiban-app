"""通知生成服务 — 学习提醒、周报、AI 建议"""

import json
import logging
from datetime import date, datetime, timedelta

from backend.src.models.notification_model import Notification
from backend.src.models.study_model import StudySession, ResourceReadStatus
from backend.src.models.exam_model import KnowledgeMastery, ExamRecord
from backend.src.models.path_model import UserPathProgress
from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#  学习提醒 — 由业务流触发
# ═══════════════════════════════════════════════

async def check_and_create_node_unlocked(user_id: int, node_topic: str, path_id: int, node_id: int):
    """节点解锁时提醒"""
    await Notification.create(
        type="reminder",
        title="新节点已解锁",
        content=f"「{node_topic}」已解锁，快去学习吧",
        target_url=f"/learning-path?path_id={path_id}&node_id={node_id}",
        target_user_id=user_id,
    )


async def check_and_create_quiz_failed(user_id: int, node_topic: str, path_id: int, node_id: int):
    """测验未通过时提醒"""
    await Notification.create(
        type="reminder",
        title="测验未通过",
        content=f"「{node_topic}」测验未通过，建议重新挑战",
        target_url=f"/learning-path?path_id={path_id}&node_id={node_id}",
        target_user_id=user_id,
    )


async def check_and_create_weekly_report(user_id: int):
    """每周一生成上周学习报告，仅当用户有过学习活动"""
    today = date.today()
    if today.weekday() != 0:
        return

    week_start = today - timedelta(days=7)
    week_end = today - timedelta(days=1)

    # 检查本周是否已生成过
    existing = await Notification.filter(
        target_user_id=user_id,
        type="weekly_report",
        created_at__gte=week_start,
    ).exists()
    if existing:
        return

    # 上周学习时长
    sessions = await StudySession.filter(
        user_id=user_id,
        date__gte=week_start,
        date__lte=week_end,
    ).all()
    week_seconds = sum(s.total_seconds for s in sessions)
    if week_seconds == 0:
        return

    hours = round(week_seconds / 3600, 1)

    # 上周答题
    exam_records = await ExamRecord.filter(
        user_id=user_id,
        is_correct__not_isnull=True,
        created_at__gte=week_start,
        created_at__lt=today,
    ).all()
    quiz_count = len(exam_records)
    correct_count = sum(1 for r in exam_records if r.is_correct)
    accuracy = round(correct_count / max(quiz_count, 1) * 100, 1)

    # 上周浏览资源数
    resource_count = await ResourceReadStatus.filter(
        user_id=user_id,
        read_at__gte=week_start,
        read_at__lt=today,
    ).count()

    await Notification.create(
        type="weekly_report",
        title="上周学习报告",
        content=f"上周学习 {hours} 小时，完成 {quiz_count} 道题（正确率 {accuracy}%），浏览 {resource_count} 份资源",
        target_url="/study-stats",
        target_user_id=user_id,
    )


# ═══════════════════════════════════════════════
#  定时任务入口 — 由 scheduler 每周一触发
# ═══════════════════════════════════════════════

async def generate_weekly_report_and_ai_tip():
    """遍历所有用户，生成周报 + LLM AI 建议"""
    from backend.src.models.usermodel import User

    users = await User.filter().all()
    total = 0
    for user in users:
        try:
            await check_and_create_weekly_report(user.id)
            tip = await _build_ai_tip(user.id)
            if tip:
                await Notification.create(
                    type="ai_tip",
                    title="AI 学习建议",
                    content=tip,
                    target_url="/learning-report",
                    target_user_id=user.id,
                )
                total += 1
        except Exception:
            logger.exception("周报/AI建议生成失败 user=%s", user.id)

    logger.info("周报+AI建议已生成，%d 名用户收到 AI 建议", total)


# ═══════════════════════════════════════════════
#  AI 建议 — LLM 生成
# ═══════════════════════════════════════════════

async def _build_ai_tip(user_id: int) -> str | None:
    """读取画像 + 薄弱知识点 + 错题标签 → LLM 生成个性化建议"""

    portrait_context = await _read_portrait(user_id)
    weak_points = await _get_weak_tags(user_id)
    error_tags = await _get_recent_error_tags(user_id)

    if not weak_points and not error_tags:
        return None

    prompt = fill_prompt(
        load_prompt("notification/ai_tip"),
        portrait_context=portrait_context or "暂无画像",
        weak_points="、".join(weak_points) if weak_points else "暂无",
        error_tags="、".join(error_tags) if error_tags else "暂无",
    )

    try:
        resp = await llm.ainvoke(prompt)
        tip = resp.content.strip()
        return tip[:250] if tip else None
    except Exception:
        logger.exception("AI 建议 LLM 调用失败 user=%s", user_id)
        return None


async def check_and_create_ai_tip(user_id: int):
    """答题后即时检查薄弱知识点，生成简短 AI 建议（非 LLM）"""
    weak_tags = await KnowledgeMastery.filter(
        user_id=user_id,
        mastery_level="beginner",
    ).limit(3).values_list("knowledge_tag", flat=True)

    if not weak_tags:
        return

    tags_str = "、".join(weak_tags)
    await Notification.create(
        type="ai_tip",
        title="学习建议",
        content=f"你在 {tags_str} 上比较薄弱，建议针对性地复习相关知识点",
        target_url="/study-stats",
        target_user_id=user_id,
    )


async def _read_portrait(user_id: int) -> str:
    """读取用户画像摘要"""
    from backend.src.models.usermodel import User
    from backend.src.service.portrait_service import PortraitChatHistory_Service

    user = await User.filter(id=user_id).first()
    if not user:
        return ""

    portrait, _ = await PortraitChatHistory_Service.read_portrait(user_id)
    traits = portrait.get("traits", {}) if portrait else {}

    parts = []
    if user.major:
        parts.append(f"专业：{user.major}")
    if user.grade:
        parts.append(f"年级：{user.grade}")
    for key, label in [
        ("strengths", "强项"), ("weaknesses", "弱项"),
        ("knowbase", "知识基础"), ("learning_pace", "学习节奏"),
    ]:
        val = traits.get(key)
        if val and isinstance(val, dict) and val.get("value"):
            parts.append(f"{label}：{val['value']}")

    return "；".join(parts) if parts else ""


async def _get_weak_tags(user_id: int) -> list[str]:
    """薄弱知识点（beginner + learning 级别，最多 5 个）"""
    records = await KnowledgeMastery.filter(
        user_id=user_id,
        mastery_level__in=["beginner", "learning"],
    ).limit(5).all()
    return [r.knowledge_tag for r in records if r.knowledge_tag]


async def _get_recent_error_tags(user_id: int) -> list[str]:
    """最近一周错题涉及的知识点标签"""
    one_week_ago = datetime.now() - timedelta(days=7)
    records = await ExamRecord.filter(
        user_id=user_id,
        is_correct=False,
        created_at__gte=one_week_ago,
    ).limit(10).all()

    tags: set[str] = set()
    for r in records:
        kt = r.knowledge_tags or ""
        if isinstance(kt, str):
            try:
                tag_list = json.loads(kt)
            except json.JSONDecodeError:
                tag_list = [kt] if kt else []
        else:
            tag_list = kt
        if isinstance(tag_list, list):
            tags.update(t for t in tag_list if isinstance(t, str))
    return list(tags)[:8]

"""通知生成服务 — 由业务流触发，创建不同类型通知"""

from datetime import date, datetime, timedelta, timezone

from backend.src.models.notification_model import Notification
from backend.src.models.study_model import StudySession
from backend.src.models.exam_model import KnowledgeMastery, ExamRecord
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.path_model import UserPathProgress


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


async def check_and_create_ai_tip(user_id: int):
    """答题后检查薄弱知识点，生成 AI 建议"""
    weak_tags = await KnowledgeMastery.filter(
        user_id=user_id,
        mastery_level="beginner",
    ).limit(3).values_list("knowledge_tag", flat=True)

    if not weak_tags:
        return

    tags_str = "、".join(weak_tags)
    await Notification.create(
        type="system",
        title="学习建议",
        content=f"你在 {tags_str} 上比较薄弱，建议针对性地复习相关知识点",
        target_url="/study-stats",
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
    from backend.src.models.study_model import ResourceReadStatus
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

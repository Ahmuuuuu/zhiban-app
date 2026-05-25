"""学习统计服务 — 心跳、汇总、资源已读"""

import logging
from datetime import date, datetime, timedelta

from backend.src.models.study_model import StudySession, ResourceReadStatus
from backend.src.models.usermodel import User
from backend.src.models.exam_model import KnowledgeMastery, ExamRecord
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.path_model import LearningPath, UserPathProgress

logger = logging.getLogger(__name__)


class StudyService:

    @staticmethod
    async def heartbeat(user_id: int) -> dict:
        """前端每 30 秒调用一次，累计今日学习时长"""
        today = date.today()
        session, _ = await StudySession.get_or_create(
            user_id=user_id, date=today,
            defaults={"total_seconds": 0, "last_heartbeat_at": datetime.now()},
        )
        session.total_seconds += 30
        session.last_heartbeat_at = datetime.now()
        await session.save()
        return {"today_seconds": session.total_seconds}

    @staticmethod
    async def mark_read(user_id: int, resource_id: int) -> dict:
        """标记资源为已读"""
        status, created = await ResourceReadStatus.get_or_create(
            user_id=user_id, resource_id=resource_id,
            defaults={"is_read": True, "read_at": datetime.now()},
        )
        if not created and not status.is_read:
            status.is_read = True
            status.read_at = datetime.now()
            await status.save()
        return {"resource_id": resource_id, "is_read": True}

    @staticmethod
    async def mark_unread(user_id: int, resource_id: int) -> dict:
        """标记资源为未读"""
        status = await ResourceReadStatus.filter(user_id=user_id, resource_id=resource_id).first()
        if status:
            status.is_read = False
            status.read_at = None
            await status.save()
        return {"resource_id": resource_id, "is_read": False}

    @staticmethod
    async def get_stats(user_id: int) -> dict:
        """聚合学习统计"""

        # ── 学习时长 ──
        today = date.today()
        week_ago = today - timedelta(days=6)

        sessions = await StudySession.filter(user_id=user_id, date__gte=week_ago).all()
        today_session = next((s for s in sessions if s.date == today), None)
        today_seconds = today_session.total_seconds if today_session else 0
        week_seconds = sum(s.total_seconds for s in sessions)
        active_days = len({s.date for s in sessions if s.total_seconds > 0})

        all_sessions = await StudySession.filter(user_id=user_id).all()
        total_seconds = sum(s.total_seconds for s in all_sessions)

        # ── 薄弱点 ──
        mastery_records = await KnowledgeMastery.filter(user_id=user_id).order_by("-last_practiced_at").all()
        weak_points = [
            {
                "tag": r.knowledge_tag,
                "accuracy": round(r.correct_count / max(r.total_attempts, 1), 2),
                "level": r.mastery_level,
                "total_attempts": r.total_attempts,
            }
            for r in mastery_records
            if r.mastery_level in ("beginner", "learning")
        ]

        # ── 学习路径 ──
        paths = []
        path_records = await LearningPath.filter().prefetch_related("nodes").all()
        for p in path_records:
            progress_records = await UserPathProgress.filter(path_id=p.id, user_id=user_id).all()
            total_nodes = len(p.nodes) if p.nodes else 0
            completed_nodes = sum(1 for r in progress_records if r.node_status == "completed")
            current = None
            for r in progress_records:
                if r.node_status in ("unlocked", "in_progress"):
                    node = next((n for n in (p.nodes or []) if n.id == r.node_id), None)
                    current = node.title if node else None
                    break
            paths.append({
                "path_id": p.id,
                "goal": p.goal or p.subject or "",
                "progress": round(completed_nodes / max(total_nodes, 1), 2),
                "total_nodes": total_nodes,
                "completed_nodes": completed_nodes,
                "current_node": current,
            })

        # ── 资源已读 ──
        resources = await GeneratedResource.filter(user_id=user_id).all()
        read_statuses = await ResourceReadStatus.filter(user_id=user_id,
            resource_id__in=[r.id for r in resources]).all()
        read_map = {rs.resource_id: rs.is_read for rs in read_statuses}

        by_type: dict[str, dict] = {}
        total_read = 0
        for r in resources:
            rt = r.resource_type or "other"
            if rt not in by_type:
                by_type[rt] = {"total": 0, "read": 0}
            by_type[rt]["total"] += 1
            if read_map.get(r.id):
                by_type[rt]["read"] += 1
                total_read += 1

        # ── 答题汇总 ──
        exam_records = await ExamRecord.filter(user_id=user_id, is_correct__not_isnull=True).all()
        total_questions = len(exam_records)
        correct_count = sum(1 for r in exam_records if r.is_correct)
        session_ids = {r.session_id for r in exam_records}

        return {
            "study_time": {
                "today_seconds": today_seconds,
                "week_seconds": week_seconds,
                "total_seconds": total_seconds,
                "active_days": active_days,
            },
            "weak_points": weak_points,
            "learning_paths": paths,
            "resources": {
                "total": len(resources),
                "read_count": total_read,
                "unread_count": len(resources) - total_read,
                "by_type": by_type,
            },
            "exam_summary": {
                "total_questions": total_questions,
                "correct_rate": round(correct_count / max(total_questions, 1), 2),
                "total_sessions": len(session_ids),
            },
        }

"""学习统计服务 — 心跳、汇总、资源已读"""

import logging
from datetime import date, datetime, timedelta

from backend.src.models.study_model import StudySession, ResourceReadStatus, ResourceCollection
from backend.src.models.exam_model import KnowledgeMastery, ExamRecord
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.path_model import LearningPath, UserPathProgress
from backend.src.service.portrait_service import build_learning_guidance, PortraitRadarService

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
        resource = await GeneratedResource.filter(id=resource_id).first()
        if not resource:
            raise ValueError("资源不存在")
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
        resource = await GeneratedResource.filter(id=resource_id).first()
        if not resource:
            raise ValueError("资源不存在")
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

        # ── 薄弱点（知识点 + 雷达维度） ──
        mastery_records = await KnowledgeMastery.filter(user_id=user_id).order_by("-last_practiced_at").all()
        weak_points = [
            {
                "tag": r.knowledge_tag,
                "accuracy": round(r.correct_count / max(r.total_attempts, 1), 2),
                "level": r.mastery_level,
                "total_attempts": r.total_attempts,
                "source": "mastery",
            }
            for r in mastery_records
            if r.mastery_level in ("beginner", "learning")
        ]
        # 追加雷达弱项维度
        try:
            radar = await PortraitRadarService.get(user_id)
            if radar and radar.get("dimensions"):
                labels = {"memory": "记忆(简单题)", "understanding": "理解(中等题)", "application": "应用(困难题)",
                          "analysis": "分析(多选题)", "breadth": "广度(知识覆盖)", "persistence": "坚持(活跃度)"}
                for d in radar["dimensions"]:
                    if d["score"] < 50:
                        weak_points.append({
                            "tag": labels.get(d["key"], d["key"]),
                            "accuracy": round(d["score"] / 100, 2),
                            "level": "beginner" if d["score"] < 40 else "learning",
                            "total_attempts": 0,
                            "source": "radar",
                        })
        except Exception:
            pass

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
                    current = node.topic if node else None
                    break
            paths.append({
                "path_id": p.id,
                "goal": p.subject or "",
                "progress": round(completed_nodes / max(total_nodes, 1), 2),
                "total_nodes": total_nodes,
                "completed_nodes": completed_nodes,
                "current_node": current,
            })

        # ── 资源已读 + 使用率 ──
        resources = await GeneratedResource.filter(user_id=user_id).all()
        read_statuses = await ResourceReadStatus.filter(user_id=user_id,
            resource_id__in=[r.id for r in resources]).all()
        read_map = {rs.resource_id: rs.is_read for rs in read_statuses}
        collections = await ResourceCollection.filter(user_id=user_id).all()
        collected_ids = {c.resource_id for c in collections}

        by_type: dict[str, dict] = {}
        total_read = 0
        total_views = 0
        total_downloads = 0
        for r in resources:
            rt = r.resource_type or "other"
            if rt not in by_type:
                by_type[rt] = {"total": 0, "read": 0}
            by_type[rt]["total"] += 1
            if read_map.get(r.id):
                by_type[rt]["read"] += 1
                total_read += 1
            total_views += (r.view_count or 0)
            total_downloads += (r.download_count or 0)

        # ── 答题汇总 ──
        exam_records = await ExamRecord.filter(user_id=user_id, is_correct__not_isnull=True).all()
        total_questions = len(exam_records)
        correct_count = sum(1 for r in exam_records if r.is_correct)
        session_ids = {r.session_id for r in exam_records}
        # 练习完成率：judged > 0 的会话视为完成
        session_judged = {}
        for r in exam_records:
            sid = r.session_id
            if sid not in session_judged:
                session_judged[sid] = False
            if r.is_correct is not None:
                session_judged[sid] = True
        completed_sessions = sum(1 for v in session_judged.values() if v)
        total_sessions = len(session_ids)

        # ── 学习指导 ──
        guidance = ""
        try:
            guidance = await build_learning_guidance(user_id)
        except Exception:
            pass

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
                "open_rate": round(total_read / max(len(resources), 1), 2),
                "total_views": total_views,
                "total_downloads": total_downloads,
                "collected_count": len(collections),
                "by_type": by_type,
            },
            "exam_summary": {
                "total_questions": total_questions,
                "correct_rate": round(correct_count / max(total_questions, 1), 2),
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "completion_rate": round(completed_sessions / max(total_sessions, 1), 2),
            },
            "learning_guidance": guidance,
        }

    @staticmethod
    async def get_exam_weekly(user_id: int) -> dict:
        """最近 7 天每日正确率"""
        today = date.today()
        week_ago = today - timedelta(days=6)

        records = await ExamRecord.filter(
            user_id=user_id,
            is_correct__not_isnull=True,
            created_at__gte=week_ago,
        ).all()

        daily_map: dict[str, dict] = {}
        for r in records:
            day = str(r.created_at.date()) if r.created_at else str(today)
            if day not in daily_map:
                daily_map[day] = {"total": 0, "correct": 0}
            daily_map[day]["total"] += 1
            if r.is_correct:
                daily_map[day]["correct"] += 1

        daily = [
            {
                "date": str(week_ago + timedelta(days=i)),
                "total": daily_map.get(str(week_ago + timedelta(days=i)), {}).get("total", 0),
                "correct": daily_map.get(str(week_ago + timedelta(days=i)), {}).get("correct", 0),
                "accuracy": round(
                    daily_map.get(str(week_ago + timedelta(days=i)), {}).get("correct", 0)
                    / max(daily_map.get(str(week_ago + timedelta(days=i)), {}).get("total", 0), 1),
                    2,
                ),
            }
            for i in range(7)
        ]

        week_total = sum(d["total"] for d in daily)
        week_correct = sum(d["correct"] for d in daily)

        return {
            "daily": daily,
            "week_total": week_total,
            "week_correct": week_correct,
            "week_accuracy": round(week_correct / max(week_total, 1), 2),
        }

    @staticmethod
    async def get_learning_guidance(user_id: int) -> dict:
        """返回个性化学习指导文本"""
        guidance = await build_learning_guidance(user_id)
        return {"guidance": guidance}

    @staticmethod
    async def collect_resource(user_id: int, resource_id: int) -> dict:
        """收藏资源（幂等）"""
        resource = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not resource:
            raise ValueError("资源不存在")
        await ResourceCollection.get_or_create(user_id=user_id, resource_id=resource_id)
        return {"resource_id": resource_id, "collected": True}

    @staticmethod
    async def uncollect_resource(user_id: int, resource_id: int) -> dict:
        """取消收藏"""
        resource = await GeneratedResource.filter(id=resource_id).first()
        if not resource:
            raise ValueError("资源不存在")
        await ResourceCollection.filter(user_id=user_id, resource_id=resource_id).delete()
        return {"resource_id": resource_id, "collected": False}

    @staticmethod
    async def list_collections(user_id: int) -> list[dict]:
        """列出已收藏资源"""
        collections = await ResourceCollection.filter(user_id=user_id).prefetch_related("resource").order_by("-created_at").all()
        result = []
        for c in collections:
            r = c.resource
            ext_map = {"document": "md", "ppt": "pptx", "mindmap": "txt", "exercise": "md", "case": "md", "reading": "md", "slide_animation": "json"}
            ext = ext_map.get(r.resource_type, "md")
            result.append({
                "resource_id": r.id,
                "topic": r.topic,
                "resource_type": r.resource_type,
                "filename": f"{r.topic}_{r.resource_type}.{ext}",
                "preview": (r.content or "")[:200],
                "download_url": f"/resource/{r.id}/download",
                "collected_at": str(c.created_at),
            })
        return result

import logging

from backend.src.models.annotation_model import ResourceAnnotation
from backend.src.utils.database import init_db

logger = logging.getLogger(__name__)


class AnnotationService:

    @staticmethod
    async def create(user_id: int, data: dict) -> dict:
        await init_db()
        annotation = await ResourceAnnotation.create(
            user_id=user_id,
            resource_id=data["resource_id"],
            selected_text=data["selected_text"],
            note_text=data["note_text"],
            position=data.get("position"),
        )
        logger.info("笔记已创建 id=%s user_id=%s resource_id=%s", annotation.id, user_id, data["resource_id"])
        return _annotation_to_dict(annotation)

    @staticmethod
    async def update(annotation_id: int, user_id: int, note_text: str) -> dict | None:
        await init_db()
        annotation = await ResourceAnnotation.filter(id=annotation_id, user_id=user_id).first()
        if not annotation:
            return None
        annotation.note_text = note_text
        await annotation.save(update_fields=["note_text", "updated_at"])
        return _annotation_to_dict(annotation)

    @staticmethod
    async def delete(annotation_id: int, user_id: int) -> bool:
        await init_db()
        annotation = await ResourceAnnotation.filter(id=annotation_id, user_id=user_id).first()
        if not annotation:
            return False
        await annotation.delete()
        logger.info("笔记已删除 id=%s user_id=%s", annotation_id, user_id)
        return True

    @staticmethod
    async def list_by_resource(resource_id: int, user_id: int) -> list[dict]:
        await init_db()
        annotations = await ResourceAnnotation.filter(
            resource_id=resource_id, user_id=user_id
        ).order_by("created_at").all()
        return [_annotation_to_dict(a) for a in annotations]

    @staticmethod
    async def collect_notes_for_quiz(user_id: int, resource_ids: list[int]) -> str:
        """收集指定资源上的用户笔记，格式化为 prompt 文本。无笔记时返回空字符串。"""
        if not resource_ids:
            return ""
        await init_db()
        annotations = await ResourceAnnotation.filter(
            user_id=user_id, resource_id__in=resource_ids
        ).order_by("created_at").all()
        if not annotations:
            return ""

        lines = [
            "以下内容为用户在对应学习资源上手动标注的笔记，反映了用户的学习关注点和可能存在的理解难点。",
            "请在出题时：",
            "1. 对笔记涉及的知识点适当提高出题优先级",
            "2. 若笔记暴露了用户的误解或薄弱环节，针对性出题帮助其纠正",
            "3. 笔记中反复出现的关键词应纳入考点",
            "",
        ]
        for a in annotations:
            lines.append(f"- 原文：「{a.selected_text}」")
            lines.append(f"  笔记：{a.note_text}")
        return "\n".join(lines)


def _annotation_to_dict(a: ResourceAnnotation) -> dict:
    return {
        "id": a.id,
        "resource_id": a.resource_id,
        "selected_text": a.selected_text,
        "note_text": a.note_text,
        "position": a.position,
        "created_at": str(a.created_at) if a.created_at else None,
        "updated_at": str(a.updated_at) if a.updated_at else None,
    }

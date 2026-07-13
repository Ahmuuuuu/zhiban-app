import logging

from backend.src.models.annotation_model import ResourceAnnotation
from backend.src.utils.database import init_db

logger = logging.getLogger(__name__)


async def create(user_id: int, data: dict) -> dict:
    await init_db()
    annotation = await ResourceAnnotation.create(
        user_id=user_id,
        source_type=data["source_type"],
        source_id=data["source_id"],
        selected_text=data["selected_text"],
        note_text=data["note_text"],
        position=data.get("position"),
    )
    logger.info("笔记已创建 id=%s user_id=%s source_type=%s source_id=%s",
                 annotation.id, user_id, data["source_type"], data["source_id"])
    return _annotation_to_dict(annotation)

async def update(annotation_id: int, user_id: int, note_text: str) -> dict | None:
    await init_db()
    annotation = await ResourceAnnotation.filter(id=annotation_id, user_id=user_id).first()
    if not annotation:
        return None
    annotation.note_text = note_text
    await annotation.save(update_fields=["note_text", "updated_at"])
    return _annotation_to_dict(annotation)

async def delete(annotation_id: int, user_id: int) -> bool:
    await init_db()
    annotation = await ResourceAnnotation.filter(id=annotation_id, user_id=user_id).first()
    if not annotation:
        return False
    await annotation.delete()
    logger.info("笔记已删除 id=%s user_id=%s", annotation_id, user_id)
    return True

async def list_by_resource(source_type: str, source_id: int, user_id: int) -> list[dict]:
    await init_db()
    annotations = await ResourceAnnotation.filter(
        source_type=source_type, source_id=source_id, user_id=user_id,
    ).order_by("created_at").all()
    return [_annotation_to_dict(a) for a in annotations]

async def collect_notes_for_quiz(user_id: int, generated_resource_ids: list[int]) -> str:
    """收集 GeneratedResource 上的用户笔记，格式化为 prompt 文本。无笔记时返回空字符串。"""
    if not generated_resource_ids:
        return ""
    await init_db()
    annotations = await ResourceAnnotation.filter(
        user_id=user_id, source_type="generated", source_id__in=generated_resource_ids,
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
        "source_type": a.source_type,
        "source_id": a.source_id,
        "selected_text": a.selected_text,
        "note_text": a.note_text,
        "position": a.position,
        "created_at": str(a.created_at) if a.created_at else None,
        "updated_at": str(a.updated_at) if a.updated_at else None,
    }

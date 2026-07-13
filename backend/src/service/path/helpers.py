"""Internal helpers for learning path services."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

from backend.src.models.exam_model import KnowledgeMastery
from backend.src.models.path_model import PathNode, UserPathProgress
from backend.src.models.portraitmodel import User_picture
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.usermodel import User
from backend.src.service.notification.service import check_and_create_node_unlocked

logger = logging.getLogger(__name__)

GenerateResources = Callable[[int, int, int], Awaitable[dict]]
GenerateQuiz = Callable[..., Awaitable[dict]]


async def check_existing_resources(
    user_id: int,
    topic: str,
    resource_types: list[str] | None = None,
):
    """Return existing resource records and missing resource types for a path node."""
    if resource_types is None:
        resource_types = ["document", "ppt", "mindmap"]

    existing_records = []
    missing_types = []
    for resource_type in resource_types:
        record = await GeneratedResource.filter(
            user_id=user_id,
            topic=topic,
            resource_type=resource_type,
        ).first()
        if record:
            existing_records.append(record)
        else:
            missing_types.append(resource_type)
    return existing_records, missing_types


async def update_progress_resource_ids(progress, all_ids: list[int]):
    """Persist generated resource ids and move an unlocked node into progress."""
    update_fields = {"resource_ids": json.dumps(all_ids, ensure_ascii=False)}
    if progress.node_status == "unlocked":
        update_fields["node_status"] = "in_progress"
        update_fields["started_at"] = datetime.now()
    await UserPathProgress.filter(id=progress.id).update(**update_fields)


async def check_resource_viewed(node_id: int, user_id: int) -> tuple[bool, int]:
    """Return whether any node resource has been viewed and the total view count."""
    progress = await UserPathProgress.filter(user_id=user_id, node_id=node_id).first()
    if not progress or not progress.resource_ids:
        return False, 0

    resource_ids = json.loads(progress.resource_ids) if progress.resource_ids else []
    if not resource_ids:
        return False, 0

    resources = await GeneratedResource.filter(id__in=resource_ids).all()
    total_views = sum(resource.view_count or 0 for resource in resources)
    return total_views > 0, total_views


async def pre_generate_node(
    path_id: int,
    node_id: int,
    user_id: int,
    generate_resources: GenerateResources,
    generate_quiz: GenerateQuiz,
):
    try:
        await asyncio.gather(
            generate_resources(path_id, node_id, user_id),
            generate_quiz(path_id, node_id, user_id, pre_generate=True),
        )
    except Exception:
        logger.exception("预生成节点资源/检测题失败 path_id=%s node_id=%s", path_id, node_id)


async def unlock_next_node(
    path_id: int,
    current_order: int,
    user_id: int,
    generate_resources: GenerateResources,
    generate_quiz: GenerateQuiz,
):
    """Unlock the next node and pre-generate resources for the next two nodes."""
    next_node = await PathNode.filter(path_id=path_id, order_index=current_order + 1).first()
    if not next_node:
        return

    await UserPathProgress.filter(
        user_id=user_id,
        path_id=path_id,
        node_id=next_node.id,
    ).update(node_status="unlocked")

    await check_and_create_node_unlocked(user_id, next_node.topic, path_id, next_node.id)

    pre_gen_ids = [next_node.id]
    node_after = await PathNode.filter(path_id=path_id, order_index=current_order + 2).first()
    if node_after:
        pre_gen_ids.append(node_after.id)

    await asyncio.gather(
        *(
            pre_generate_node(path_id, node_id, user_id, generate_resources, generate_quiz)
            for node_id in pre_gen_ids
        )
    )


async def update_portrait_from_mastery(user_id: int):
    """Summarize knowledge mastery and sync it into portrait traits."""
    records = await KnowledgeMastery.filter(user_id=user_id).all()
    if not records:
        return

    mastery_data = [
        {
            "tag": record.knowledge_tag,
            "level": record.mastery_level,
            "accuracy": round(record.correct_count / max(record.total_attempts, 1), 2),
        }
        for record in records
    ]

    strengths = [item["tag"] for item in mastery_data if item["level"] in ("mastered", "proficient")]
    weaknesses = [item["tag"] for item in mastery_data if item["level"] == "beginner"]
    avg_accuracy = round(sum(item["accuracy"] for item in mastery_data) / len(mastery_data), 2)
    level_map = {"beginner": 1, "learning": 2, "proficient": 3, "mastered": 4}
    avg_level = sum(level_map.get(item["level"], 1) for item in mastery_data) / len(mastery_data)
    knowbase = round(min(avg_level, 5), 1)

    user = await User.filter(id=user_id).prefetch_related("picture").first()
    if not user:
        return

    picture = await user.picture
    if not picture:
        picture = await User_picture.create()
        user.picture = picture
        await user.save()

    existing = {}
    if picture.traits:
        try:
            existing = json.loads(picture.traits)
        except (json.JSONDecodeError, TypeError):
            logger.warning("画像 traits JSON 解析失败 user_id=%s", user_id)
            existing = {}

    existing["knowledge_mastery"] = mastery_data
    existing["updated_at"] = str(datetime.now())
    existing["knowbase"] = {
        "value": str(knowbase),
        "confidence": min(0.95, 0.3 + avg_accuracy * 0.5),
        "source": "agent_inferred",
    }
    if strengths:
        existing["strengths"] = {
            "value": "、".join(strengths[:5]),
            "confidence": 0.85,
            "source": "agent_inferred",
        }
    if weaknesses:
        existing["weaknesses"] = {
            "value": "、".join(weaknesses[:5]),
            "confidence": 0.75,
            "source": "agent_inferred",
        }

    picture.traits = json.dumps(existing, ensure_ascii=False)
    await picture.save()

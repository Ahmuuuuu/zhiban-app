"""Chat-history records for generated resources."""

from __future__ import annotations

import json
import logging

from backend.src.models.chat_history_model import ChatHistory
from backend.src.service.resource.metadata import FILE_EXT_MAP

logger = logging.getLogger(__name__)


def resource_history_response(resources: list[dict], topic: str = "") -> str:
    if not resources:
        return json.dumps(
            {
                "type": "resource_list",
                "topic": topic,
                "resources": [],
                "message": "资源生成完成，但没有生成可保存的文件。",
            },
            ensure_ascii=False,
        )

    items = []
    for resource in resources:
        file_type = resource.get("resource_type") or resource.get("file_type") or "resource"
        topic = resource.get("topic") or "学习资源"
        resource_id = resource.get("resource_id")
        ext = FILE_EXT_MAP.get(file_type, "md")
        filename = resource.get("filename") or f"{topic}_{file_type}.{ext}"
        item = {
            "type": "resource",
            "file_type": file_type,
            "filename": filename,
            "file_id": resource_id,
            "resource_id": resource_id,
            "download_url": f"/resource/{resource_id}/download" if resource_id else None,
            "topic": topic,
        }
        if file_type == "external_video":
            for key in (
                "cover_url",
                "embed_url",
                "title",
                "author",
                "duration_text",
                "view_count_text",
                "source",
                "source_label",
                "description",
                "file_url",
                "preview_url",
            ):
                if resource.get(key):
                    item[key] = resource[key]
        items.append(item)

    return json.dumps({"type": "resource_list", "topic": topic, "resources": items}, ensure_ascii=False)


async def save_generation_to_history(
    user_id: int,
    chat_group_id: int,
    req: str,
    resources: list[dict],
    *,
    include_request: bool = True,
) -> None:
    if not chat_group_id or chat_group_id <= 0:
        logger.warning("跳过历史保存：chat_group_id=%s user_id=%s", chat_group_id, user_id)
        return
    try:
        await ChatHistory.create(
            user_id=user_id,
            chat_group_id=chat_group_id,
            req=req if include_request else "",
            res=resource_history_response(resources, topic=req),
        )
        logger.info(
            "资源生成历史已保存 user_id=%s chat_group_id=%s resources=%d",
            user_id,
            chat_group_id,
            len(resources) if resources else 0,
        )
    except Exception:
        logger.exception("保存资源生成历史失败 user_id=%s chat_group_id=%s", user_id, chat_group_id)

"""Persistence helpers for generated resources."""

from __future__ import annotations

import re

from backend.src.models.resource_model import GeneratedResource
from backend.src.models.usermodel import User
from backend.src.service.resource.metadata import (
    apply_ppt_theme_to_content,
    build_cover_url,
    extract_ppt_theme_id,
)


def clean_generation_topic(topic: str | None) -> str:
    text = str(topic or "").strip()
    text = re.sub(r"\n\n【生成类型指令】[\s\S]*$", "", text)
    text = re.sub(r"\n\n【思维导图模板】[\s\S]*$", "", text)
    return text.strip() or "学习资源"


async def save_resources(
    topic: str,
    user_id: int,
    generated: dict,
    review_passed: bool,
    retry_count: int,
    file_urls: dict | None = None,
    ppt_theme_id: str | None = None,
) -> list[dict]:
    """Persist generated resource content in one transaction."""
    from tortoise.transactions import in_transaction

    user = await User.filter(id=user_id).first()
    if not user:
        return []

    file_urls = file_urls or {}
    topic = clean_generation_topic(topic)
    saved: list[dict] = []

    async with in_transaction():
        for resource_type, content in generated.items():
            item_content = (
                apply_ppt_theme_to_content(content, ppt_theme_id)
                if resource_type == "ppt"
                else content
            )
            record = await GeneratedResource.create(
                topic=topic,
                resource_type=resource_type,
                content=item_content,
                review_passed=review_passed,
                retry_count=retry_count,
                file_url=file_urls.get(resource_type),
                user=user,
            )
            cover_url = build_cover_url(resource_type, file_urls.get(resource_type), record.id)
            if cover_url:
                await GeneratedResource.filter(id=record.id).update(cover_url=cover_url)
            saved.append(
                {
                    "resource_id": record.id,
                    "topic": record.topic,
                    "resource_type": record.resource_type,
                    "content": record.content,
                    "review_passed": record.review_passed,
                    "retry_count": record.retry_count,
                    "file_url": record.file_url,
                    "cover_url": cover_url,
                    "visibility": record.visibility or "private",
                }
            )
            if resource_type == "ppt":
                saved[-1]["ppt_theme_id"] = extract_ppt_theme_id(record.content)
    return saved

"""Resource metadata helpers shared by resource services."""

from __future__ import annotations

import logging
import re

from backend.src.models.resource_model import GeneratedResource
from backend.src.utils.mindmap import parse_mindmap_text

logger = logging.getLogger(__name__)

FILE_EXT_MAP = {
    "document": "md",
    "ppt": "pptx",
    "mindmap": "txt",
    "exercise": "md",
    "case": "md",
    "reading": "md",
    "slide_animation": "json",
    "audio": "mp3",
    "html": "html",
    "video": "html",
    "external_video": "url",
}

PPT_THEME_RE = re.compile(
    r"^\s*<!--\s*theme\s*:\s*([A-Za-z0-9_-]{1,64})\s*-->\s*$",
    re.IGNORECASE | re.MULTILINE,
)
PPT_META_COMMENT_RE = re.compile(
    r"^\s*<!--\s*(?:theme|layout|visual)\s*:[\s\S]*?-->\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def format_mindmap_content(content: str | None) -> str | dict | None:
    if not content:
        return content
    try:
        return parse_mindmap_text(content)
    except Exception:
        logger.exception("思维导图 JSON 转换失败")
        return content


def normalize_ppt_theme_id(ppt_theme_id: str | None) -> str:
    theme_id = str(ppt_theme_id or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", theme_id):
        return theme_id
    return ""


def extract_ppt_theme_id(content: str | None) -> str:
    match = PPT_THEME_RE.search(content or "")
    return match.group(1) if match else ""


def looks_like_ppt_markdown(content: str | None) -> bool:
    text = PPT_META_COMMENT_RE.sub("", str(content or "")).strip()
    return text.startswith("#")


def apply_ppt_theme_to_content(content: str | None, ppt_theme_id: str | None) -> str | None:
    theme_id = normalize_ppt_theme_id(ppt_theme_id)
    if not content or not theme_id:
        return content

    blocks = re.split(r"\n\s*---+\s*\n", str(content).strip())
    themed_blocks: list[str] = []
    for block in blocks:
        clean_block = PPT_THEME_RE.sub("", block).strip()
        themed_blocks.append(f"<!-- theme: {theme_id} -->\n{clean_block}".strip())
    return "\n---\n".join(themed_blocks)


def build_cover_url(resource_type: str, file_url: str | None, resource_id: int) -> str | None:
    if resource_type == "image" and file_url:
        return file_url
    return f"/static/covers/default_{resource_type}.svg"


async def resource_to_dict(
    record: GeneratedResource,
    current_user_id: int | None = None,
    include_content: bool = False,
) -> dict:
    ext = FILE_EXT_MAP.get(record.resource_type, "md")
    content = record.content
    preview = content[:200] if content else ""
    if record.resource_type == "mindmap" and content:
        try:
            preview = parse_mindmap_text(content)
            if include_content:
                content = format_mindmap_content(content)
        except Exception:
            logger.exception("思维导图 JSON 转换失败 resource_id=%s", record.id)

    item = {
        "resource_id": record.id,
        "topic": record.topic,
        "title": record.topic,
        "resource_type": record.resource_type,
        "filename": f"{record.topic}_{record.resource_type}.{ext}",
        "file_type": ext,
        "preview": preview,
        "download_url": f"/resource/{record.id}/download",
        "review_passed": record.review_passed,
        "created_at": str(record.created_at),
        "updated_at": str(record.updated_at),
        "view_count": record.view_count,
        "download_count": record.download_count,
        "like_count": record.like_count,
        "favorite_count": record.favorite_count,
        "cover_url": record.cover_url,
        "visibility": record.visibility or "private",
        "owner_user_id": record.user_id,
        "is_owner": bool(current_user_id and record.user_id == current_user_id),
    }
    if record.resource_type == "ppt":
        item["ppt_theme_id"] = extract_ppt_theme_id(record.content)
    if include_content:
        item["content"] = content
        item["retry_count"] = record.retry_count
    if record.file_url:
        item["file_url"] = record.file_url
        item["url"] = record.file_url
        item["preview_url"] = record.file_url if record.resource_type in ("html", "video", "external_video") else ""

    if current_user_id:
        from backend.src.models.study_model import ResourceCollection, ResourceLike

        item["liked"] = await ResourceLike.filter(user_id=current_user_id, resource_id=record.id).exists()
        item["favorited"] = await ResourceCollection.filter(user_id=current_user_id, resource_id=record.id).exists()
    else:
        item["liked"] = False
        item["favorited"] = False
    return item

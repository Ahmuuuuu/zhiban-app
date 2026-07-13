"""Resource library operations.

This module owns resource CRUD, visibility, download, and user interaction
state. Generation orchestration stays in ResourceService for now.
"""

from __future__ import annotations

import logging
from datetime import datetime

from tortoise.expressions import F, Q

from backend.src.models.resource_model import GeneratedResource
from backend.src.models.usermodel import User
from backend.src.service.resource.metadata import (
    FILE_EXT_MAP,
    build_cover_url,
    extract_ppt_theme_id,
    format_mindmap_content,
    looks_like_ppt_markdown,
    resource_to_dict,
)
from backend.src.utils.mindmap import parse_mindmap_text

logger = logging.getLogger(__name__)


class ResourceLibraryService:
    @staticmethod
    async def toggle_like(resource_id: int, user_id: int) -> dict:
        from backend.src.models.study_model import ResourceLike

        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")
        resource = await GeneratedResource.filter(id=resource_id).first()
        if not resource:
            raise ValueError("资源不存在")

        existing = await ResourceLike.filter(user_id=user_id, resource_id=resource_id).first()
        if existing:
            await existing.delete()
            await GeneratedResource.filter(id=resource_id).update(like_count=F("like_count") - 1)
            await resource.refresh_from_db()
            return {"liked": False, "like_count": resource.like_count}

        await ResourceLike.create(user=user, resource=resource)
        await GeneratedResource.filter(id=resource_id).update(like_count=F("like_count") + 1)
        await resource.refresh_from_db()
        return {"liked": True, "like_count": resource.like_count}

    @staticmethod
    async def toggle_favorite(resource_id: int, user_id: int) -> dict:
        from backend.src.models.study_model import ResourceCollection

        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")
        resource = await GeneratedResource.filter(id=resource_id).first()
        if not resource:
            raise ValueError("资源不存在")

        existing = await ResourceCollection.filter(user_id=user_id, resource_id=resource_id).first()
        if existing:
            await existing.delete()
            await GeneratedResource.filter(id=resource_id).update(favorite_count=F("favorite_count") - 1)
            await resource.refresh_from_db()
            return {"favorited": False, "favorite_count": resource.favorite_count}

        await ResourceCollection.create(user=user, resource=resource)
        await GeneratedResource.filter(id=resource_id).update(favorite_count=F("favorite_count") + 1)
        await resource.refresh_from_db()
        return {"favorited": True, "favorite_count": resource.favorite_count}

    @staticmethod
    async def get_resource(resource_id: int, user_id: int) -> dict | None:
        record = await GeneratedResource.filter(
            Q(id=resource_id),
            Q(user_id=user_id) | Q(visibility="public"),
        ).first()
        if not record:
            return None

        await GeneratedResource.filter(id=resource_id).update(
            view_count=F("view_count") + 1,
            last_viewed_at=datetime.now(),
        )
        await record.refresh_from_db()

        content = record.content
        if record.resource_type == "mindmap":
            content = format_mindmap_content(content)

        result = {
            "resource_id": record.id,
            "topic": record.topic,
            "resource_type": record.resource_type,
            "content": content,
            "review_passed": record.review_passed,
            "retry_count": record.retry_count,
            "created_at": str(record.created_at),
            "view_count": record.view_count,
            "download_count": record.download_count,
            "like_count": record.like_count,
            "favorite_count": record.favorite_count,
            "cover_url": record.cover_url,
            "visibility": record.visibility or "private",
            "owner_user_id": record.user_id,
            "is_owner": record.user_id == user_id,
        }
        if record.file_url:
            result["file_url"] = record.file_url
            result["url"] = record.file_url
            result["preview_url"] = record.file_url if record.resource_type in ("html", "video", "external_video") else ""

        from backend.src.models.study_model import ResourceCollection, ResourceLike

        result["liked"] = await ResourceLike.filter(user_id=user_id, resource_id=resource_id).exists()
        result["favorited"] = await ResourceCollection.filter(user_id=user_id, resource_id=resource_id).exists()

        if record.resource_type == "ppt" and looks_like_ppt_markdown(record.content):
            try:
                from backend.src.utils.tts_utils import parse_slides

                slides_data = parse_slides(record.content)
                result["slides"] = [
                    {
                        **slide,
                        "index": i,
                        "title": slide.get("title", ""),
                        "text": slide.get("text", ""),
                        "notes": slide.get("notes", ""),
                    }
                    for i, slide in enumerate(slides_data)
                ]
            except Exception:
                logger.warning("PPT 幻灯片元数据解析失败 resource_id=%s", resource_id)

        try:
            from backend.src.utils.tts_utils import NARRATABLE_TYPES

            if record.resource_type in NARRATABLE_TYPES:
                from backend.src.models.narration_model import Narration

                narration = await Narration.filter(resource_id=resource_id).order_by("-created_at").first()
                if narration:
                    result["narration"] = {
                        "narration_id": narration.id,
                        "voice": narration.voice,
                        "sections": narration.slides_json,
                        "created_at": str(narration.created_at),
                    }
        except Exception:
            logger.warning("旁白查询失败 resource_id=%s", resource_id)

        return result

    @staticmethod
    async def list_resources(user_id: int, visibility: str | None = None) -> list[dict]:
        if visibility == "public":
            records = await GeneratedResource.filter(visibility="public").order_by("-created_at").all()
        else:
            records = await GeneratedResource.filter(user_id=user_id).order_by("-created_at").all()

        result = []
        for record in records:
            ext = FILE_EXT_MAP.get(record.resource_type, "md")
            preview = record.content[:200] if record.content else ""
            if record.resource_type == "mindmap" and record.content:
                try:
                    preview = parse_mindmap_text(record.content)
                except Exception:
                    logger.exception("思维导图预览 JSON 转换失败 resource_id=%s", record.id)

            item = {
                "resource_id": record.id,
                "topic": record.topic,
                "resource_type": record.resource_type,
                "filename": f"{record.topic}_{record.resource_type}.{ext}",
                "file_type": ext,
                "preview": preview,
                "download_url": f"/resource/{record.id}/download",
                "review_passed": record.review_passed,
                "created_at": str(record.created_at),
                "view_count": record.view_count,
                "download_count": record.download_count,
                "like_count": record.like_count,
                "favorite_count": record.favorite_count,
                "cover_url": record.cover_url,
                "visibility": record.visibility or "private",
                "owner_user_id": record.user_id,
                "is_owner": record.user_id == user_id,
            }
            if record.file_url:
                item["file_url"] = record.file_url
                item["url"] = record.file_url
                item["preview_url"] = record.file_url if record.resource_type in ("html", "video", "external_video") else ""

            from backend.src.models.study_model import ResourceCollection, ResourceLike

            item["liked"] = await ResourceLike.filter(user_id=user_id, resource_id=record.id).exists()
            item["favorited"] = await ResourceCollection.filter(user_id=user_id, resource_id=record.id).exists()
            result.append(item)
        return result

    @staticmethod
    async def admin_list_resources(visibility: str | None = None, include_content: bool = False) -> list[dict]:
        query = GeneratedResource.all()
        if visibility:
            query = query.filter(visibility=visibility)
        records = await query.order_by("-updated_at", "-created_at").all()
        return [await resource_to_dict(record, None, include_content=include_content) for record in records]

    @staticmethod
    async def admin_update_resource(resource_id: int, data: dict) -> dict | None:
        record = await GeneratedResource.filter(id=resource_id).first()
        if not record:
            return None

        title = data.get("title") or data.get("topic")
        resource_type = data.get("resource_type") or data.get("resourceType")
        content = data.get("content")
        visibility = data.get("visibility")
        cover_url = data.get("cover_url") or data.get("coverUrl")
        file_url = data.get("file_url") or data.get("fileUrl")

        update_fields = ["updated_at"]
        if title is not None:
            record.topic = str(title).strip() or record.topic
            update_fields.append("topic")
        if resource_type is not None:
            record.resource_type = str(resource_type).strip() or record.resource_type
            update_fields.append("resource_type")
        if content is not None:
            record.content = str(content)
            update_fields.append("content")
        if visibility is not None:
            value = str(visibility).strip()
            if value in ("public", "private", "pending", "rejected"):
                record.visibility = value
                update_fields.append("visibility")
        if cover_url is not None:
            record.cover_url = str(cover_url).strip() or None
            update_fields.append("cover_url")
        if file_url is not None:
            record.file_url = str(file_url).strip() or None
            update_fields.append("file_url")

        await record.save(update_fields=list(dict.fromkeys(update_fields)))
        return await resource_to_dict(record, None, include_content=True)

    @staticmethod
    async def admin_delete_resource(resource_id: int) -> bool:
        record = await GeneratedResource.filter(id=resource_id).first()
        if not record:
            return False
        await record.delete()
        return True

    @staticmethod
    async def admin_approve_resource(resource_id: int) -> dict | None:
        return await ResourceLibraryService.admin_update_resource(resource_id, {"visibility": "public"})

    @staticmethod
    async def admin_reject_resource(resource_id: int) -> dict | None:
        return await ResourceLibraryService.admin_update_resource(resource_id, {"visibility": "rejected"})

    @staticmethod
    async def admin_import_base_resource(admin_id: int, data: dict) -> dict | None:
        user = await User.filter(id=admin_id).first()
        if not user:
            return None

        title = str(data.get("title") or data.get("topic") or "基础资源").strip()
        resource_type = str(data.get("resource_type") or data.get("resourceType") or "document").strip() or "document"
        content = str(data.get("content") or data.get("preview") or "").strip()
        file_url = str(data.get("file_url") or data.get("fileUrl") or "").strip() or None
        cover_url = str(data.get("cover_url") or data.get("coverUrl") or "").strip() or None

        if not content:
            content = f"{title}\n\n该资源由管理员导入。"

        record = await GeneratedResource.create(
            topic=title,
            resource_type=resource_type,
            content=content,
            review_passed=True,
            retry_count=0,
            visibility="public",
            file_url=file_url,
            cover_url=cover_url,
            user=user,
        )
        if not record.cover_url:
            cover = build_cover_url(resource_type, file_url, record.id)
            if cover:
                record.cover_url = cover
                await record.save(update_fields=["cover_url", "updated_at"])
        return await resource_to_dict(record, admin_id, include_content=True)

    @staticmethod
    async def publish_resource(resource_id: int, user_id: int, visibility: str = "public") -> dict | None:
        if visibility not in ("public", "private", "pending", "rejected"):
            visibility = "private"
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return None
        record.visibility = visibility
        await record.save(update_fields=["visibility", "updated_at"])
        return await resource_to_dict(record, user_id, include_content=True)

    @staticmethod
    async def download_resource(resource_id: int, user_id: int) -> tuple[bytes, str, str] | None:
        record = await GeneratedResource.filter(
            Q(id=resource_id),
            Q(user_id=user_id) | Q(visibility="public"),
        ).first()
        if not record:
            return None
        record.download_count += 1
        await record.save()
        ext = FILE_EXT_MAP.get(record.resource_type, "md")
        filename = f"{record.topic}_{record.resource_type}.{ext}"
        if record.resource_type == "ppt":
            try:
                from backend.src.utils.pptx_generator import markdown_to_pptx
            except ImportError:
                raise ImportError("PPT 导出需要安装 python-pptx 依赖")

            content_bytes = markdown_to_pptx(record.content, extract_ppt_theme_id(record.content))
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            return content_bytes, f"{record.topic}_ppt.pptx", media_type
        return record.content.encode("utf-8"), filename, "text/markdown; charset=utf-8"

    @staticmethod
    async def delete_resource(resource_id: int, user_id: int) -> bool:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return False
        await record.delete()
        return True

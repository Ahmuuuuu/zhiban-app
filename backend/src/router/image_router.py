"""图片生成 API"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from tortoise.expressions import Q

from backend.src.service.image_service import ImageService
from backend.src.models.image_model import GeneratedImage
from backend.src.schemas.image import GenerateImageRequest
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/image", tags=["AI 图片生成"])

IMAGES_DIR = Path(__file__).parent.parent.parent / "static" / "images"


class ImageVisibilityRequest(BaseModel):
    visibility: str = Field(default="public", pattern="^(public|private)$")


@router.post("/generate")
async def generate_image(
    user_id: int = Depends(get_user_id_from_token),
    data: GenerateImageRequest = Body(...),
):
    """提交图片生成任务到讯飞 HiDream，立即返回 task_id，后台异步轮询"""
    from backend.src.service.image_service import _ensure_prompt_quality
    try:
        prompt = await _ensure_prompt_quality(data.prompt)
        result = await ImageService.submit(
            prompt=prompt,
            user_id=user_id,
            aspect_ratio=data.aspect_ratio,
            img_count=data.img_count,
            chat_group_id=data.chat_group_id,
        )
        return {"code": 200, "msg": "任务已提交", "data": result}
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """查询图片生成任务状态，每次调用会主动查询一次讯飞"""
    result = await ImageService.poll_once(task_id)
    if result is None:
        return {"code": 404, "msg": "任务不存在"}
    return {"code": 200, "msg": "success", "data": result}


@router.get("/list")
async def list_images(
    user_id: int = Depends(get_user_id_from_token),
    visibility: str | None = Query(None),
):
    """列出当前用户生成的所有图片"""
    try:
        if visibility == "public":
            records = await GeneratedImage.filter(visibility="public").order_by("-created_at").all()
        else:
            records = await GeneratedImage.filter(user_id=user_id).order_by("-created_at").all()
        data = [
            {
                "image_id": r.id,
                "prompt": r.prompt,
                "filename": r.filename,
                "url": f"/static/images/{r.filename}",
                "aspect_ratio": r.aspect_ratio,
                "visibility": r.visibility or "private",
                "owner_user_id": r.user_id,
                "is_owner": r.user_id == user_id,
                "created_at": str(r.created_at),
            }
            for r in records
        ]
        return {"code": 200, "msg": "success", "data": data}
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.post("/{image_id}/visibility")
async def update_image_visibility(
    image_id: int,
    data: ImageVisibilityRequest = Body(...),
    user_id: int = Depends(get_user_id_from_token),
):
    try:
        r = await GeneratedImage.filter(id=image_id, user_id=user_id).first()
        if not r:
            return {"code": 404, "msg": "图片不存在或无权操作"}
        r.visibility = data.visibility
        await r.save(update_fields=["visibility"])
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "image_id": r.id,
                "prompt": r.prompt,
                "filename": r.filename,
                "url": f"/static/images/{r.filename}",
                "aspect_ratio": r.aspect_ratio,
                "visibility": r.visibility,
                "owner_user_id": r.user_id,
                "is_owner": True,
                "created_at": str(r.created_at),
            },
        }
    except Exception:
        raise HTTPException(500, "更新图片可见性失败")


@router.get("/{image_id}")
async def get_image(
    image_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    """获取单张图片的详情"""
    try:
        r = await GeneratedImage.filter(Q(id=image_id), Q(user_id=user_id) | Q(visibility="public")).first()
        if not r:
            return {"code": 404, "msg": "图片不存在"}
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "image_id": r.id,
                "prompt": r.prompt,
                "filename": r.filename,
                "url": f"/static/images/{r.filename}",
                "aspect_ratio": r.aspect_ratio,
                "visibility": r.visibility or "private",
                "owner_user_id": r.user_id,
                "is_owner": r.user_id == user_id,
                "created_at": str(r.created_at),
            },
        }
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.get("/{image_id}/download")
async def download_image(
    image_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    """下载图片文件"""
    try:
        r = await GeneratedImage.filter(Q(id=image_id), Q(user_id=user_id) | Q(visibility="public")).first()
        if not r:
            return {"code": 404, "msg": "图片不存在"}
        filepath = IMAGES_DIR / r.filename
        if not filepath.exists():
            return {"code": 404, "msg": "图片文件不存在"}
        return FileResponse(
            path=str(filepath),
            media_type="image/jpeg",
            filename=r.filename,
            headers={"Content-Disposition": f'attachment; filename="{r.filename}"'},
        )
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    """删除图片及其文件"""
    try:
        r = await GeneratedImage.filter(id=image_id, user_id=user_id).first()
        if not r:
            return {"code": 404, "msg": "图片不存在"}
        filepath = IMAGES_DIR / r.filename
        if filepath.exists():
            filepath.unlink()
        await r.delete()
        return {"code": 200, "msg": "删除成功"}
    except Exception:
        raise HTTPException(500, "服务器错误")

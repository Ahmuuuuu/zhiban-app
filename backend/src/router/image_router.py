"""图片生成 API"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from fastapi.responses import FileResponse

from backend.src.service.image_service import ImageService
from backend.src.models.image_model import GeneratedImage
from backend.src.schemas.image import GenerateImageRequest
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/image", tags=["AI 图片生成"])

IMAGES_DIR = Path(__file__).parent.parent.parent / "static" / "images"


@router.post("/generate")
async def generate_image(
    user_id: int = Depends(get_user_id_from_token),
    data: GenerateImageRequest = Body(...),
):
    """调用 HiDream 生成图片，保存至服务器 static/images/ 目录"""
    try:
        records = await ImageService.generate(
            prompt=data.prompt,
            user_id=str(user_id),
            aspect_ratio=data.aspect_ratio,
            img_count=data.img_count,
        )
        return {"code": 200, "msg": "success", "data": records}
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except TimeoutError:
        raise HTTPException(504, "图片生成超时，请稍后重试")
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.get("/list")
async def list_images(user_id: int = Depends(get_user_id_from_token)):
    """列出当前用户生成的所有图片"""
    try:
        records = await GeneratedImage.filter(user_id=user_id).order_by("-created_at").all()
        data = [
            {
                "image_id": r.id,
                "prompt": r.prompt,
                "filename": r.filename,
                "url": f"/static/images/{r.filename}",
                "aspect_ratio": r.aspect_ratio,
                "created_at": str(r.created_at),
            }
            for r in records
        ]
        return {"code": 200, "msg": "success", "data": data}
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.get("/{image_id}")
async def get_image(
    image_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    """获取单张图片的详情"""
    try:
        r = await GeneratedImage.filter(id=image_id, user_id=user_id).first()
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
        r = await GeneratedImage.filter(id=image_id, user_id=user_id).first()
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

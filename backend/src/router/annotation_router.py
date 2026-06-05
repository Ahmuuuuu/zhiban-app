"""笔记路由"""

from fastapi import APIRouter, Depends, HTTPException

from backend.src.schemas.annotation import CreateAnnotationRequest, UpdateAnnotationRequest
from backend.src.service.annotation_service import AnnotationService
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/annotation", tags=["笔记"])


@router.get("/resource/{resource_id}")
async def list_annotations(
    resource_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    result = await AnnotationService.list_by_resource(resource_id, user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.post("")
async def create_annotation(
    body: CreateAnnotationRequest,
    user_id: int = Depends(get_user_id_from_token),
):
    annotation = await AnnotationService.create(user_id, body.model_dump())
    return {"code": 200, "msg": "success", "data": annotation}


@router.put("/{annotation_id}")
async def update_annotation(
    annotation_id: int,
    body: UpdateAnnotationRequest,
    user_id: int = Depends(get_user_id_from_token),
):
    result = await AnnotationService.update(annotation_id, user_id, body.note_text)
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在或无权操作")
    return {"code": 200, "msg": "success", "data": result}


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    ok = await AnnotationService.delete(annotation_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="笔记不存在或无权操作")
    return {"code": 200, "msg": "success", "data": None}

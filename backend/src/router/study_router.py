"""学习统计路由"""

from fastapi import APIRouter, HTTPException, Depends

from backend.src.service.study_service import StudyService
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/study", tags=["学习统计"])


@router.post("/heartbeat")
async def heartbeat(user_id: int = Depends(get_user_id_from_token)):
    """前端每 30 秒调用一次，累计学习时长"""
    result = await StudyService.heartbeat(user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/stats")
async def get_stats(user_id: int = Depends(get_user_id_from_token)):
    """聚合学习统计：时长、薄弱点、路径、资源、答题"""
    result = await StudyService.get_stats(user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.post("/resource/{resource_id}/mark-read")
async def mark_read(resource_id: int, user_id: int = Depends(get_user_id_from_token)):
    """标记资源为已读"""
    result = await StudyService.mark_read(user_id, resource_id)
    return {"code": 200, "msg": "已标记为已读", "data": result}


@router.post("/resource/{resource_id}/mark-unread")
async def mark_unread(resource_id: int, user_id: int = Depends(get_user_id_from_token)):
    """标记资源为未读"""
    result = await StudyService.mark_unread(user_id, resource_id)
    return {"code": 200, "msg": "已标记为未读", "data": result}

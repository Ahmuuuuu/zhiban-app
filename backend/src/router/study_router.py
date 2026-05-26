"""学习统计路由"""

from fastapi import APIRouter, Depends, HTTPException

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


@router.get("/learning-guidance")
async def get_learning_guidance(user_id: int = Depends(get_user_id_from_token)):
    """个性化学习方法建议"""
    result = await StudyService.get_learning_guidance(user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.post("/resource/{resource_id}/collect")
async def collect_resource(resource_id: int, user_id: int = Depends(get_user_id_from_token)):
    """收藏资源"""
    try:
        result = await StudyService.collect_resource(user_id, resource_id)
        return {"code": 200, "msg": "收藏成功", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/resource/{resource_id}/collect")
async def uncollect_resource(resource_id: int, user_id: int = Depends(get_user_id_from_token)):
    """取消收藏"""
    result = await StudyService.uncollect_resource(user_id, resource_id)
    return {"code": 200, "msg": "已取消收藏", "data": result}


@router.get("/collections")
async def list_collections(user_id: int = Depends(get_user_id_from_token)):
    """已收藏资源列表"""
    result = await StudyService.list_collections(user_id)
    return {"code": 200, "msg": "success", "data": result}

"""轻量学习路径路由 — 供前端动态路径动画"""

from fastapi import APIRouter, HTTPException, Depends, Body

from backend.src.service.path_service import PathService
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/learning_path", tags=["学习路径(轻量)"])


@router.get("/current")
async def get_current_path(user_id: int = Depends(get_user_id_from_token)):
    """用户当前活跃路径（含节点、进度、薄弱点诊断、下一步动作）"""
    result = await PathService.get_current_path(user_id)
    if not result:
        return {"code": 404, "msg": "暂无进行中的学习路径，请先生成或加入路径"}
    return {"code": 200, "msg": "success", "data": result}


@router.post("/nodes/{node_id}/complete")
async def complete_node(
    node_id: int,
    user_id: int = Depends(get_user_id_from_token),
    session_id: str = Body(..., embed=True),
):
    """完成节点测验 → 评分门禁 → 解锁下一节点，返回新节点供动画展示"""
    try:
        result = await PathService.complete_node(node_id, user_id, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}

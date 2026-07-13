"""轻量学习路径路由 — 供前端动态路径动画"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.src.service.path.service import PathService
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/learning_path", tags=["学习路径(轻量)"])


class CompleteNodeBody(BaseModel):
    session_id: str
    answers: Optional[Dict[str, Any]] = None
    correct_answers: Optional[Dict[str, Any]] = None


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
    body: CompleteNodeBody,
    user_id: int = Depends(get_user_id_from_token),
):
    """完成节点测验 → 评分门禁 → 解锁下一节点，返回新节点供动画展示"""
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("complete_node 请求 node_id=%s user_id=%s session_id=%r answers_count=%s correct_answers_count=%s", node_id, user_id, body.session_id, len(body.answers) if body.answers else 0, len(body.correct_answers) if body.correct_answers else 0)
    try:
        result = await PathService.complete_node(node_id, user_id, body.session_id, answers=body.answers, correct_answers=body.correct_answers)
    except ValueError as e:
        msg = str(e)
        if msg in ("节点不存在", "未加入该路径"):
            raise HTTPException(status_code=404, detail=msg)
        _logger.warning("complete_node 失败 node_id=%s user_id=%s session_id=%s: %s", node_id, user_id, body.session_id, msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        _logger.exception("complete_node 异常 node_id=%s user_id=%s session_id=%s", node_id, user_id, body.session_id)
        raise HTTPException(status_code=500, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}

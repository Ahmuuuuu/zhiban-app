"""题库路由"""

import json

from fastapi import APIRouter, Query, HTTPException, Depends

from backend.src.service.exam.service import ExamService
from backend.src.schemas.exam import GenerateExamRequest, SubmitAnswerRequest
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/exam", tags=["题库"])


@router.post("/generate")
async def generate_exam(data: GenerateExamRequest, user_id: int = Depends(get_user_id_from_token)):
    """AI 生成题目"""
    types = [t.strip() for t in data.question_types.split(",") if t.strip()]
    result = await ExamService.generate_and_save(data.topic, user_id, types, data.count, data.difficulty)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/questions")
async def list_questions(
    user_id: int = Depends(get_user_id_from_token),
    question_type: str | None = None,
    difficulty: str | None = None,
    knowledge_tag: str | None = None,
    node_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """题目列表（分页+筛选），传 node_id 仅返回该节点关联的题目"""
    result = await ExamService.list_questions(user_id, question_type, difficulty, knowledge_tag, node_id, page, page_size)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/questions/{question_id}")
async def get_question(question_id: int, user_id: int = Depends(get_user_id_from_token)):
    """题目详情"""
    question = await ExamService.get_question(question_id, user_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {"code": 200, "msg": "success", "data": question}


@router.delete("/questions/{question_id}")
async def delete_question(question_id: int, user_id: int = Depends(get_user_id_from_token)):
    """删除题目"""
    ok = await ExamService.delete_question(question_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="题目不存在或无权限")
    return {"code": 200, "msg": "已删除"}


@router.post("/submit")
async def submit_answer(data: SubmitAnswerRequest, user_id: int = Depends(get_user_id_from_token)):
    """提交答案"""
    try:
        answer = json.dumps(data.answer, ensure_ascii=False) if isinstance(data.answer, list) else data.answer
        result = await ExamService.submit_answer(data.question_id, user_id, answer, data.time_spent, data.session_id, data.node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.get("/records")
async def get_records(
    user_id: int = Depends(get_user_id_from_token),
    node_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """答题记录，传 node_id 仅返回该节点关联的记录"""
    result = await ExamService.get_records(user_id, node_id, page, page_size)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/session/{session_id}")
async def get_session(session_id: str, user_id: int = Depends(get_user_id_from_token)):
    """查询一次练习会话的完整状态"""
    result = await ExamService.get_session(session_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"code": 200, "msg": "success", "data": result}


@router.get("/sessions")
async def list_sessions(user_id: int = Depends(get_user_id_from_token)):
    """列出用户的所有练习会话摘要"""
    result = await ExamService.list_sessions(user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/statistics")
async def get_statistics(user_id: int = Depends(get_user_id_from_token)):
    """用户整体答题统计（按难度/题型/知识点正确率 + 总分）"""
    result = await ExamService.get_statistics(user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/mastery")
async def get_mastery(user_id: int = Depends(get_user_id_from_token)):
    """知识点掌握度"""
    result = await ExamService.get_mastery(user_id)
    return {"code": 200, "msg": "success", "data": result}

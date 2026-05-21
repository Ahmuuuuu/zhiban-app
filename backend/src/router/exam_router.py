"""题库路由"""

from fastapi import APIRouter, Query, HTTPException

from backend.src.service.exam_service import ExamService
from backend.src.schemas.exam import GenerateExamRequest, SubmitAnswerRequest

router = APIRouter(prefix="/exam", tags=["题库"])


@router.post("/generate")
async def generate_exam(data: GenerateExamRequest):
    """AI 生成题目"""
    types = [t.strip() for t in data.question_types.split(",") if t.strip()]
    questions = await ExamService.generate_and_save(data.topic, data.user_id, types, data.count, data.difficulty)
    return {"code": 200, "msg": "success", "data": questions}


@router.get("/questions")
async def list_questions(
    user_id: int,
    question_type: str | None = None,
    difficulty: str | None = None,
    knowledge_tag: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """题目列表（分页+筛选）"""
    result = await ExamService.list_questions(user_id, question_type, difficulty, knowledge_tag, page, page_size)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/questions/{question_id}")
async def get_question(question_id: int, user_id: int):
    """题目详情"""
    question = await ExamService.get_question(question_id, user_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {"code": 200, "msg": "success", "data": question}


@router.delete("/questions/{question_id}")
async def delete_question(question_id: int, user_id: int):
    """删除题目"""
    ok = await ExamService.delete_question(question_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="题目不存在或无权限")
    return {"code": 200, "msg": "已删除"}


@router.post("/submit")
async def submit_answer(data: SubmitAnswerRequest):
    """提交答案"""
    try:
        result = await ExamService.submit_answer(data.question_id, data.user_id, data.answer, data.time_spent)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.get("/records")
async def get_records(user_id: int, page: int = 1, page_size: int = 20):
    """答题记录"""
    result = await ExamService.get_records(user_id, page, page_size)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/mastery")
async def get_mastery(user_id: int):
    """知识点掌握度"""
    result = await ExamService.get_mastery(user_id)
    return {"code": 200, "msg": "success", "data": result}

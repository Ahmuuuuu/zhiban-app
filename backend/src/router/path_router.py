"""学习路径路由"""

from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import StreamingResponse

from backend.src.service.path.service import PathService
from backend.src.utils.jwt import get_user_id_from_token
from backend.src.schemas.path import (
    GeneratePathRequest,
    EnrollPathRequest,
    SubmitNodeQuizRequest,
    RegeneratePathRequest,
    GenerateFromProfileRequest,
)

router = APIRouter(prefix="/path", tags=["学习路径"])


@router.post("/generate")
async def generate_path(data: GeneratePathRequest, user_id: int = Depends(get_user_id_from_token)):
    """AI 生成学习路径"""
    result = await PathService.generate_path(data.subject, user_id, data.difficulty, data.node_count)
    return {"code": 200, "msg": "success", "data": result}


@router.post("/generate/stream")
async def generate_path_stream(data: GeneratePathRequest, user_id: int = Depends(get_user_id_from_token)):
    return StreamingResponse(
        PathService.generate_path_stream(data.subject, user_id, data.difficulty, data.node_count),
        media_type="text/event-stream",
    )


@router.get("/list")
async def list_paths(user_id: int = Depends(get_user_id_from_token)):
    """路径列表"""
    result = await PathService.list_paths(user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/{path_id}")
async def get_path(path_id: int, user_id: int = Depends(get_user_id_from_token)):
    """路径详情（含所有节点）"""
    result = await PathService.get_path(path_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="路径不存在")
    return {"code": 200, "msg": "success", "data": result}


@router.post("/enroll")
async def enroll_path(data: EnrollPathRequest, user_id: int = Depends(get_user_id_from_token)):
    """加入路径开始学习"""
    try:
        result = await PathService.enroll_path(data.path_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.get("/{path_id}/progress")
async def get_progress(path_id: int, user_id: int = Depends(get_user_id_from_token)):
    """用户在路径上的整体进度"""
    result = await PathService.get_progress(path_id, user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/{path_id}/node/{node_id}")
async def get_node(path_id: int, node_id: int, user_id: int = Depends(get_user_id_from_token)):
    """节点详情（含资源和进度）"""
    result = await PathService.get_node(path_id, node_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"code": 200, "msg": "success", "data": result}


@router.post("/{path_id}/node/{node_id}/generate-resources")
async def generate_node_resources(path_id: int, node_id: int, user_id: int = Depends(get_user_id_from_token)):
    """手动为节点生成学习资源"""
    try:
        result = await PathService.generate_node_resources(path_id, node_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.post("/{path_id}/node/{node_id}/generate-quiz")
async def generate_node_quiz(path_id: int, node_id: int, user_id: int = Depends(get_user_id_from_token)):
    """为节点生成测验题目"""
    try:
        result = await PathService.generate_node_quiz(path_id, node_id, user_id, pre_generate=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.post("/{path_id}/node/{node_id}/generate-resources/stream")
async def generate_node_resources_stream(path_id: int, node_id: int, user_id: int = Depends(get_user_id_from_token)):
    """流式为节点生成学习资源（SSE），生成好一个推送一个"""
    return StreamingResponse(
        PathService.generate_node_resources_stream(path_id, node_id, user_id),
        media_type="text/event-stream",
    )


@router.post("/{path_id}/node/{node_id}/generate-quiz/stream")
async def generate_node_quiz_stream(path_id: int, node_id: int, user_id: int = Depends(get_user_id_from_token)):
    """流式为节点生成测验题目（SSE）"""
    return StreamingResponse(
        PathService.generate_node_quiz_stream(path_id, node_id, user_id),
        media_type="text/event-stream",
    )


@router.post("/{path_id}/node/{node_id}/submit-quiz")
async def submit_node_quiz(
    path_id: int,
    node_id: int,
    data: SubmitNodeQuizRequest,
    user_id: int = Depends(get_user_id_from_token),
):
    """提交节点测验 → 评分 → 门禁 → 解锁下一节点"""
    try:
        result = await PathService.submit_node_quiz(path_id, node_id, user_id, data.session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.post("/{path_id}/video")
async def generate_path_video(path_id: int, user_id: int = Depends(get_user_id_from_token)):
    """为整条学习路径生成一个综合视频课件"""
    try:
        result = await PathService.generate_path_video(path_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.get("/{path_id}/video")
async def get_path_video(path_id: int, user_id: int = Depends(get_user_id_from_token)):
    """获取路径已有的视频课件"""
    result = await PathService.get_path_video(path_id, user_id)
    if not result:
        return {"code": 200, "msg": "success", "data": None}
    return {"code": 200, "msg": "success", "data": result}


@router.post("/regenerate")
async def regenerate_path(data: RegeneratePathRequest, user_id: int = Depends(get_user_id_from_token)):
    """基于最新画像重建路径"""
    try:
        result = await PathService.regenerate_path(data.path_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "msg": "success", "data": result}


@router.post("/generate-from-profile")
async def generate_paths_from_profile(data: GenerateFromProfileRequest, user_id: int = Depends(get_user_id_from_token)):
    """根据用户专业 + 年级自动获取课程 → 批量生成学习路径（1h 内不重复）"""
    from datetime import datetime, timedelta
    from backend.src.models.usermodel import User
    from backend.src.models.path_model import LearningPath
    from backend.src.service.curriculum.service import get_courses
    from backend.src.models.notification_model import Notification

    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.major:
        raise HTTPException(status_code=400, detail="请先在个人资料中设置专业")

    # 时间窗口防抖
    recent = await LearningPath.filter(
        user_id=user_id,
        created_at__gte=datetime.now() - timedelta(hours=1),
    ).first()
    if recent:
        return {"code": 200, "msg": "1小时内已生成过路径，请稍后再试", "data": {"major": user.major, "grade": user.grade, "courses": [], "paths": []}}

    courses = await get_courses(user.major, user.grade or "")
    courses = courses[:max(1, data.course_limit)]

    import asyncio
    results = await asyncio.gather(
        *[PathService.generate_path(course, user_id, data.difficulty, data.node_count) for course in courses],
        return_exceptions=True,
    )

    new_paths = []
    cached_count = 0
    for course, result in zip(courses, results):
        if isinstance(result, Exception):
            continue
        if result.get("cached"):
            cached_count += 1
        else:
            new_paths.append({"path_id": result.get("path_id"), "subject": course, "nodes": result.get("nodes", [])})

    all_subjects = [p.get("subject") for p in new_paths]
    if new_paths:
        course_names = "、".join(all_subjects)
        grade_text = f"{user.grade}" if user.grade else ""
        suffix = f"（另外 {cached_count} 门已存在，已跳过）" if cached_count else ""
        await Notification.create(
            type="system",
            title="学习路径已生成",
            content=f"已根据{grade_text}{user.major}的课程（{course_names}）生成 {len(new_paths)} 条学习路径。{suffix}",
            target_url=f"/learning-path?major={user.major}",
            target_user_id=user_id,
        )

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "major": user.major,
            "grade": user.grade,
            "courses": all_subjects,
            "paths": new_paths,
        },
    }

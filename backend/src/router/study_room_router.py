"""自习室 API — 会话、帧检测、延时摄影"""

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.src.service.study_room.service import StudyRoomNotFound, StudyRoomService
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/study-room", tags=["自习室"])


class StartStudyRoomRequest(BaseModel):
    goal: str = Field(default="完成一次专注自习", max_length=80)
    planned_minutes: int = Field(default=45, ge=10, le=240)
    vlog_enabled: bool = Field(default=False)
    timelapse_interval_seconds: int = Field(default=5)
    timelapse_target_seconds: int | None = Field(default=None, ge=10, le=60)


class FinishStudyRoomRequest(BaseModel):
    client_elapsed_seconds: int = Field(default=0, ge=0)


@router.post("/sessions/start")
async def start_study_room_session(
    data: StartStudyRoomRequest = Body(...),
    user_id: int = Depends(get_user_id_from_token),
):
    """开始一次自习室会话。"""
    result = await StudyRoomService.start_session(
        user_id=user_id,
        goal=data.goal,
        planned_minutes=data.planned_minutes,
        vlog_enabled=data.vlog_enabled,
        timelapse_interval_seconds=data.timelapse_interval_seconds,
        timelapse_target_seconds=data.timelapse_target_seconds,
    )
    return {"code": 200, "msg": "success", "data": result}


@router.post("/sessions/{session_id}/frame")
async def upload_study_room_frame(
    session_id: str,
    frame: UploadFile = File(...),
    client_elapsed_seconds: int = Form(0),
    save_for_vlog: bool = Form(False),
    user_id: int = Depends(get_user_id_from_token),
):
    """上传一帧摄像头图片并返回当前监督状态。"""
    try:
        result = await StudyRoomService.process_frame(
            user_id=user_id,
            session_key=session_id,
            frame=frame,
            client_elapsed_seconds=client_elapsed_seconds,
            save_for_vlog=save_for_vlog,
        )
        return {"code": 200, "msg": "success", "data": result}
    except StudyRoomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{session_id}")
async def get_study_room_session(
    session_id: str,
    user_id: int = Depends(get_user_id_from_token),
):
    """查询自习室会话详情。"""
    try:
        result = await StudyRoomService.get_session(user_id=user_id, session_key=session_id)
        return {"code": 200, "msg": "success", "data": result}
    except StudyRoomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/finish")
async def finish_study_room_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    data: FinishStudyRoomRequest | None = Body(default=None),
    user_id: int = Depends(get_user_id_from_token),
):
    """结束一次自习室会话。"""
    try:
        result = await StudyRoomService.finish_session(
            user_id=user_id,
            session_key=session_id,
            client_elapsed_seconds=data.client_elapsed_seconds if data else 0,
        )
        if result.get("timelapse", {}).get("status") == "generating":
            background_tasks.add_task(StudyRoomService.generate_timelapse_for_session, user_id, session_id)
        return {"code": 200, "msg": "success", "data": result}
    except StudyRoomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/timelapse")
async def get_study_room_timelapse(
    session_id: str,
    user_id: int = Depends(get_user_id_from_token),
):
    """查询延时摄影状态。"""
    try:
        result = await StudyRoomService.get_timelapse(user_id=user_id, session_key=session_id)
        return {"code": 200, "msg": "success", "data": result}
    except StudyRoomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}/timelapse")
async def delete_study_room_timelapse(
    session_id: str,
    user_id: int = Depends(get_user_id_from_token),
):
    """删除延时摄影成片和原始抽帧。"""
    try:
        await StudyRoomService.delete_timelapse(user_id=user_id, session_key=session_id)
        return {"code": 200, "msg": "已删除"}
    except StudyRoomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

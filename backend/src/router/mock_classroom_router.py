"""Mock classroom API."""

import os

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.src.service.mock_classroom.service import MockClassroomNotFound, MockClassroomService
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/mock-classroom", tags=["模拟课堂"])


async def get_mock_classroom_user_id(
    authorization: str | None = Header(None, alias="Authorization"),
    token: str | None = Header(None),
) -> int:
    try:
        return get_user_id_from_token(authorization=authorization, token=token)
    except HTTPException as exc:
        debug_enabled = os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        if not debug_enabled:
            raise exc

        user_id = int(os.getenv("MOCK_CLASSROOM_DEBUG_USER_ID", "1"))
        from backend.src.models.usermodel import User

        await User.get_or_create(
            id=user_id,
            defaults={
                "username": f"mock_classroom_debug_{user_id}",
                "password": "",
                "role": "user",
            },
        )
        return user_id


class StartMockClassroomRequest(BaseModel):
    topic: str = Field(default="完成一次模拟讲课", max_length=128)
    planned_minutes: int = Field(default=5, ge=3, le=30)


class FinishMockClassroomRequest(BaseModel):
    client_elapsed_seconds: int = Field(default=0, ge=0)


@router.post("/sessions/start")
async def start_mock_classroom_session(
    data: StartMockClassroomRequest = Body(...),
    user_id: int = Depends(get_mock_classroom_user_id),
):
    result = await MockClassroomService.start_session(
        user_id=user_id,
        topic=data.topic,
        planned_minutes=data.planned_minutes,
    )
    return {"code": 200, "msg": "success", "data": result}


@router.post("/sessions/{session_id}/frame")
async def upload_mock_classroom_frame(
    session_id: str,
    frame: UploadFile = File(...),
    client_elapsed_seconds: int = Form(0),
    user_id: int = Depends(get_mock_classroom_user_id),
):
    try:
        result = await MockClassroomService.process_frame(
            user_id=user_id,
            session_key=session_id,
            frame=frame,
            client_elapsed_seconds=client_elapsed_seconds,
        )
        return {"code": 200, "msg": "success", "data": result}
    except MockClassroomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/audio")
async def upload_mock_classroom_audio(
    session_id: str,
    audio: UploadFile = File(...),
    client_elapsed_seconds: int = Form(0),
    user_id: int = Depends(get_mock_classroom_user_id),
):
    try:
        result = await MockClassroomService.upload_audio(
            user_id=user_id,
            session_key=session_id,
            audio=audio,
            client_elapsed_seconds=client_elapsed_seconds,
        )
        return {"code": 200, "msg": "success", "data": result}
    except MockClassroomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/finish")
async def finish_mock_classroom_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    data: FinishMockClassroomRequest | None = Body(default=None),
    user_id: int = Depends(get_mock_classroom_user_id),
):
    try:
        result = await MockClassroomService.finish_session(
            user_id=user_id,
            session_key=session_id,
            client_elapsed_seconds=data.client_elapsed_seconds if data else 0,
        )
        if result.get("report_status") == "generating":
            background_tasks.add_task(MockClassroomService.generate_report_for_session, user_id, session_id)
        return {"code": 200, "msg": "success", "data": result}
    except MockClassroomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/report")
async def get_mock_classroom_report(
    session_id: str,
    user_id: int = Depends(get_mock_classroom_user_id),
):
    try:
        result = await MockClassroomService.get_report(user_id=user_id, session_key=session_id)
        return {"code": 200, "msg": "success", "data": result}
    except MockClassroomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}/media")
async def delete_mock_classroom_media(
    session_id: str,
    user_id: int = Depends(get_mock_classroom_user_id),
):
    try:
        await MockClassroomService.delete_media(user_id=user_id, session_key=session_id)
        return {"code": 200, "msg": "已删除"}
    except MockClassroomNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

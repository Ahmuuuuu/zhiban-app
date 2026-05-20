from fastapi import APIRouter, HTTPException, Depends, Body, Query
from fastapi.responses import StreamingResponse
from backend.src.service.chat_service import ChatService
from backend.src.schemas.chat import CreateNewHistory, CreateMsgIntoHistory, StreamNewHistory, StreamMsgIntoHistory
from backend.src.utils.jwt import create_access_token, get_user_id_from_token

router = APIRouter(prefix="/ai_chat", tags=["AI 聊天"])


@router.post("/create_new_history")
async def new_history(
    user_id: int = Depends(get_user_id_from_token),
    data: CreateNewHistory = Body(...)
):
    try:
        message, msg = await ChatService.create_new_history(user_id, data.user_req)
        if message is None:
            return {"code": 404, "msg": msg}
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "user_id": create_access_token(message.user_id),
                "chat_group_id": message.chat_group_id,
            },
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.post("/create_msg_into_history")
async def new_message(
    user_id: int = Depends(get_user_id_from_token),
    data: CreateMsgIntoHistory = Body(...)
):
    try:
        message, msg = await ChatService.create_message_into_history(
            user_id, data.chat_group_id, data.user_req
        )
        if message is None:
            return {"code": 404, "msg": msg}
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "user_id": create_access_token(user_id),
                "chat_group_id": data.chat_group_id,
            },
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.get("/read_history_group")
async def read_history(user_id: int = Depends(get_user_id_from_token)):
    try:
        history, msg = await ChatService.read_history(user_id)
        return {"code": 200, "msg": msg, "data": history}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.get("/read_messages_from_history")
async def read_messages(
    user_id: int = Depends(get_user_id_from_token),
    chat_group_id: int = Query(...)
):
    try:
        messages, msg = await ChatService.read_message(user_id, chat_group_id)
        return {"code": 200, "msg": msg, "data": messages}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.delete("/delete_history_group")
async def delete_history(
    user_id: int = Depends(get_user_id_from_token),
    chat_group_id: int = Query(...)
):
    try:
        user, group, msg = await ChatService.delete_history(user_id, chat_group_id)
        if user is None:
            return {"code": 404, "msg": msg}
        if group is None:
            return {"code": 404, "msg": msg}
        return {"code": 200, "msg": msg}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")


# ═══════════════════════════════════════
#  流式接口
# ═══════════════════════════════════════

@router.post("/stream_new_history")
async def stream_new_history(
    user_id: int = Depends(get_user_id_from_token),
    data: StreamNewHistory = Body(...)
):
    return StreamingResponse(
        ChatService.stream_create_new_history(user_id, data.user_req),
        media_type="text/event-stream",
    )


@router.post("/stream_msg_into_history")
async def stream_new_message(
    user_id: int = Depends(get_user_id_from_token),
    data: StreamMsgIntoHistory = Body(...)
):
    return StreamingResponse(
        ChatService.stream_create_message_into_history(
            user_id, data.chat_group_id, data.user_req
        ),
        media_type="text/event-stream",
    )

"""学习课件 HTML 生成路由 — CRUD + SSE 实时进度"""
import json
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.src.service.presentation_service import (
    generate,
    generate_questions,
    preview,
    get_presentation,
    list_presentations,
    delete_presentation,
    _subscribe_sse,
    _unsubscribe_sse,
)
from backend.src.utils.jwt import get_user_id_from_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/presentation", tags=["课件生成"])


class GenerateRequest(BaseModel):
    topic: str = Field(description="学习话题，必须已通过 /resource/generate 生成过资源")
    voice: str = Field(default="zh-CN-XiaoxiaoNeural", description="EdgeTTS 语音名称")
    chapters: list[str] | None = Field(default=None, description="要生成的章节列表，如 ['intro', 'ppt']，不传则全生成")
    answers: dict | None = Field(default=None, description="用户作答 {question_id: value}，用于裁剪内容")
    chat_group_id: int = Field(default=0, description="聊天组 ID，用于写入聊天历史")


class PreviewRequest(BaseModel):
    topic: str = Field(description="学习话题")


class QuestionsRequest(BaseModel):
    topic: str = Field(description="学习话题")
    chat_group_id: int = Field(default=0, description="聊天组 ID，用于写入聊天历史")


@router.post("/generate")
async def generate_presentation(data: GenerateRequest, user_id: int = Depends(get_user_id_from_token)):
    """生成动态 HTML 课件：学科介绍 → 思维导图 → PPT讲解 → EdgeTTS 配音"""
    result = await generate(data.topic, user_id, voice=data.voice, chapters=data.chapters, answers=data.answers, chat_group_id=data.chat_group_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 200, "msg": "success", "data": result}


@router.post("/questions")
async def get_questions(data: QuestionsRequest, user_id: int = Depends(get_user_id_from_token)):
    """AI 分析资源内容，返回 2-3 个选择题帮助用户聚焦课件方向"""
    result = await generate_questions(data.topic, user_id, chat_group_id=data.chat_group_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 200, "msg": "success", "data": result}


@router.get("/list")
async def list_presentation(user_id: int = Depends(get_user_id_from_token)):
    """列出当前用户的所有课件"""
    items = await list_presentations(user_id)
    return {"code": 200, "msg": "success", "data": items}


@router.get("/{presentation_id}")
async def get_presentation_detail(presentation_id: int, user_id: int = Depends(get_user_id_from_token)):
    """查询课件详情（含章节列表和状态）"""
    result = await get_presentation(presentation_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="课件不存在")
    return {"code": 200, "msg": "success", "data": result}


@router.post("/preview")
async def preview_presentation(data: PreviewRequest, user_id: int = Depends(get_user_id_from_token)):
    """预览话题的可用章节，供用户选择"""
    result = await preview(data.topic, user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 200, "msg": "success", "data": result}


@router.delete("/{presentation_id}")
async def delete_presentation_endpoint(presentation_id: int, user_id: int = Depends(get_user_id_from_token)):
    """删除课件"""
    ok = await delete_presentation(presentation_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="课件不存在")
    return {"code": 200, "msg": "success"}


@router.get("/{presentation_id}/sse")
async def presentation_sse(presentation_id: int, user_id: int = Depends(get_user_id_from_token)):
    """SSE 实时跟踪课件生成进度"""
    # 先校验课件存在
    result = await get_presentation(presentation_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="课件不存在")

    q = _subscribe_sse(presentation_id)

    async def event_stream():
        try:
            # 先发当前状态
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
            # 如果已完结则不再等待
            if result["status"] in ("ready", "failed"):
                return

            while True:
                try:
                    msg = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, lambda: q.pop(0) if q else None),
                        timeout=30,
                    )
                    if msg is None:
                        continue
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    if msg.get("status") in ("ready", "failed"):
                        return
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'status': 'keepalive'}, ensure_ascii=False)}\n\n"
        finally:
            _unsubscribe_sse(presentation_id, q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

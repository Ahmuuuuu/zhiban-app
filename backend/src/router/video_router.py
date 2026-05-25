"""视频/语音旁白路由"""

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from backend.src.service.narration_service import narrate_resource
from backend.src.utils.tts_utils import VOICES
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/video", tags=["视频生成"])


class NarrateRequest(BaseModel):
    resource_id: int = Field(description="PPT 资源的 ID")
    voice: str = Field(default="zh-CN-XiaoxiaoNeural", description="EdgeTTS 语音名称")


@router.post("/narrate")
async def narrate_ppt(data: NarrateRequest, user_id: int = Depends(get_user_id_from_token)):
    """对 PPT 资源逐页生成旁白语音，返回每页的音频 URL"""
    result = await narrate_resource(data.resource_id, data.voice)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 200, "msg": "success", "data": result}


@router.get("/voices")
async def list_voices():
    """列出可用的 EdgeTTS 中文语音"""
    return {"code": 200, "msg": "success", "data": VOICES}

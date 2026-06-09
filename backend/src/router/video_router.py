"""视频/语音旁白路由 — 支持 ppt/document/case/reading/mindmap 文字类资源 CRUD"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.src.service.narration_service import narrate_resource, list_narrations, get_narration, delete_narration
from backend.src.utils.tts_utils import VOICES, NARRATABLE_TYPES
from backend.src.utils.jwt import get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["视频生成"])


class NarrateRequest(BaseModel):
    resource_id: int = Field(description="文字类资源的 ID")
    voice: str = Field(default="zh-CN-XiaoxiaoNeural", description="EdgeTTS 语音名称")
    force_regenerate: bool = Field(default=False, description="是否强制重新生成")


@router.post("/narrate")
async def narrate_resource_endpoint(data: NarrateRequest, user_id: int = Depends(get_user_id_from_token)):
    """对文字类资源逐段生成旁白语音"""
    result = await narrate_resource(data.resource_id, data.voice, force_regenerate=data.force_regenerate)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/narrations")
async def list_all_narrations(user_id: int = Depends(get_user_id_from_token)):
    """列出当前用户的所有旁白记录"""
    result = await list_narrations(user_id)
    return {"code": 200, "msg": "success", "data": result}


@router.get("/narrations/{narration_id}")
async def get_narration_detail(narration_id: int, user_id: int = Depends(get_user_id_from_token)):
    """获取单个旁白详情（含每段音频）"""
    result = await get_narration(narration_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="旁白记录不存在")
    return {"code": 200, "msg": "success", "data": result}


@router.delete("/narrations/{narration_id}")
async def delete_narration_record(narration_id: int, user_id: int = Depends(get_user_id_from_token)):
    """删除旁白记录及音频文件"""
    ok = await delete_narration(narration_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="旁白记录不存在")
    return {"code": 200, "msg": "已删除"}


@router.get("/narratable-types")
async def list_narratable_types():
    """列出支持旁白生成的资源类型"""
    return {"code": 200, "msg": "success", "data": sorted(NARRATABLE_TYPES)}


@router.get("/voices")
async def list_voices():
    """列出可用的 EdgeTTS 中文语音"""
    return {"code": 200, "msg": "success", "data": VOICES}

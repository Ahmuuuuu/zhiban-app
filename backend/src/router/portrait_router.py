import logging

from fastapi import APIRouter, HTTPException, Depends, Body
from backend.src.service.portrait_service import PortraitChatHistory_Service
from backend.src.schemas.portrait import Init_Portrait
from backend.src.utils.jwt import create_access_token, get_user_id_from_token

router = APIRouter(prefix="/ai_portrait", tags=["AI人设（仅初始化/读取）"])


# ═══════════════════════════════════════
#  画像初始化（弹窗数据接收）
# ═══════════════════════════════════════

@router.post("/init_portrait")
async def init_portrait(
    user_id: int = Depends(get_user_id_from_token),
    data: Init_Portrait = Body(...)
):
    try:
        user, msg = await PortraitChatHistory_Service.init_portrait(
            user_id, data.cognition, data.learning_goal, data.personality_tags
        )
        if user is None:
            return {"code": 404, "msg": msg}
        return {
            "code": 200,
            "msg": msg,
            "data": {
                "user_id": create_access_token(user.id),
            },
        }
    except HTTPException:
        raise
    except Exception as error:
        logging.getLogger(__name__).exception("读取画像失败")
        raise HTTPException(500, f"服务器错误: {type(error).__name__}: {error}")


@router.get("/read_portrait")
async def read_portrait(user_id: int = Depends(get_user_id_from_token)):
    try:
        data, msg = await PortraitChatHistory_Service.read_portrait(user_id)
        if data is None:
            return {"code": 404, "msg": msg}
        return {"code": 200, "msg": msg, "data": data}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.post("/regenerate")
async def regenerate_portrait(user_id: int = Depends(get_user_id_from_token)):
    """调用 LLM 重新生成画像摘要 + 推断认知风格/学习目标"""
    try:
        data = await PortraitChatHistory_Service.regenerate_portrait(user_id)
        return {"code": 200, "msg": "画像已更新", "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("画像再生失败")
        raise HTTPException(500, "服务器错误")

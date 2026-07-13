import logging

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import List
from backend.src.service.portrait.service import PortraitChatHistory_Service, PortraitRadarService
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


# ═══════════════════════════════════════
#  对话问答画像初始化
# ═══════════════════════════════════════

class DialogueTurn(BaseModel):
    question: str = ""
    answer: str = ""


class InitFromDialogueRequest(BaseModel):
    dialogue: List[DialogueTurn]


@router.post("/init_from_dialogue")
async def init_from_dialogue(
    user_id: int = Depends(get_user_id_from_token),
    data: InitFromDialogueRequest = Body(...),
):
    """通过多轮自然语言问答让 LLM 提取用户画像（替代标签选择）"""
    try:
        result = await PortraitChatHistory_Service.init_from_dialogue(
            user_id,
            [{"question": t.question, "answer": t.answer} for t in data.dialogue],
        )
        return {"code": 200, "msg": "画像初始化成功", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("对话画像初始化失败 user_id=%s", user_id)
        raise HTTPException(500, "服务器错误")


# ═══════════════════════════════════════
#  六维雷达
# ═══════════════════════════════════════

@router.get("/radar")
async def get_radar(user_id: int = Depends(get_user_id_from_token)):
    """获取六维雷达数据，无则自动计算"""
    try:
        radar = await PortraitRadarService.get(user_id)
        if not radar:
            return {"code": 404, "msg": "暂无答题数据，无法生成雷达图"}
        return {"code": 200, "msg": "success", "data": radar}
    except Exception:
        logging.getLogger(__name__).exception("雷达获取失败")
        raise HTTPException(500, "服务器错误")


@router.post("/radar/refresh")
async def refresh_radar(user_id: int = Depends(get_user_id_from_token)):
    """强制重算六维雷达数据"""
    try:
        radar = await PortraitRadarService.compute(user_id)
        try:
            await PortraitRadarService.sync_to_portrait(user_id)
        except Exception:
            logging.getLogger(__name__).exception("雷达同步画像失败 user_id=%s", user_id)
        return {"code": 200, "msg": "雷达数据已刷新", "data": radar}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logging.getLogger(__name__).exception("雷达刷新失败")
        raise HTTPException(500, "服务器错误")

import json
from backend.src.models.usermodel import User
from backend.src.models.portraitmodel import User_picture
from backend.src.utils.portrait_utils import parse_traits


class PortraitChatHistory_Service:

    # ═══════════════════════════════════════
    #  画像初始化
    # ═══════════════════════════════════════

    @staticmethod
    async def init_portrait(user_id: int, cognition: str | None,
                            learning_goal: str | None, personality_tags: str | None):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "未查找到该用户"

        picture = None
        picture_id = getattr(user, "picture_id", None)

        if picture_id:
            picture = await User_picture.filter(id=picture_id).first()

        if not picture:
            try:
                picture = await user.picture
            except Exception:
                picture = None
        if not picture:
            picture = await User_picture.create()
            user.picture = picture
            await user.save()

        if cognition:
            picture.cognition = cognition
        if learning_goal:
            picture.learning_goal = learning_goal
        if personality_tags is not None:
            if isinstance(personality_tags, list):
                picture.personality_tags = json.dumps(personality_tags, ensure_ascii=False)
            else:
                picture.personality_tags = personality_tags

        await picture.save()
        return user, "画像初始化成功"

    # ═══════════════════════════════════════
    #  画像读取
    # ═══════════════════════════════════════

    @staticmethod
    async def read_portrait(user_id: int):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "未查找到该用户"

        picture = await user.picture
        if not picture:
            return None, "该用户暂无画像"

        data = {
            "cognition": picture.cognition,
            "learning_goal": picture.learning_goal,
            "personality_tags": picture.personality_tags,
            "traits": parse_traits(picture.traits),
            "profile_summary": picture.profile_summary,
        }
        return data, "获取画像成功"

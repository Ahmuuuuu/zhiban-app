"""用户画像工具"""

from backend.src.utils.database import init_db
from backend.src.service.portrait_service import (
    TRAIT_KEYS, format_portrait,
    parse_traits, dump_traits, build_trait_entry,
)
from backend.src.models.usermodel import User
from langchain_core.tools import tool


@tool
async def read_portrait(user_id: str, show_missing: bool = False):
    """获取用户完整画像。参数：user_id用户数字ID，show_missing是否显示待补充维度（默认False）"""
    try:
        await init_db()
        user = await User.filter(id=int(user_id.strip())).first()
        if not user:
            return "未查找到该用户"
        picture = await user.picture
        if not picture:
            return "该用户尚未创建画像"
        return "\n".join(format_portrait(picture, show_missing=show_missing))
    except Exception as e:
        return f"获取画像失败：{e}"


PICTURE_FIELDS = {"cognition", "learning_goal"}

VALID_COGNITION = {"visual", "auditory", "read-write", "practical"}
VALID_LEARNING_GOAL = {"exam", "competition", "certification", "interest", "job"}


@tool
async def update_portrait(user_id: str, field: str, value: str, source: str = "user_stated"):
    """更新用户画像的指定维度，自动计算置信度。参数: user_id用户数字ID, field维度名(可用TRAIT_KEYS或cognition/learning_goal), value维度值, source来源类型"""
    try:
        await init_db()
        user_id_int = int(user_id.strip())

        user = await User.filter(id=user_id_int).first()
        if not user:
            return "未查找到该用户"
        picture = await user.picture
        if not picture:
            return "该用户尚未创建画像"

        # 画像表级字段 (cognition / learning_goal)
        if field in PICTURE_FIELDS:
            if field == "cognition" and value not in VALID_COGNITION:
                return f"cognition 值无效，可选：{', '.join(sorted(VALID_COGNITION))}"
            if field == "learning_goal" and value not in VALID_LEARNING_GOAL:
                return f"learning_goal 值无效，可选：{', '.join(sorted(VALID_LEARNING_GOAL))}"
            setattr(picture, field, value)
            await picture.save()
            return f"画像字段 '{field}' 已更新为 '{value}'（来源：{source}）"

        # traits JSON 维度
        if field not in TRAIT_KEYS:
            return f"未知维度 '{field}'，可选：{', '.join(sorted(TRAIT_KEYS) | sorted(PICTURE_FIELDS))}"
        traits = parse_traits(picture.traits)
        existing = traits.get(field) if isinstance(traits.get(field), dict) else None
        traits[field] = build_trait_entry(value, source, existing)
        picture.traits = dump_traits(traits)
        await picture.save()
        entry = traits[field]
        return f"维度 '{field}' 已更新：{value}，置信度 {entry['confidence']}（来源：{source}）"
    except Exception as e:
        return f"更新画像失败：{e}"

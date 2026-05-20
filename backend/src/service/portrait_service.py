"""画像服务 — 初始化、读取、格式化、置信度计算"""

import json
from backend.src.models.usermodel import User
from backend.src.models.portraitmodel import User_picture

# ═══════════════════════════════════════
#  维度与标签映射（原 portrait_utils）
# ═══════════════════════════════════════

TRAIT_KEYS = [
    "knowbase",
    "commonmis",
    "learning_pace",
    "interest",
    "strengths",
    "weaknesses",
]

LABEL_MAP = {
    "knowbase":      "知识掌握程度(1-5)",
    "commonmis":     "易错点",
    "learning_pace": "学习节奏偏好",
    "interest":      "兴趣方向",
    "strengths":     "学习强项",
    "weaknesses":    "学习弱项",
}

CONFIDENCE_FLOOR = {"popup": 0.75, "user_stated": 0.65, "agent_inferred": 0.30}
CONFIDENCE_CEIL  = {"popup": 0.95, "user_stated": 0.95, "agent_inferred": 0.60}
CONFIDENCE_BOOST = {"popup": 0.08, "user_stated": 0.10, "agent_inferred": 0.10}
CONFIDENCE_MAX = 0.95


def parse_traits(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def dump_traits(traits: dict) -> str:
    return json.dumps(traits, ensure_ascii=False)


def trait_display(traits: dict, key: str) -> str | None:
    data = traits.get(key)
    if data is None:
        return None
    if isinstance(data, dict):
        return data.get("value", "")
    return str(data)


def trait_confident(traits: dict, key: str) -> bool:
    data = traits.get(key)
    if not isinstance(data, dict):
        return False
    return data.get("confidence", 0) >= CONFIDENCE_MAX


def build_trait_entry(value: str, source: str, existing: dict | None = None) -> dict:
    old_conf = existing.get("confidence", 0) if existing else 0
    old_source = existing.get("source", "")    if existing else ""

    floor = CONFIDENCE_FLOOR.get(source, 0.30)
    boost = CONFIDENCE_BOOST.get(source, 0.10)
    ceil  = CONFIDENCE_CEIL.get(source, 0.95)

    if source == old_source:
        new_conf = min(ceil, max(old_conf, floor) + boost)
    else:
        new_conf = min(ceil, max(old_conf, floor))

    return {
        "value": value,
        "confidence": round(new_conf, 2),
        "source": source,
    }


def _unpack(data) -> tuple:
    if isinstance(data, dict):
        return data.get("value"), data.get("confidence", 0)
    return data, 0


def format_portrait(picture, show_missing: bool = False) -> list[str]:
    lines = ["【用户画像】"]

    if picture.cognition:
        lines.append(f"认知风格：{picture.cognition}")
    if picture.learning_goal:
        lines.append(f"学习目标：{picture.learning_goal}")
    if picture.personality_tags:
        try:
            tags = json.loads(picture.personality_tags)
            lines.append(f"性格标签：{'、'.join(tags)}")
        except (json.JSONDecodeError, TypeError):
            lines.append(f"性格标签：{picture.personality_tags}")

    traits = parse_traits(picture.traits)
    filled_keys = []
    for key in TRAIT_KEYS:
        data = traits.get(key)
        if not data:
            continue
        val, conf = _unpack(data)
        if val is None or val == "":
            continue
        filled_keys.append(key)
        label = LABEL_MAP.get(key, key)
        marker = " ✓" if conf >= CONFIDENCE_MAX else ""
        lines.append(f"{label}：{val}（置信度 {conf}）{marker}")

    if picture.profile_summary:
        lines.append(f"画像总结：{picture.profile_summary}")

    if show_missing:
        missing = [k for k in TRAIT_KEYS if k not in filled_keys]
        if missing:
            lines.append(f"\n【待补充维度】：{'、'.join(missing)}")
        else:
            lines.append("\n【画像状态】：全部维度已完善")

    return lines


# ═══════════════════════════════════════
#  Service 方法
# ═══════════════════════════════════════

class PortraitChatHistory_Service:

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

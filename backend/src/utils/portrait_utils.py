"""
画像共享工具 — 解析、格式化、置信度计算。
dailychat 和 portrait 两个 agent 共用，避免重复代码。
"""

import json

# ── 维度与标签映射 ──
TRAIT_KEYS = [
    "knowbase",       # 知识掌握程度 1-5
    "commonmis",      # 易错点
    "learning_pace",  # 学习节奏偏好
    "interest",       # 兴趣方向
    "strengths",      # 学习强项
    "weaknesses",     # 学习弱项
]

LABEL_MAP = {
    "knowbase":      "知识掌握程度(1-5)",
    "commonmis":     "易错点",
    "learning_pace": "学习节奏偏好",
    "interest":      "兴趣方向",
    "strengths":     "学习强项",
    "weaknesses":    "学习弱项",
}


# ── 置信度规则 ──
CONFIDENCE_FLOOR = {"popup": 0.75, "user_stated": 0.65, "agent_inferred": 0.30}
CONFIDENCE_CEIL  = {"popup": 0.95, "user_stated": 0.95, "agent_inferred": 0.60}
CONFIDENCE_BOOST = {"popup": 0.08, "user_stated": 0.10, "agent_inferred": 0.10}

# 总上限
CONFIDENCE_MAX = 0.95

# trait 的 JSON 结构：{ "value": ..., "confidence": 0.x, "source": "..." }


def parse_traits(raw: str | None) -> dict:
    """安全解析 traits JSON，失败返回 {}"""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def dump_traits(traits: dict) -> str:
    return json.dumps(traits, ensure_ascii=False)


def trait_display(traits: dict, key: str) -> str | None:
    """读取单个维度的展示值（仅 value 部分，不含元数据）"""
    data = traits.get(key)
    if data is None:
        return None
    if isinstance(data, dict):
        return data.get("value", "")
    return str(data)


def trait_confident(traits: dict, key: str) -> bool:
    """该维度是否已经达到 0.95"""
    data = traits.get(key)
    if not isinstance(data, dict):
        return False
    return data.get("confidence", 0) >= CONFIDENCE_MAX


def build_trait_entry(value: str, source: str, existing: dict | None = None) -> dict:
    """
    构造或更新单维度的 {'value', 'confidence', 'source'}。
    existing 为旧数据（可能为空）。
    """
    old_conf = existing.get("confidence", 0) if existing else 0
    old_source = existing.get("source", "")    if existing else ""

    floor = CONFIDENCE_FLOOR.get(source, 0.30)
    boost = CONFIDENCE_BOOST.get(source, 0.10)
    ceil  = CONFIDENCE_CEIL.get(source, 0.95)

    # 如果来源相同则累加；不同来源取较高者
    if source == old_source:
        new_conf = min(ceil, max(old_conf, floor) + boost)
    else:
        new_conf = min(ceil, max(old_conf, floor))

    return {
        "value": value,
        "confidence": round(new_conf, 2),
        "source": source,
    }


def format_portrait(picture, show_missing: bool = False) -> list[str]:
    """
    把 User_picture 对象格式化成行列表。
    show_missing=True 时额外输出【待补充维度】。
    """
    lines = ["【用户画像】"]

    # 弹窗标签
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

    # AI 动态画像
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

    # 画像摘要
    if picture.profile_summary:
        lines.append(f"画像总结：{picture.profile_summary}")

    if show_missing:
        missing = [k for k in TRAIT_KEYS if k not in filled_keys]
        if missing:
            lines.append(f"\n【待补充维度】：{'、'.join(missing)}")
        else:
            lines.append("\n【画像状态】：全部维度已完善")

    return lines


def _unpack(data) -> tuple:
    """从 traits[key] 中取出 (value, confidence)"""
    if isinstance(data, dict):
        return data.get("value"), data.get("confidence", 0)
    return data, 0

"""画像服务 — 初始化、读取、格式化、置信度计算、再生"""

import json
import logging
from backend.src.models.usermodel import User
from backend.src.models.portraitmodel import User_picture

logger = logging.getLogger(__name__)

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


def format_portrait(picture, show_missing: bool = False, radar_data: dict | None = None) -> list[str]:
    lines = ["【用户画像】"]

    # 六维雷达（如有）
    if radar_data and radar_data.get("dimensions"):
        lines.append(PortraitRadarService.format_for_prompt(radar_data))

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

    # 知识点掌握度（给智能体出题/推荐用）
    mastery = traits.get("knowledge_mastery")
    if mastery and isinstance(mastery, list) and len(mastery) > 0:
        lines.append("\n【知识点掌握度】")
        for m in mastery:
            level_cn = {"beginner": "入门", "learning": "学习中", "proficient": "熟练", "mastered": "已掌握"}.get(m.get("level"), m.get("level"))
            lines.append(f"  - {m.get('tag')}：{level_cn}（正确率 {m.get('accuracy', 0)}）")

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

    @staticmethod
    async def regenerate_portrait(user_id: int) -> dict:
        """调用 LLM 生成画像自然语言摘要，并推断认知风格/学习目标"""
        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")
        picture = await user.picture
        if not picture:
            raise ValueError("画像不存在，请先初始化")

        portrait_lines = format_portrait(picture, show_missing=True)
        portrait_text = "\n".join(portrait_lines)

        from backend.src.ai_core.llm_config import llm

        prompt = f"""你是一个学习画像分析师。根据以下用户画像数据，完成两件事：

1. 用一段流畅的中文（80-150字）总结该学习者的整体情况，包括知识水平、学习特点、待提升方向。
2. 推断最可能的学习目标(learning_goal)：exam/competition/certification/interest/job 之一。
3. 推断最可能的认知风格(cognition)：visual/auditory/read-write/practical 之一。

{portrait_text}

请严格按JSON格式输出，不要加任何额外文字：
{{"profile_summary": "...", "learning_goal": "...", "cognition": "..."}}"""

        try:
            response = await llm.ainvoke(prompt)
            raw = response.content.strip()
            from backend.src.utils.json_parser import parse_llm_json
            result = parse_llm_json(raw)
        except Exception:
            logger.exception("LLM 画像摘要生成失败 user_id=%s", user_id)
            raise RuntimeError("画像摘要生成失败，请稍后重试")

        summary = result.get("profile_summary", "")
        learning_goal = result.get("learning_goal", "")
        cognition = result.get("cognition", "")

        if summary:
            picture.profile_summary = summary
        if learning_goal and not picture.learning_goal:
            picture.learning_goal = learning_goal
        if cognition and not picture.cognition:
            picture.cognition = cognition
        await picture.save()

        data = {
            "cognition": picture.cognition,
            "learning_goal": picture.learning_goal,
            "personality_tags": picture.personality_tags,
            "traits": parse_traits(picture.traits),
            "profile_summary": picture.profile_summary,
        }
        return data


# ═══════════════════════════════════════
#  六维雷达 Service
# ═══════════════════════════════════════

RADAR_DIMENSIONS = [
    {"key": "memory",        "label": "记忆",   "desc": "easy 难度题目正确率"},
    {"key": "understanding", "label": "理解",   "desc": "medium 难度题目正确率"},
    {"key": "application",   "label": "应用",   "desc": "hard 难度题目正确率"},
    {"key": "analysis",      "label": "分析",   "desc": "多选题正确率"},
    {"key": "breadth",       "label": "广度",   "desc": "已覆盖知识标签种类数"},
    {"key": "persistence",   "label": "坚持",   "desc": "近 30 天活跃天数占比"},
]


class PortraitRadarService:

    @staticmethod
    async def compute(user_id: int) -> dict:
        """从答题数据实时计算六维雷达分数并写入 PortraitRadar 表"""
        from datetime import datetime, timedelta
        from backend.src.models.exam_model import ExamRecord, ExamQuestion, KnowledgeMastery
        from backend.src.models.portrait_radar_model import PortraitRadar

        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # 所有已判分的答题记录（join 题目表拿 difficulty/question_type）
        records = await ExamRecord.filter(
            user_id=user_id, is_correct__not_isnull=True
        ).prefetch_related("question").all()

        def _accuracy(questions) -> int:
            """给定题目列表，算正确率百分比整数"""
            if not questions:
                return 0
            scored = [(r.is_correct, r.question) for r in records if r.question in questions]
            if not scored:
                return 0
            correct = sum(1 for ok, _ in scored if ok)
            return round(correct / len(scored) * 100)

        # 按难度分组
        easy_qs = [r.question for r in records if r.question and r.question.difficulty == "easy"]
        medium_qs = [r.question for r in records if r.question and r.question.difficulty == "medium"]
        hard_qs = [r.question for r in records if r.question and r.question.difficulty == "hard"]

        memory = _accuracy(easy_qs)
        understanding = _accuracy(medium_qs)
        application = _accuracy(hard_qs)

        # 分析 — multi_choice 题型正确率
        multi_qs = [r.question for r in records if r.question and r.question.question_type == "multi_choice"]
        analysis = _accuracy(multi_qs)

        # 广度 — 已覆盖知识标签种类数（上限 20 种 = 100 分）
        mastery_records = await KnowledgeMastery.filter(user_id=user_id).all()
        tag_count = len(mastery_records)
        breadth = min(100, round(tag_count / 20 * 100))

        # 坚持 — 近 30 天活跃天数占比
        from datetime import timezone as tz
        cutoff = datetime.now(tz.utc) - timedelta(days=30)
        recent_dates = set()
        for r in records:
            ct = r.created_at
            if not ct:
                continue
            if ct.tzinfo is None:
                ct = ct.replace(tzinfo=tz.utc)
            if ct >= cutoff:
                recent_dates.add(ct.date())
        persistence = min(100, round(len(recent_dates) / 30 * 100))

        # 写入/更新 Radar 表
        radar, _ = await PortraitRadar.get_or_create(user=user)
        radar.memory = memory
        radar.understanding = understanding
        radar.application = application
        radar.analysis = analysis
        radar.breadth = breadth
        radar.persistence = persistence
        await radar.save()

        return PortraitRadarService._format(radar)

    @staticmethod
    async def get(user_id: int) -> dict | None:
        """获取最新雷达数据，不存在则自动计算"""
        from backend.src.models.portrait_radar_model import PortraitRadar

        radar = await PortraitRadar.filter(user_id=user_id).first()
        if not radar:
            try:
                return await PortraitRadarService.compute(user_id)
            except ValueError:
                return None
        return PortraitRadarService._format(radar)

    @staticmethod
    def _format(radar) -> dict:
        return {
            "radar_id": radar.id,
            "user_id": radar.user_id,
            "dimensions": [
                {"key": "memory",        "label": "记忆",   "score": radar.memory,        "desc": "简单题正确率"},
                {"key": "understanding", "label": "理解",   "score": radar.understanding, "desc": "中等题正确率"},
                {"key": "application",   "label": "应用",   "score": radar.application,   "desc": "困难题正确率"},
                {"key": "analysis",      "label": "分析",   "score": radar.analysis,      "desc": "多选题正确率"},
                {"key": "breadth",       "label": "广度",   "score": radar.breadth,       "desc": "知识标签覆盖度"},
                {"key": "persistence",   "label": "坚持",   "score": radar.persistence,   "desc": "近30天活跃度"},
            ],
            "updated_at": str(radar.updated_at),
        }

    @staticmethod
    def format_for_prompt(radar: dict) -> str:
        """格式化为 agent prompt 可用的文本"""
        if not radar or not radar.get("dimensions"):
            return "暂无六维雷达数据"
        lines = ["【六维能力雷达】"]
        for d in radar["dimensions"]:
            bar = "█" * (d["score"] // 10) + "░" * (10 - d["score"] // 10)
            lines.append(f"  {d['label']}：{bar} {d['score']}")
        return "\n".join(lines)

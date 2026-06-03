"""课程体系服务 — 专业×年级 → 核心课程（查表 + LLM 回退）"""

import json
import logging

from backend.src.models.curriculum_model import CurriculumCourse

logger = logging.getLogger(__name__)

# 年级策略：(查询优先级, 总上限)
_GRADE_CONFIG = {
    "大一": (["大一", "大二"], 7),
    "大二": (["大二", "大一"], 7),
    "大三": (["大三", "大二", "大一"], 7),
    "大四": (["大四", "大三", "大二"], 7),
}
_DEFAULT = (["大一", "大二"], 7)


async def get_courses(major: str, grade: str) -> list[str]:
    """查表获取课程，未命中则走 LLM 推理写入"""
    if not major:
        return []
    grade_priority, total_limit = _GRADE_CONFIG.get(grade, _DEFAULT)
    courses = await _query_from_db(major, grade_priority, total_limit)
    if courses:
        return courses
    courses = await _infer_by_llm(major, grade, grade_priority, total_limit)
    return courses


async def sync_to_portrait(user_id: int, major: str, grade: str) -> list[str] | None:
    """同步课程到用户画像 traits.curriculum_courses"""
    courses = await get_courses(major, grade)
    if not courses:
        return None

    from backend.src.models.usermodel import User
    from backend.src.models.portraitmodel import User_picture
    from backend.src.service.portrait_service import parse_traits, dump_traits

    user = await User.filter(id=user_id).first()
    if not user:
        return None
    picture = await user.picture
    if not picture:
        picture = await User_picture.create()
        user.picture = picture
        await user.save()

    traits = parse_traits(picture.traits)
    traits["curriculum_courses"] = courses
    traits["curriculum_major"] = major
    traits["curriculum_grade"] = grade
    picture.traits = dump_traits(traits)
    await picture.save()
    return courses


async def _query_from_db(major: str, grade_priority: list[str], total_limit: int) -> list[str]:
    """按年级优先级从表查询课程，上限 total_limit 门"""
    result: list[str] = []
    seen: set[str] = set()
    for g in grade_priority:
        if len(result) >= total_limit:
            break
        row = await CurriculumCourse.filter(major=major, grade=g).first()
        if not row:
            continue
        try:
            grade_courses = json.loads(row.courses)
        except (json.JSONDecodeError, TypeError):
            continue
        for c in grade_courses:
            if c not in seen and len(result) < total_limit:
                seen.add(c)
                result.append(c)
    return result


async def _infer_by_llm(major: str, grade: str, grade_priority: list[str], total_limit: int) -> list[str]:
    """LLM 按年级推理课程并写入表，失败返回空列表"""
    from backend.src.ai_core.llm_config import llm

    try:
        resp = await llm.ainvoke(
            f"你是一位大学教务老师。请列出「{major}」专业以下年级的核心课程：{'、'.join(grade_priority)}。\n"
            f"要求：每个年级列出该学年最核心的课程名称。\n"
            f"请严格按 JSON 格式输出，不要加任何额外文字：\n"
            f'{{"{grade_priority[0]}": ["课程1", "课程2", ...], ...}}'
        )
        raw = resp.content.strip()
        from backend.src.utils.json_parser import parse_llm_json
        data = parse_llm_json(raw)
    except Exception:
        logger.exception("LLM 课程推理失败 major=%s grade=%s", major, grade)
        return []

    if not isinstance(data, dict):
        return []

    all_courses: list[str] = []
    for g in grade_priority:
        courses = data.get(g, [])
        if isinstance(courses, list):
            for c in courses:
                if isinstance(c, str) and c not in all_courses and len(all_courses) < total_limit:
                    all_courses.append(c)
            # 写入表
            try:
                await CurriculumCourse.update_or_create(
                    defaults={"courses": json.dumps(courses, ensure_ascii=False)},
                    major=major, grade=g,
                )
            except Exception:
                logger.exception("写入课程表失败 major=%s grade=%s", major, g)

    return all_courses

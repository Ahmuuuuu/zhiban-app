"""Interactive classroom lesson generation for learning path nodes."""

from __future__ import annotations

import json
import logging
import hashlib
from pathlib import Path
from typing import Any

from backend.src.ai_core.llm_config import llm
from backend.src.models.path_model import LearningPath, PathNode, UserPathProgress
from backend.src.models.portraitmodel import User_picture
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.usermodel import User
from backend.src.service.portrait.service import PortraitRadarService, format_portrait
from backend.src.utils.constants import STATIC_DIR
from backend.src.utils.json_parser import parse_llm_json
from backend.src.utils.tts_utils import clean_for_tts, generate_audio

logger = logging.getLogger(__name__)

CLASSROOM_AUDIO_DIR = STATIC_DIR / "audio" / "classroom"


def _safe_json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid path JSON payload skipped in classroom service", exc_info=True)
        return fallback


def _clip(text: Any, limit: int = 900) -> str:
    value = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
    return value[:limit]


def _bounded_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


def _resource_snapshot(resource: dict[str, Any], content: str = "") -> dict[str, str]:
    title = resource.get("title") or resource.get("topic") or resource.get("filename") or resource.get("name") or "学习资料"
    rtype = resource.get("typeLabel") or resource.get("resource_type") or resource.get("fileType") or resource.get("type") or "资料"
    summary = (
        resource.get("summary")
        or resource.get("description")
        or resource.get("abstract")
        or resource.get("content")
        or resource.get("text")
        or content
    )
    return {
        "title": _clip(title, 80),
        "type": _clip(rtype, 32),
        "summary": _clip(summary, 780),
    }


async def generate_classroom_audio(
    text: str,
    user_id: int,
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = "+0%",
) -> dict[str, Any]:
    cleaned = clean_for_tts(_clip(text, 520))
    if not cleaned:
        raise ValueError("讲解文本不能为空")

    digest = hashlib.sha1(f"{user_id}:{voice}:{rate}:{cleaned}".encode("utf-8")).hexdigest()[:24]
    output_path = CLASSROOM_AUDIO_DIR / str(user_id) / f"{digest}.mp3"
    saved_path = await generate_audio(cleaned, str(output_path), voice=voice, rate=rate)
    saved_name = Path(saved_path).name
    return {
        "audio_url": f"/static/audio/classroom/{user_id}/{saved_name}",
        "voice": voice,
        "rate": rate,
        "text": cleaned,
    }


_GENERIC_CLASSROOM_PHRASES = [
    "按当前节点动态讲解",
    "课堂会",
    "资料会",
    "资源会",
    "根据当前节点",
    "暂无可展示摘要",
    "节点驱动",
    "资料联动",
    "本幕讲解",
    "继续讲解",
    "右侧资料不是摆设",
    "单独预览文件",
    "把已有资源用起来",
    "把资料用起来",
    "当前讲解",
    "资料只服务",
    "文件列表",
    "右侧资料",
]


def _is_generic_teaching(script: Any, board_items: Any, example: Any) -> bool:
    """Detect product-like classroom text before it reaches the UI."""
    text = " ".join([
        str(script or ""),
        " ".join(str(item or "") for item in board_items) if isinstance(board_items, list) else str(board_items or ""),
        str(example or ""),
    ])
    compact = " ".join(text.split())
    if len(compact) < 50:
        return True

    hits = sum(1 for phrase in _GENERIC_CLASSROOM_PHRASES if phrase in compact)
    if hits >= 2:
        return True

    if isinstance(board_items, list):
        meaningful_items = [
            str(item).strip()
            for item in board_items
            if len(str(item).strip()) >= 4
            and not any(phrase in str(item) for phrase in _GENERIC_CLASSROOM_PHRASES)
        ]
        if len(meaningful_items) < 2:
            return True

    return False


def _fallback_lesson(topic: str, summary: str, resources: list[dict[str, str]], portrait_text: str) -> dict[str, Any]:
    keywords = [item for item in summary.replace("，", "、").replace(",", "、").split("、") if item.strip()][:5]
    if not keywords:
        keywords = [topic, "关键概念", "典型题型"]
    resource_titles = [item["title"] for item in resources[:3]] or ["当前路径节点"]
    personal = "会结合你的画像调整讲法" if portrait_text and "暂无" not in portrait_text else "先按通用课堂节奏推进"
    return {
        "title": topic,
        "personal_summary": personal,
        "segments": [
            {
                "id": "lead-in",
                "type": "hook",
                "title": "情境导入",
                "subtitle": "先把知识点放进真实任务",
                "intent": "先知道为什么学",
                "teacher_speech": f"这节课先把「{topic}」放进真实解题场景里。你不需要一开始背完整定义，先抓它解决什么问题，再看它和后续知识的关系。",
                "script": f"这节课先把「{topic}」放进真实解题场景里。你不需要一开始背完整定义，先抓它解决什么问题，再看它和后续知识的关系。",
                "board_title": "本节要解决的问题",
                "board_items": [summary or f"{topic} 是本节点的核心任务", "先建立问题意识", "再进入概念拆解"],
                "points": [summary or f"{topic} 是本节点的核心任务", "先建立问题意识，再进入概念拆解"],
                "visual_hint": "从问题入口进入，不把资料当成普通文件列表。",
                "example": f"如果题目问到「{topic}」，先判断它考的是概念、步骤还是应用。",
                "resource_refs": [],
                "duration_seconds": 18,
                "question": {
                    "prompt": f"学「{topic}」时，最先要问自己的问题是什么？",
                    "options": ["它解决什么问题", "先背所有定义", "直接跳到下一章"],
                    "answer": "它解决什么问题",
                    "feedback": "对，先抓问题，再补定义和公式，后面做题会稳很多。",
                },
            },
            {
                "id": "concept",
                "type": "concept",
                "title": "核心讲解",
                "subtitle": "把主干拆成可理解的关系",
                "intent": "拆开关键概念",
                "teacher_speech": f"现在进入主干。围绕「{topic}」，我们先抓住 { '、'.join(keywords[:3]) }。每个概念都不要孤立看，要问它从哪里来、参与什么过程、容易和谁混淆。",
                "script": f"现在进入主干。围绕「{topic}」，我们先抓住 { '、'.join(keywords[:3]) }。每个概念都不要孤立看，要问它从哪里来、参与什么过程、容易和谁混淆。",
                "board_title": "概念主线",
                "board_items": keywords,
                "points": keywords,
                "visual_hint": "按“来源 -> 作用 -> 易混点”三步看概念。",
                "example": f"把「{topic}」拆成一个输入、一个处理过程、一个输出结果。",
                "resource_refs": [],
                "duration_seconds": 24,
                "question": {
                    "prompt": "如果只能保留一句话，你会怎样概括这一段？",
                    "options": ["概念关系和使用场景", "教材原文", "随便记几个词"],
                    "answer": "概念关系和使用场景",
                    "feedback": "很好，课堂的目标是能解释和迁移，不是只记词。",
                },
            },
            {
                "id": "resource-link",
                "type": "resource",
                "title": "资料验证",
                "subtitle": "用资料查证课堂主线",
                "intent": "查证关键点",
                "teacher_speech": f"现在用资料反过来验证「{topic}」的板书。先找到定义、步骤或例题，再判断它能否解释刚才的概念关系。",
                "script": f"现在用资料反过来验证「{topic}」的板书。先找到定义、步骤或例题，再判断它能否解释刚才的概念关系。",
                "board_title": "查证路径",
                "board_items": ["找定义", "找步骤", "找例题", "回看结构"],
                "points": [f"定位「{topic}」的定义", "找可复现的步骤或公式", "用例题检查板书是否能解释"],
                "visual_hint": "资料只负责查证，不在课堂主画面重复列文件。",
                "example": f"先找资料中能解释「{topic}」定义或步骤的一段，再对照板书复述。",
                "resource_refs": [
                    {
                        "title": item["title"],
                        "type": item["type"],
                        "how_to_use": _clip(item.get("summary") or "用来验证本幕板书", 90),
                    }
                    for item in resources[:3]
                ],
                "duration_seconds": 22,
                "question": {
                    "prompt": "看资料时最应该优先验证什么？",
                    "options": ["课堂刚讲的关键关系", "页面排版好不好看", "资料有多少页"],
                    "answer": "课堂刚讲的关键关系",
                    "feedback": "对，资料要为理解服务，不是单纯浏览。",
                },
            },
            {
                "id": "checkpoint",
                "type": "quiz",
                "title": "即时检查",
                "subtitle": "用一个短问暴露薄弱点",
                "intent": "用短问题卡住薄弱点",
                "teacher_speech": f"这里做一个短检查：如果你能用自己的话讲清「{topic}」的关键步骤，就说明主线已经过关；如果讲不清，就回到板书第一条。",
                "script": f"这里做一个短检查：如果你能用自己的话讲清「{topic}」的关键步骤，就说明主线已经过关；如果讲不清，就回到板书第一条。",
                "board_title": "检查路径",
                "board_items": ["用一句话概括", "举一个例子", "指出一个易错点"],
                "points": ["用一句话概括", "举一个例子", "指出一个易错点"],
                "visual_hint": "先小问，再决定是否进入正式测验。",
                "example": f"试着说出「{topic}」最容易出错的一处。",
                "resource_refs": [],
                "duration_seconds": 18,
                "question": {
                    "prompt": f"你现在最可能卡在「{topic}」的哪一块？",
                    "options": ["概念关系", "计算步骤", "例题迁移"],
                    "answer": "概念关系",
                    "feedback": "无论选哪项都可以，后面小知会按你的回答追问。",
                },
            },
            {
                "id": "feynman",
                "type": "feynman",
                "title": "费曼反讲",
                "subtitle": "换你当老师讲一遍",
                "intent": "换你当老师",
                "teacher_speech": f"最后换你讲。请用给同学解释的方式，把「{topic}」讲成三句话：它是什么、为什么重要、题目里怎么用。",
                "script": f"最后换你讲。请用给同学解释的方式，把「{topic}」讲成三句话：它是什么、为什么重要、题目里怎么用。",
                "board_title": "三句话反讲",
                "board_items": ["是什么", "为什么重要", "怎么用"],
                "points": ["是什么", "为什么重要", "怎么用"],
                "visual_hint": "讲不顺的地方就是下一轮补强点。",
                "example": f"你可以这样开头：{topic} 主要帮助我理解……",
                "resource_refs": [],
                "duration_seconds": 20,
                "question": {
                    "prompt": "你准备用哪种方式讲给小知听？",
                    "options": ["三句话总结", "举例说明", "先说不懂处"],
                    "answer": "三句话总结",
                    "feedback": "可以，从短解释开始，小知再继续追问。",
                },
            },
        ],
    }


def _normalize_lesson(raw: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return fallback
    segments = raw.get("segments")
    if not isinstance(segments, list) or len(segments) < 3:
        return fallback

    normalized = []
    fallback_by_id = {item["id"]: item for item in fallback["segments"]}
    for index, item in enumerate(segments[:6]):
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or f"segment-{index + 1}")
        base = fallback_by_id.get(sid, fallback["segments"][min(index, len(fallback["segments"]) - 1)])
        question = item.get("question") if isinstance(item.get("question"), dict) else base.get("question", {})
        script = item.get("teacher_speech") or item.get("script") or base["script"]
        board_items = item.get("board_items") if isinstance(item.get("board_items"), list) else item.get("points")
        resource_refs = item.get("resource_refs") if isinstance(item.get("resource_refs"), list) else base.get("resource_refs", [])
        example = item.get("example") or base.get("example") or ""
        if _is_generic_teaching(script, board_items, example):
            script = base["script"]
            board_items = base["board_items"]
            example = base.get("example") or ""
            if not resource_refs:
                resource_refs = base.get("resource_refs", [])
        normalized.append({
            "id": sid,
            "type": _clip(item.get("type") or base.get("type") or sid, 24),
            "title": _clip(item.get("title") or base["title"], 24),
            "subtitle": _clip(item.get("subtitle") or base.get("subtitle") or "", 56),
            "intent": _clip(item.get("intent") or base["intent"], 28),
            "teacher_speech": _clip(script, 360),
            "script": _clip(script, 360),
            "board_title": _clip(item.get("board_title") or base.get("board_title") or "课堂板书", 32),
            "board_items": [
                _clip(point, 56)
                for point in (board_items if isinstance(board_items, list) else base["points"])
                if str(point or "").strip()
            ][:5],
            "points": [
                _clip(point, 72)
                for point in (item.get("points") if isinstance(item.get("points"), list) else base["points"])
                if str(point or "").strip()
            ][:5],
            "visual_hint": _clip(item.get("visual_hint") or base.get("visual_hint") or "", 90),
            "example": _clip(example, 120),
            "resource_refs": [
                {
                    "title": _clip(ref.get("title") if isinstance(ref, dict) else ref, 48),
                    "type": _clip(ref.get("type") if isinstance(ref, dict) else "资料", 24),
                    "how_to_use": _clip(ref.get("how_to_use") if isinstance(ref, dict) else "支撑本幕讲解", 120),
                }
                for ref in resource_refs
                if (isinstance(ref, dict) and ref.get("title")) or str(ref or "").strip()
            ][:3],
            "duration_seconds": _bounded_int(item.get("duration_seconds") or base.get("duration_seconds"), 20, 12, 45),
            "question": {
                "prompt": _clip(question.get("prompt") or base["question"]["prompt"], 90),
                "options": [
                    _clip(option, 28)
                    for option in (question.get("options") if isinstance(question.get("options"), list) else base["question"]["options"])
                    if str(option or "").strip()
                ][:4],
                "answer": _clip(question.get("answer") or base["question"]["answer"], 28),
                "feedback": _clip(question.get("feedback") or base["question"]["feedback"], 120),
            },
        })

    if len(normalized) < 3:
        return fallback
    return {
        "title": _clip(raw.get("title") or fallback["title"], 60),
        "personal_summary": _clip(raw.get("personal_summary") or fallback["personal_summary"], 120),
        "segments": normalized,
    }


async def _build_portrait_context(user_id: int) -> str:
    user = await User.filter(id=user_id).first()
    parts = []
    if user:
        if user.major:
            parts.append(f"专业：{user.major}")
        if user.grade:
            parts.append(f"年级：{user.grade}")
        if user.profile:
            parts.append(f"简介：{user.profile}")

    picture = await User_picture.filter(user_id=user_id).first()
    if picture:
        radar_data = None
        try:
            radar_data = await PortraitRadarService.get(user_id)
        except Exception:
            logger.debug("Read portrait radar failed in classroom service", exc_info=True)
        parts.extend(format_portrait(picture, show_missing=False, radar_data=radar_data))

    return "\n".join(parts) if parts else "暂无画像数据"


async def _load_node_resources(progress: UserPathProgress | None, client_resources: list[dict[str, Any]]) -> list[dict[str, str]]:
    snapshots = [_resource_snapshot(item) for item in client_resources[:6] if isinstance(item, dict)]
    seen_titles = {item["title"] for item in snapshots}

    resource_ids = _safe_json_loads(progress.resource_ids if progress else None, [])
    if not isinstance(resource_ids, list) or not resource_ids:
        return snapshots[:6]

    records = await GeneratedResource.filter(id__in=resource_ids).all()
    for record in records:
        item = _resource_snapshot(
            {"title": record.topic, "resource_type": record.resource_type},
            content=record.content,
        )
        if item["title"] in seen_titles:
            continue
        seen_titles.add(item["title"])
        snapshots.append(item)
        if len(snapshots) >= 6:
            break
    return snapshots


async def generate_classroom_lesson(
    path_id: int,
    node_id: int,
    user_id: int,
    client_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    node = await PathNode.filter(id=node_id, path_id=path_id).first()
    if not node:
        return None

    path = await LearningPath.filter(id=path_id).first()
    progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()

    client_payload = client_payload or {}
    client_node = client_payload.get("node") if isinstance(client_payload.get("node"), dict) else {}
    client_resources = client_payload.get("resources") if isinstance(client_payload.get("resources"), list) else []
    quiz = client_payload.get("quiz") if isinstance(client_payload.get("quiz"), dict) else {}

    topic = node.topic or client_node.get("title") or client_node.get("topic") or "当前节点"
    knowledge_tags = _safe_json_loads(node.knowledge_tags, [])
    quiz_config = _safe_json_loads(node.quiz_config, {})
    summary = (
        client_node.get("summary")
        or client_node.get("description")
        or "、".join(str(item) for item in knowledge_tags[:6])
        or f"围绕 {topic} 完成概念理解、资料验证和检测。"
    )
    resources = await _load_node_resources(progress, client_resources)
    portrait_context = await _build_portrait_context(user_id)
    fallback = _fallback_lesson(topic, summary, resources, portrait_context)

    prompt = f"""
你是知伴的互动课堂规划智能体。请为一个学习路径节点生成真正可讲授的课堂脚本。

输出要求：
1. 只输出 JSON，不要 Markdown，不要解释。
2. JSON 顶层字段：title, personal_summary, segments。
3. segments 必须是 5 段，id 固定为 lead-in, concept, resource-link, checkpoint, feynman。
4. 每段包含 type、title、subtitle、intent、teacher_speech、script、board_title、board_items、points、visual_hint、example、resource_refs、duration_seconds、question。
5. teacher_speech/script 是小知可直接朗读的讲稿，每段 120-190 中文字，必须讲具体知识，不要空泛宣传。
6. board_items 是屏幕板书，3-5 条，每条不超过 24 字，必须是本节点知识内容，不要写“按当前节点动态讲解”。
7. example 是本幕的短例子、类比或操作步骤，不超过 60 字。
8. resource_refs 只能引用给出的可用资源，包含 title、type、how_to_use；没有合适资源则给空数组。
9. question 包含 prompt、options、answer、feedback；options 3 个。
10. 个性化必须基于画像、年级专业、弱点或资源，不要写“根据你的画像”这种空话。
11. 课堂内容要像老师讲课：先抛问题，再讲板书，再用例子/题目检查。避免像资料预览列表。
12. 禁止只描述产品功能，例如“课堂会根据节点讲解”“资料会辅助学习”；必须直接讲本节点知识本身。
13. 如果节点涉及计算、公式、步骤或概念关系，至少在 example 或 board_items 中给出一个具体表达式、步骤链或易混对比。
14. resource-link 段只能讲“如何用资料验证本节点的定义、步骤、例题或易错点”，不要写“资料不是摆设”“把资料用起来”这类产品说明。

路径主题：{path.subject if path else "未知"}
节点标题：{topic}
节点摘要：{summary}
知识标签：{json.dumps(knowledge_tags, ensure_ascii=False)}
测验配置：{json.dumps(quiz_config, ensure_ascii=False)}
前端测验快照：{json.dumps(quiz, ensure_ascii=False)[:900]}
可用资源摘要：{json.dumps(resources, ensure_ascii=False)[:2200]}
用户画像：
{portrait_context}
"""

    try:
        response = await llm.ainvoke(prompt, priority="high", user_id=user_id, pool="path")
        parsed = parse_llm_json(response.content)
        lesson = _normalize_lesson(parsed, fallback)
    except Exception:
        logger.exception("classroom lesson generation failed path_id=%s node_id=%s user_id=%s", path_id, node_id, user_id)
        lesson = fallback

    return {
        "path_id": path_id,
        "node_id": node_id,
        "topic": topic,
        "resources": resources,
        "portrait_context": portrait_context,
        "lesson": lesson,
    }

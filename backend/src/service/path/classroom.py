"""Interactive classroom lesson generation for learning path nodes."""

from __future__ import annotations

import json
import logging
import hashlib
import re
from pathlib import Path
from typing import Any

from backend.src.models.path_model import LearningPath, PathNode, UserPathProgress
from backend.src.models.portraitmodel import User_picture
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.usermodel import User
from backend.src.service.portrait.service import PortraitRadarService, format_portrait
from backend.src.utils.constants import STATIC_DIR
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
    "先建立问题意识",
    "用一句话解释",
    "前后知识的关系",
    "页数",
    "页块",
    "支撑本幕",
    "讲给小知",
    "资料不是摆设",
    "课堂主画面",
    "亲啊",
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


def _dedupe_text_items(items: list[Any], limit: int = 5, size: int = 56) -> list[str]:
    cleaned: list[str] = []
    seen = set()
    for item in items if isinstance(items, list) else []:
        text = _clip(item, size).strip(" ，,。；;")
        if not text:
            continue
        if any(phrase in text for phrase in _GENERIC_CLASSROOM_PHRASES):
            continue
        key = re.sub(r"[\s，,。；;：:、]+", "", text).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _resource_refs(resources: list[dict[str, str]], limit: int = 3) -> list[dict[str, str]]:
    refs = []
    for item in resources[:limit]:
        refs.append({
            "title": _clip(item.get("title") or "学习资料", 48),
            "type": _clip(item.get("type") or "资料", 24),
            "how_to_use": _clip(item.get("summary") or "核对定义、步骤或例题", 90),
        })
    return refs


def _teaching_pack(topic: str, summary: str) -> dict[str, Any]:
    title = _clip(topic, 60) or "当前知识点"
    context = f"{title} {_clip(summary, 500)}"

    if re.search(r"BCD|ASCII|编码", context, re.I):
        return {
            "lead": "先分清两件事：数字怎样保存，字符怎样编号。",
            "entry_items": ["数字表示", "字符编码", "易混对比"],
            "core_items": ["BCD表示十进制数字", "8421BCD按权相加", "压缩BCD一字节两位", "ASCII表示字符编号", "编码值不等于数值"],
            "lines": [
                "BCD服务十进制数字，每一位只允许表示0到9。",
                "8421BCD靠8、4、2、1四个位权组合出一位十进制数。",
                "ASCII服务字符，字符“5”的编码是35H，不等于数值5。",
            ],
            "example": "十进制59的压缩BCD是0101 1001B；字符“5”的ASCII码是35H。",
            "resource_items": ["查BCD定义", "查8421权值", "查ASCII码表"],
            "resource_lines": ["先在资料中找BCD定义。", "再找8421BCD权值说明。", "最后对比ASCII码表里的字符编号。"],
            "resource_example": "资料里若同时出现BCD和ASCII，重点看它们分别服务“数字”和“字符”。",
            "question": "为什么字符“5”的ASCII码不是二进制数5？",
            "feynman_prompt": "请用“数字表示”和“字符编号”的区别讲清BCD与ASCII。",
        }

    if re.search(r"补码|反码|原码|符号", context):
        return {
            "lead": "负数编码的核心目标，是让机器用加法完成减法。",
            "entry_items": ["为什么要补码", "负数怎么表示", "溢出怎么判断"],
            "core_items": ["原码最高位表符号", "反码负数按位取反", "补码等于反码加一", "补码统一加减运算", "溢出看符号变化"],
            "lines": [
                "原码直观，但会出现正零和负零，运算处理不方便。",
                "补码把减法转换为加法，让CPU可以复用同一套加法器。",
                "判断补码结果必须结合机器位数，不能只看二进制表面。",
            ],
            "example": "8位机器中，-5原码为10000101，反码为11111010，补码为11111011。",
            "resource_items": ["找表示规则", "找转换步骤", "找溢出例题"],
            "resource_lines": ["先查原码、反码、补码的定义。", "再核对负数转换步骤。", "最后看溢出判断例题。"],
            "resource_example": "遇到补码例题，先确认位数，再做取反加一。",
            "question": "为什么补码能让减法用加法器完成？",
            "feynman_prompt": "请用“省掉单独减法电路”的角度解释补码。",
        }

    if re.search(r"数制|进制|转换|位权|基数", context):
        return {
            "lead": "进制转换只抓两个词：基数决定可用数字，位权决定每位价值。",
            "entry_items": ["基数是什么", "位权怎么算", "怎么互转"],
            "core_items": ["基数决定数字范围", "位权决定每位价值", "按权展开转十进制", "除基取余转目标进制", "二八十六分组互转"],
            "lines": [
                "任意进制都能按位权展开成十进制，这是最稳的中间桥。",
                "十进制转其他进制常用除基取余，余数从下往上读。",
                "二进制到八进制每3位一组，到十六进制每4位一组。",
            ],
            "example": "1011B = 1x8 + 0x4 + 1x2 + 1x1 = 11D。",
            "resource_items": ["找位权公式", "找转换步骤", "找分组例题"],
            "resource_lines": ["先查基数和位权定义。", "再找按权展开例子。", "最后核对分组互转规则。"],
            "resource_example": "看到1011B时，先写位权8、4、2、1，再相加。",
            "question": "为什么二进制转十六进制可以每4位一组？",
            "feynman_prompt": "请用“基数”和“位权”解释一次进制转换。",
        }

    if re.search(r"寻址|物理地址|段地址|偏移|CS|IP", context, re.I):
        return {
            "lead": "8086寻址可以先看成：段起点加段内偏移。",
            "entry_items": ["段地址是什么", "偏移地址是什么", "物理地址怎么算"],
            "core_items": ["段地址左移4位", "偏移地址定位段内位置", "物理地址20位", "CS和IP配合取指", "DS常用于数据访问"],
            "lines": [
                "8086用段地址和偏移地址组合出20位物理地址。",
                "段地址左移4位相当于乘16，再加偏移地址。",
                "CS:IP用于取下一条指令，DS通常配合数据访问。",
            ],
            "example": "CS=1234H，IP=5678H，则物理地址=12340H+5678H=179B8H。",
            "resource_items": ["找地址公式", "找寄存器作用", "找计算例题"],
            "resource_lines": ["先查物理地址公式。", "再确认CS、IP、DS的作用。", "最后做一题段地址加偏移地址。"],
            "resource_example": "资料中若有CS:IP例题，直接拿来验证左移4位再相加。",
            "question": "段地址为什么要左移4位再加偏移地址？",
            "feynman_prompt": "请用“楼栋号加房间号”的类比解释段地址和偏移地址。",
        }

    if re.search(r"8086|CPU|微处理器|内部结构|EU|BIU", context, re.I):
        return {
            "lead": "8086内部结构先看两个协作单元：EU负责执行，BIU负责取指和总线。",
            "entry_items": ["谁负责执行", "谁负责取指", "为什么能并行"],
            "core_items": ["EU负责译码执行", "BIU负责取指访存", "指令队列减少等待", "寄存器保存中间结果", "标志位记录运算状态"],
            "lines": [
                "EU包含运算器、寄存器和标志寄存器，负责真正执行指令。",
                "BIU负责访问存储器和I/O，并把指令提前取入队列。",
                "指令队列让取指和执行部分重叠，是8086流水思想的入口。",
            ],
            "example": "BIU先取指进队列，EU执行当前指令；遇到转移指令时队列会刷新。",
            "resource_items": ["找EU组成", "找BIU作用", "找指令队列"],
            "resource_lines": ["先查EU和BIU各自组成。", "再看指令队列为什么能减少等待。", "最后联系转移指令刷新队列。"],
            "resource_example": "看到8086结构图时，先把部件分到EU或BIU两边。",
            "question": "8086为什么要把EU和BIU分开？",
            "feynman_prompt": "请用“前台执行、后台取货”的类比解释EU和BIU。",
        }

    keywords = _dedupe_text_items(
        [item for item in re.split(r"[，,、。；;\s]+", f"{title} {summary}") if item],
        limit=5,
        size=24,
    )
    core_items = keywords if len(keywords) >= 3 else [title, "核心定义", "关键步骤", "典型例题", "易错点"]
    return {
        "lead": f"这节先讲清「{title}」解决的问题，再把细节留给资料和练习。",
        "entry_items": core_items[:3],
        "core_items": core_items,
        "lines": [
            f"先确认「{title}」的定义边界，避免和相近概念混淆。",
            "再找它的步骤、结构或作用链，形成可复述的主线。",
            "最后用一个例题或场景检查自己能不能迁移。",
        ],
        "example": f"先说清「{title}」是什么，再补一个它解决什么问题的例子。",
        "resource_items": ["找定义边界", "找步骤公式", "找例题验证"],
        "resource_lines": ["先找资料中的定义边界。", "再找步骤、公式或例题。", "最后复述证据支持的结论。"],
        "resource_example": f"在资料中找一段能解释「{title}」定义或步骤的内容。",
        "question": f"「{title}」最容易和哪个概念混淆？",
        "feynman_prompt": f"请用三句话讲清「{title}」：是什么、为什么重要、怎么用。",
    }


def _fallback_lesson(topic: str, summary: str, resources: list[dict[str, str]], portrait_text: str) -> dict[str, Any]:
    pack = _teaching_pack(topic, summary)
    personal = "会结合你的画像调整讲法" if portrait_text and "暂无" not in portrait_text else "先按通用课堂节奏推进"
    return {
        "title": topic,
        "personal_summary": personal,
        "segments": [
            {
                "id": "lead-in",
                "type": "hook",
                "title": "情境导入",
                "subtitle": "先判断它解决什么问题",
                "intent": "先知道为什么学",
                "teacher_speech": f"这节先从问题进入：{pack['lead']}你不用一开始背完整资料，先抓住它解决什么问题、常在题目里以什么形式出现，再进入细节。",
                "script": f"这节先从问题进入：{pack['lead']}你不用一开始背完整资料，先抓住它解决什么问题、常在题目里以什么形式出现，再进入细节。",
                "board_title": "问题入口",
                "board_items": pack["entry_items"],
                "points": pack["lines"][:3],
                "visual_hint": pack["lead"],
                "example": pack["example"],
                "resource_refs": [],
                "duration_seconds": 18,
                "question": {
                    "prompt": pack["question"],
                    "options": ["先说定义", "先看例题", "先找易混点"],
                    "answer": "先说定义",
                    "feedback": "先把定义边界说清楚，再看例题和易混点。",
                },
            },
            {
                "id": "concept",
                "type": "concept",
                "title": "核心讲解",
                "subtitle": "把主干拆成可理解的关系",
                "intent": "拆开关键概念",
                "teacher_speech": f"现在讲主干。{''.join(pack['lines'])}这一幕只保留最核心的关系，更多推导细节留到右侧资料里慢慢看。",
                "script": f"现在讲主干。{''.join(pack['lines'])}这一幕只保留最核心的关系，更多推导细节留到右侧资料里慢慢看。",
                "board_title": "概念主线",
                "board_items": pack["core_items"],
                "points": pack["lines"],
                "visual_hint": pack["lead"],
                "example": pack["example"],
                "resource_refs": [],
                "duration_seconds": 24,
                "question": {
                    "prompt": pack["question"],
                    "options": ["定义边界", "步骤关系", "易错对比"],
                    "answer": "定义边界",
                    "feedback": "先抓定义边界，再补步骤关系和易错对比。",
                },
            },
            {
                "id": "resource-link",
                "type": "resource",
                "title": "资料佐证",
                "subtitle": "用资料查证课堂主线",
                "intent": "查证关键点",
                "teacher_speech": f"现在用资料做校验。{''.join(pack['resource_lines'])}资料不需要整篇搬进课堂，只要找出能支撑刚才板书的证据。",
                "script": f"现在用资料做校验。{''.join(pack['resource_lines'])}资料不需要整篇搬进课堂，只要找出能支撑刚才板书的证据。",
                "board_title": "查证路径",
                "board_items": pack["resource_items"],
                "points": pack["resource_lines"],
                "visual_hint": "资料负责查证，课堂负责讲清主线。",
                "example": pack["resource_example"],
                "resource_refs": _resource_refs(resources),
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
                "teacher_speech": f"现在做一次短检查：{pack['question']}如果答不上来，不急着继续刷题，先回到上一幕板书，把定义、步骤和例子重新对齐。",
                "script": f"现在做一次短检查：{pack['question']}如果答不上来，不急着继续刷题，先回到上一幕板书，把定义、步骤和例子重新对齐。",
                "board_title": "检查路径",
                "board_items": ["用一句话概括", "举一个例子", "指出一个易错点"],
                "points": [pack["question"], "答不上来就回看板书", "用例题定位薄弱点"],
                "visual_hint": "先小问，再决定是否进入正式测验。",
                "example": pack["question"],
                "resource_refs": [],
                "duration_seconds": 18,
                "question": {
                    "prompt": pack["question"],
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
                "teacher_speech": f"最后换你讲。{pack['feynman_prompt']}讲不顺的地方不用藏起来，那正是下一轮学习最该补的位置。",
                "script": f"最后换你讲。{pack['feynman_prompt']}讲不顺的地方不用藏起来，那正是下一轮学习最该补的位置。",
                "board_title": "三句话反讲",
                "board_items": ["是什么", "为什么重要", "怎么用"],
                "points": ["是什么", "为什么重要", "怎么用"],
                "visual_hint": "讲不顺的地方就是下一轮补强点。",
                "example": pack["feynman_prompt"],
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

    picture = None
    if user and getattr(user, "picture_id", None):
        picture = await User_picture.filter(id=user.picture_id).first()
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

    # 延迟导入规避循环依赖：classroom_graph 顶部 import 了本模块的 _normalize_lesson 等
    from backend.src.ai_core.classroom_graph import classroom_graph, ClassroomState
    from backend.src.service.path.generation_locks import get_node_generation_lock

    lock = await get_node_generation_lock(user_id, path_id, node_id, "classroom")
    async with lock:
        try:
            initial = ClassroomState(
                path_id=path_id,
                node_id=node_id,
                user_id=user_id,
                subject=path.subject if path else "未知",
                topic=topic,
                summary=summary,
                knowledge_tags=knowledge_tags,
                quiz_config=quiz_config,
                quiz_snapshot=quiz,
                resources=resources,
                portrait_context=portrait_context,
                fallback_lesson=fallback,
                llm_priority="high",
            )
            final_state = await classroom_graph.ainvoke(initial)
            lesson = final_state.get("lesson") or fallback
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

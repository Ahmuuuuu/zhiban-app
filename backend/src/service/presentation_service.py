"""学习课件 HTML 生成服务 — 先出骨架，后台补音频"""

import asyncio
import json
import logging
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

from backend.src.models.presentation_model import Presentation
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.notification_model import Notification
from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt

logger = logging.getLogger(__name__)

PRESENTATION_DIR = Path(__file__).parent.parent.parent / "static" / "presentations"
TEMPLATE_PATH = Path(__file__).parent.parent / "ai_core" / "prompts" / "presentation" / "template.html"
TEMPLATE_VIDEO_PATH = Path(__file__).parent.parent / "ai_core" / "prompts" / "presentation" / "template_video.html"
PRESENTATION_TEMPLATE_VERSION = "visual-v5"


# ═══════════════════════════════════════════════
#  预览 — 展示可用章节让用户选择
# ═══════════════════════════════════════════════

async def preview(topic: str, user_id: int) -> dict:
    """预览话题的可用章节及其内容大纲"""
    doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
    chapters = []

    # intro — 从 document ## 标题提取
    if doc:
        content = doc.content or ""
        raw_parts = re.split(r"\n(?=## )", content.strip())
        if len(raw_parts) <= 1:
            raw_parts = re.split(r"\n(?=# )", content.strip())
        slides = []
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            lines = part.split("\n")
            title = lines[0].lstrip("#").strip()
            summary = ""
            for l in lines[1:]:
                s = l.strip().lstrip("-* ").strip()
                if s:
                    summary = s[:80]
                    break
            slides.append({"title": title, "summary": summary})
        chapters.append({
            "id": "intro",
            "title": "学科介绍",
            "slide_count": len(slides),
            "slides": slides,
        })

    # mindmap
    if mindmap_data:
        from backend.src.utils.mindmap import parse_mindmap_text

        def _count_nodes(node) -> int:
            return 1 + sum(_count_nodes(c) for c in node.get("children", []))
        parsed = parse_mindmap_text(mindmap_data.content or "")
        node_count = _count_nodes(parsed) if parsed else 0
        top_topics = [c.get("topic", "") for c in (parsed.get("children", [])[:5])] if parsed else []
        chapters.append({
            "id": "mindmap",
            "title": "思维导图",
            "node_count": node_count,
            "top_topics": top_topics,
        })

    # PPT
    if ppt_data:
        from backend.src.utils.tts_utils import parse_slides
        slides_meta = parse_slides(ppt_data.content or "")
        slides = [{"title": m.get("title", ""), "bullet_count": len(m.get("bullets", []))} for m in slides_meta]
        chapters.append({
            "id": "ppt",
            "title": "PPT讲解",
            "slide_count": len(slides),
            "slides": slides,
        })

    return {"chapters": chapters}


async def generate_questions(topic: str, user_id: int, chat_group_id: int = 0) -> dict:
    """分析资源内容或话题本身，生成 2-3 个选择题帮助用户聚焦课件方向"""
    from backend.src.models.usermodel import User

    doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
    has_resources = any([doc, mindmap_data, ppt_data])

    # 画像上下文
    portrait_context = ""
    user = await User.filter(id=user_id).first()
    if user:
        parts = []
        if user.major:
            parts.append(f"专业：{user.major}")
        if user.grade:
            parts.append(f"年级：{user.grade}")
        portrait_context = "；".join(parts) if parts else ""

    if has_resources:
        # 有资源 → 基于实际章节出题
        questions_list = await _generate_questions_from_content(topic, portrait_context, doc, ppt_data)
    else:
        # 无资源 → 基于话题常识出题（与资源生成并行）
        questions_list = await _generate_questions_from_topic(topic, portrait_context)

    if not questions_list:
        questions_list = [{
            "id": "depth",
            "question": "需要多深的内容？",
            "multi": False,
            "options": [
                {"label": "5分钟概览，了解核心概念", "value": "overview"},
                {"label": "标准讲解，理解原理和应用", "value": "standard"},
                {"label": "逐页详解，包含推导和案例", "value": "deep"},
            ],
        }]

    # 写入聊天历史
    if chat_group_id and chat_group_id > 0:
        from backend.src.models.chat_history_model import ChatHistory
        try:
            await ChatHistory.create(
                user=user,
                chat_group_id=chat_group_id,
                req="",
                res=json.dumps({"type": "presentation_questions", "topic": topic, "questions": questions_list, "_video_hint": "动态课件"}, ensure_ascii=False),
            )
        except Exception:
            logger.exception("保存追问到聊天历史失败")

    return {"questions": questions_list}


async def _generate_questions_from_content(topic: str, portrait_context: str, doc, ppt_data) -> list[dict]:
    """基于已有资源内容生成问题"""
    lines: list[str] = []
    if doc:
        content = doc.content or ""
        raw_parts = re.split(r"\n(?=## )", content.strip())
        if len(raw_parts) <= 1:
            raw_parts = re.split(r"\n(?=# )", content.strip())
        titles = []
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            title = part.split("\n")[0].lstrip("#").strip()
            titles.append(title)
        if titles:
            lines.append(f"【学科介绍】章节：{' | '.join(titles[:10])}")
    if ppt_data:
        from backend.src.utils.tts_utils import parse_slides
        slides_meta = parse_slides(ppt_data.content or "")
        titles = [m.get("title", "") for m in slides_meta if m.get("title")]
        if titles:
            lines.append(f"【PPT讲解】幻灯片：{' | '.join(titles[:15])}")

    content_summary = "\n".join(lines) if lines else "暂无章节信息"

    prompt = fill_prompt(
        load_prompt("presentation/questions"),
        topic=topic,
        portrait_context=portrait_context or "暂无画像",
        content_summary=content_summary,
    )

    try:
        resp = await llm.ainvoke(prompt)
        raw = resp.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        questions_data = json.loads(raw)
        return questions_data.get("questions", [])
    except json.JSONDecodeError:
        logger.warning("AI 问题 JSON 解析失败，降级为默认问题 raw=%s", raw[:200])
        return _default_questions(doc, ppt_data)
    except Exception:
        logger.exception("AI 问题生成失败")
        return _default_questions(doc, ppt_data)


async def _generate_questions_from_topic(topic: str, portrait_context: str) -> list[dict]:
    """无资源时，基于话题常识生成问题"""
    prompt = fill_prompt(
        load_prompt("presentation/questions_topic_only"),
        topic=topic,
        portrait_context=portrait_context or "暂无画像",
    )

    try:
        resp = await llm.ainvoke(prompt)
        raw = resp.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        questions_data = json.loads(raw)
        return questions_data.get("questions", [])
    except json.JSONDecodeError:
        logger.warning("AI 问题（话题模式）JSON 解析失败 raw=%s", raw[:200])
        return []
    except Exception:
        logger.exception("AI 问题（话题模式）生成失败")
        return []


def _default_questions(doc, ppt_data) -> list[dict]:
    """LLM 失败时的降级：从资源中提取章节标题作为选项"""
    options: list[dict] = []
    if doc:
        content = doc.content or ""
        raw_parts = re.split(r"\n(?=## )", content.strip())
        if len(raw_parts) <= 1:
            raw_parts = re.split(r"\n(?=# )", content.strip())
        for part in raw_parts[:6]:
            part = part.strip()
            if not part:
                continue
            title = part.split("\n")[0].lstrip("#").strip()[:30]
            if title:
                slug = re.sub(r"\s+", "_", title)
                options.append({"label": title, "value": slug})
    if not options and ppt_data:
        from backend.src.utils.tts_utils import parse_slides
        slides = parse_slides(ppt_data.content or "")
        for m in slides[:6]:
            title = m.get("title", "")[:30]
            if title:
                slug = re.sub(r"\s+", "_", title)
                options.append({"label": title, "value": slug})

    questions = []
    if options:
        questions.append({
            "id": "focus",
            "question": "你想重点讲哪几个方向？",
            "multi": True,
            "options": options,
        })
    questions.append({
        "id": "depth",
        "question": "需要多深的内容？",
        "multi": False,
        "options": [
            {"label": "5分钟概览，了解核心概念", "value": "overview"},
            {"label": "标准讲解，理解原理和应用", "value": "standard"},
            {"label": "逐页详解，包含推导和案例", "value": "deep"},
        ],
    })
    return questions


# ─── 内容裁剪 ───

def _crop_content_by_answers(doc, mindmap_data, ppt_data, answers: dict) -> tuple:
    """根据用户答案裁剪资源内容，返回裁剪后的副本"""
    focus_vals = _parse_focus_values(answers)
    depth = answers.get("depth", "standard")

    cropped_doc = _crop_document(doc, focus_vals, depth) if doc else None
    cropped_ppt = _crop_ppt(ppt_data, focus_vals, depth) if ppt_data else None
    # mindmap 暂不支持裁剪，保留原样
    return cropped_doc, mindmap_data, cropped_ppt


def _parse_focus_values(answers: dict) -> set[str]:
    """从 answers 中提取 focus 关键词"""
    keywords: set[str] = set()
    for key, val in answers.items():
        if key.startswith("focus") or key == "focus":
            if isinstance(val, list):
                for v in val:
                    keywords.update(_extract_keywords(v))
            elif isinstance(val, str):
                keywords.update(_extract_keywords(val))
    return keywords


def _extract_keywords(val: str) -> set[str]:
    """从 value 中拆词，如 'supervised_learning' → {'supervised', 'learning'}"""
    # 同时也保留原始值做子串匹配
    kw = {val.lower(), val.lower().replace("_", " "), val.lower().replace("_", "")}
    # 拆词
    for part in val.lower().replace("_", " ").split():
        if len(part) > 1:
            kw.add(part)
    return kw


def _crop_document(record, focus_vals: set[str], depth: str):
    """裁剪文档内容：只保留匹配的章节，并控制密度"""
    if not record:
        return None
    content = record.content or ""
    raw_parts = re.split(r"\n(?=## )", content.strip())
    if len(raw_parts) <= 1:
        raw_parts = re.split(r"\n(?=# )", content.strip())

    if not focus_vals:
        new_content = _trim_content_depth(content, depth)
        return _make_cropped_copy(record, new_content)

    kept: list[str] = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        title = part.split("\n")[0].lstrip("#").strip().lower()
        text = part.lower()
        if any(kw in title or kw in text for kw in focus_vals):
            kept.append(part)

    if not kept:
        return record

    new_content = "\n\n".join(kept)
    if depth == "overview":
        new_content = _trim_content_depth(new_content, depth)
    return _make_cropped_copy(record, new_content)


def _crop_ppt(record, focus_vals: set[str], depth: str):
    """裁剪 PPT 内容：只保留匹配的幻灯片"""
    if not record:
        return None
    content = record.content or ""
    slides = re.split(r"\n---\n", content.strip())

    if not focus_vals:
        new_content = _trim_content_depth(content, depth, is_ppt=True)
        return _make_cropped_copy(record, new_content)

    kept: list[str] = []
    for slide in slides:
        slide = slide.strip()
        if not slide:
            continue
        slide_lower = slide.lower()
        if any(kw in slide_lower for kw in focus_vals):
            kept.append(slide)

    if not kept:
        return record

    new_content = "\n---\n".join(kept)
    if depth == "overview":
        new_content = _trim_content_depth(new_content, depth, is_ppt=True)
    return _make_cropped_copy(record, new_content)


def _make_cropped_copy(record, new_content: str):
    """创建裁剪后的轻量副本，不污染 ORM 对象"""
    return SimpleNamespace(
        id=record.id,
        content=new_content,
        resource_type=record.resource_type,
        topic=record.topic,
    )


def _trim_content_depth(content: str, depth: str, is_ppt: bool = False) -> str:
    """概览模式：每段只保留标题 + 前 2 个 bullet"""
    if depth != "overview":
        return content
    sep = "\n---\n" if is_ppt else "\n\n"
    blocks = content.split(sep)
    trimmed: list[str] = []
    for block in blocks:
        lines = block.strip().split("\n")
        kept_lines = []
        bullet_count = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                if bullet_count < 2:
                    kept_lines.append(line)
                    bullet_count += 1
            else:
                kept_lines.append(line)
        trimmed.append("\n".join(kept_lines))
    return sep.join(trimmed)
_sse_queues: dict[int, list[asyncio.Queue]] = {}


def _subscribe_sse(presentation_id: int) -> asyncio.Queue:
    q = asyncio.Queue()
    _sse_queues.setdefault(presentation_id, []).append(q)
    return q


def _unsubscribe_sse(presentation_id: int, q: asyncio.Queue):
    queues = _sse_queues.get(presentation_id, [])
    if q in queues:
        queues.remove(q)
    if not queues:
        _sse_queues.pop(presentation_id, None)


async def _notify_sse(presentation_id: int, data: dict):
    for q in _sse_queues.get(presentation_id, []):
        q.put_nowait(data)


# ═══════════════════════════════════════════════
#  对外 API
# ═══════════════════════════════════════════════

async def generate(topic: str, user_id: int, voice: str = "zh-CN-XiaoxiaoNeural",
                  chapters: list[str] | None = None, answers: dict | None = None,
                  chat_group_id: int = 0, video_mode: bool = False) -> dict:
    """创建课件记录 + 立即出骨架 + 后台补音频。video_mode=True 使用简洁视频模板"""
    import time as _time
    _t_total = _time.perf_counter()
    from datetime import datetime, timedelta
    from backend.src.models.usermodel import User
    user = await User.filter(id=user_id).first()
    if not user:
        return {"error": "用户不存在"}

    # 去重：2 分钟内同话题同模板已创建过课件 → 直接返回已有记录
    _expected_tag = "template-version:video-v3" if video_mode else f"template-version:{PRESENTATION_TEMPLATE_VERSION}"
    cutoff = datetime.now() - timedelta(minutes=2)
    existing = await Presentation.filter(
        user_id=user_id, topic=topic, created_at__gte=cutoff,
    ).order_by("-created_at").first()
    if existing and _presentation_file_matches_template(existing.file_url, _expected_tag):
        logger.info("课件去重命中 user=%s topic=%s existing_id=%s video_mode=%s", user_id, topic, existing.id, video_mode)
        return {
            "id": existing.id,
            "file_url": _versioned_presentation_url(existing.file_url),
            "status": existing.status,
            "cached": True,
            "template_version": "video" if video_mode else PRESENTATION_TEMPLATE_VERSION,
        }

    doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
    if not any([doc, mindmap_data, ppt_data]):
        return {"error": f"话题「{topic}」暂无已生成的资源，请先通过 /resource/generate 生成"}

    # 用户作答 → 裁剪内容
    if answers:
        doc, mindmap_data, ppt_data = _crop_content_by_answers(doc, mindmap_data, ppt_data, answers)

    # 构建个性化画像引入（最前章节）
    portrait_intro = await _build_portrait_intro(topic, user)

    # 构建骨架章节（立即可看），后台只补音频
    chapters, audio_tasks = _build_chapter_skeletons(doc, mindmap_data, ppt_data, plain=video_mode)

    # 画像引入置顶
    if portrait_intro:
        chapters.insert(0, portrait_intro)
        from types import SimpleNamespace as _SN
        intro_text = portrait_intro["slides"][0].get("intro_text", "")
        intro_resource = _SN(id=0, content=intro_text, resource_type="document")
        audio_tasks.insert(0, {"chapter_idx": 0, "resource": intro_resource})
        for t in audio_tasks[1:]:
            t["chapter_idx"] += 1

    record = await Presentation.create(user=user, topic=topic, status="ready")  # 骨架立即可看，音频后台补充

    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)
    html = _render_html(topic, chapters, template_path=TEMPLATE_VIDEO_PATH if video_mode else None)
    filename = f"{_safe_filename(topic)}_{uuid.uuid4().hex[:8]}.html"
    file_path = PRESENTATION_DIR / filename
    file_path.write_text(html, encoding="utf-8")

    record.file_url = f"/static/presentations/{filename}"
    record.chapters_json = json.dumps(chapters, ensure_ascii=False)
    record.total_duration_ms = sum(c.get("total_duration_ms", 0) for c in chapters)
    await record.save()

    # 保存到聊天历史
    if chat_group_id and chat_group_id > 0:
        from backend.src.models.chat_history_model import ChatHistory
        try:
            req_text = topic
            if answers:
                req_text = json.dumps({"topic": topic, "answers": answers}, ensure_ascii=False)
            res_json = json.dumps({
                "type": "presentation",
                "id": record.id,
                "topic": topic,
                "file_url": _versioned_presentation_url(record.file_url),
                "status": "ready",
                "_video_hint": "动态课件已生成，可立即查看",
            }, ensure_ascii=False)
            await ChatHistory.create(
                user=user,
                chat_group_id=chat_group_id,
                req=req_text,
                res=res_json,
            )
        except Exception:
            logger.exception("保存课件到聊天历史失败")

    # 立即推送通知，用户不用等音频
    try:
        await Notification.create(
            type="resource",
            title="课件已生成",
            content=f"「{topic}」课件已生成，共 {len(chapters)} 章，可立即查看（音频后台补充中）",
            target_url=f"/presentation?id={record.id}",
            target_user_id=user_id,
        )
    except Exception:
        logger.exception("课件通知推送失败")

    # 骨架已出，后台补音频
    asyncio_create_task(_add_audio_to_presentation(record.id, topic, user_id, voice, chapters, audio_tasks))

    logger.info("[课件] 骨架生成完成 topic=%s record=%d chapters=%d 耗时=%.1fs（音频后台补充中）",
                topic, record.id, len(chapters), _time.perf_counter() - _t_total)

    return {
        "id": record.id,
        "file_url": _versioned_presentation_url(record.file_url),
        "status": "ready",  # 骨架已可看，音频后台补充
        "template_version": PRESENTATION_TEMPLATE_VERSION,
        "message": "课件已生成，音频在后台补充中",
    }


async def get_presentation(presentation_id: int, user_id: int) -> dict | None:
    """查询课件状态"""
    record = await Presentation.filter(id=presentation_id, user_id=user_id).first()
    if not record:
        return None

    chapters = []
    if record.chapters_json:
        chapters = json.loads(record.chapters_json)

    return {
        "id": record.id,
        "topic": record.topic,
        "status": record.status,
        "file_url": _versioned_presentation_url(record.file_url),
        "template_version": PRESENTATION_TEMPLATE_VERSION,
        "chapters": chapters,
        "chapter_count": len(chapters),
        "total_duration_ms": record.total_duration_ms,
        "error_message": record.error_message,
        "created_at": str(record.created_at),
    }


async def list_presentations(user_id: int) -> list[dict]:
    """列出用户所有课件"""
    records = await Presentation.filter(user_id=user_id).order_by("-created_at").all()
    return [
        {
            "id": r.id,
            "topic": r.topic,
            "status": r.status,
            "chapter_count": len(json.loads(r.chapters_json)) if r.chapters_json else 0,
            "total_duration_ms": r.total_duration_ms,
            "file_url": _versioned_presentation_url(r.file_url),
            "template_version": PRESENTATION_TEMPLATE_VERSION,
            "created_at": str(r.created_at),
        }
        for r in records
    ]


async def delete_presentation(presentation_id: int, user_id: int) -> bool:
    """删除课件和 HTML 文件"""
    record = await Presentation.filter(id=presentation_id, user_id=user_id).first()
    if not record:
        return False

    if record.file_url:
        fp = _presentation_file_path(record.file_url)
        if fp and fp.exists():
            fp.unlink()

    await record.delete()
    return True


# ═══════════════════════════════════════════════
#  两阶段生成：骨架 → 音频
# ═══════════════════════════════════════════════

def _build_chapter_skeletons(doc=None, mindmap_data=None, ppt_data=None, plain: bool = False) -> tuple[list[dict], list[dict]]:
    """从资源构建无音频的章节骨架，返回 (chapters, audio_tasks)"""
    from backend.src.utils.mindmap import parse_mindmap_text

    chapters: list[dict] = []
    audio_tasks: list[dict] = []

    if doc:
        ch = _build_intro_skeleton(doc)
        chapters.append(ch)
        audio_tasks.append({"chapter_idx": len(chapters) - 1, "resource": doc})
    if mindmap_data:
        parsed = parse_mindmap_text(mindmap_data.content or "")
        svg = _mindmap_to_svg(parsed)
        ch = _build_mindmap_skeleton(mindmap_data, svg)
        chapters.append(ch)
        audio_tasks.append({"chapter_idx": len(chapters) - 1, "resource": mindmap_data})
    if ppt_data:
        ch = _build_ppt_skeleton(ppt_data, plain=plain)
        chapters.append(ch)
        audio_tasks.append({"chapter_idx": len(chapters) - 1, "resource": ppt_data})

    return chapters, audio_tasks


async def _add_audio_to_presentation(record_id: int, topic: str, user_id: int, voice: str,
                                      chapters: list[dict], audio_tasks: list[dict]):
    """骨架已出，优先复用旁白 DB 缓存，无缓存时才逐 slide 生成音频"""
    import hashlib
    import os as _os
    import time as _time
    from backend.src.models.narration_model import Narration
    from backend.src.service.narration_service import _generate_tts
    from backend.src.utils.tts_utils import parse_by_type as _parse_by_type, generate_audio_with_timestamps

    _t_start = _time.perf_counter()

    record = await Presentation.filter(id=record_id).first()
    if not record:
        return

    _flush_lock = asyncio.Lock()

    _TTS_CACHE = Path(__file__).parent.parent.parent / "static" / "audio" / "_cache"
    _TTS_CACHE.mkdir(parents=True, exist_ok=True)
    _tts_cache_key = lambda text, v: hashlib.md5(f"{text}_{v}".encode()).hexdigest()[:12]

    async def _tts_one_slide(text: str, resource_id: int, slide_idx: int) -> dict | None:
        """生成单张 slide 的 TTS 音频，返回 {audio_url, duration_ms, word_timestamps} 或 None"""
        if not text:
            return None
        cache_key = _tts_cache_key(text, voice)
        base_dir = Path(__file__).parent.parent.parent / "static" / "audio" / str(resource_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(base_dir / f"{cache_key}.mp3")
        json_path = str(base_dir / f"{cache_key}.json")
        audio_url = f"/static/audio/{resource_id}/{cache_key}.mp3"

        global_mp3 = str(_TTS_CACHE / f"{cache_key}.mp3")
        global_json = str(_TTS_CACHE / f"{cache_key}.json")

        if not (_os.path.exists(output_path) and _os.path.exists(json_path)):
            if _os.path.exists(global_mp3) and _os.path.exists(global_json):
                import shutil as _shutil
                _shutil.copy2(global_mp3, output_path)
                _shutil.copy2(global_json, json_path)

        if _os.path.exists(output_path) and _os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    word_timestamps = json.load(f)
                dur = _real_duration_from_timestamps(word_timestamps, int(len(text) / 4 * 1000))
                logger.info("[课件] TTS 缓存命中 resource=%d slide=%d text_len=%d", resource_id, slide_idx, len(text))
                return {"audio_url": audio_url, "duration_ms": dur, "word_timestamps": word_timestamps}
            except (json.JSONDecodeError, IOError):
                pass

        t0 = _time.perf_counter()
        word_timestamps = await _generate_tts(text, voice, output_path)
        if word_timestamps is None:
            return None

        t_cost = _time.perf_counter() - t0
        logger.info("[课件] TTS 生成耗时 resource=%d slide=%d text_len=%d cost=%.1fs", resource_id, slide_idx, len(text), t_cost)

        dur = _real_duration_from_timestamps(word_timestamps, int(len(text) / 4 * 1000))
        return {"audio_url": audio_url, "duration_ms": dur, "word_timestamps": word_timestamps}

    async def _process_chapter(task: dict):
        t_ch_start = _time.perf_counter()
        res = task["resource"]
        ch_idx = task["chapter_idx"]
        ch = chapters[ch_idx]
        resource_id = res.id if hasattr(res, 'id') else 0
        content = res.content if hasattr(res, 'content') else (res.get('content') if isinstance(res, dict) else '')
        resource_type = res.resource_type if hasattr(res, 'resource_type') else (res.get('resource_type', 'document') if isinstance(res, dict) else 'document')

        # 优先复用旁白 DB 缓存（_pre_generate_narration 在资源生成时已写入）
        narration = await Narration.filter(resource_id=resource_id, voice=voice).first()
        if narration and narration.slides_json:
            if resource_type == "document":
                _patch_intro_audio(ch, {"sections": narration.slides_json})
            elif resource_type == "ppt":
                _patch_ppt_audio(ch, {"sections": narration.slides_json})
            elif resource_type == "mindmap":
                _patch_mindmap_audio(ch, {"sections": narration.slides_json})
            ch["is_audio_ready"] = True
            t_flush = _time.perf_counter()
            partial_segments = _build_audio_segments(chapters)
            async with _flush_lock:
                await _flush(record, topic, chapters, "ready", segments=partial_segments)
            logger.info("[课件] 复用旁白缓存 chapter=%d resource=%d cost=%.1fs flush=%.1fs",
                        ch_idx, resource_id, _time.perf_counter() - t_ch_start, _time.perf_counter() - t_flush)
            return

        # 无旁白缓存 → 逐 slide 生成 TTS
        sections = _parse_by_type(content, resource_type)
        if not sections:
            ch["is_audio_ready"] = True
            async with _flush_lock:
                await _flush(record, topic, chapters, "ready")
            return

        slides = ch.get("slides", [])
        total_slides = len(sections)

        async def _one_slide(i: int, section: dict):
            text = section.get("text", "")
            result = await _tts_one_slide(text, resource_id, i)
            if result and i < len(slides):
                slides[i]["audio_url"] = result["audio_url"]
                slides[i]["duration_ms"] = result["duration_ms"]
                slides[i]["word_timestamps"] = result.get("word_timestamps", [])
            done_count = sum(1 for s in slides if s.get("audio_url"))
            ch["total_duration_ms"] = sum(s.get("duration_ms", 0) for s in slides)
            ch["audio_slide_count"] = done_count
            logger.info("[课件] slide 音频进度 chapter=%d %d/%d record=%d", ch_idx, done_count, total_slides, record_id)

        await asyncio.gather(*(_one_slide(i, s) for i, s in enumerate(sections)), return_exceptions=True)
        ch["is_audio_ready"] = True
        t_flush = _time.perf_counter()
        partial_segments = _build_audio_segments(chapters)
        async with _flush_lock:
            await _flush(record, topic, chapters, "ready", segments=partial_segments)
        logger.info("[课件] 音频已补 chapter=%d type=%s cost=%.1fs flush=%.1fs record=%d",
                    ch_idx, ch.get("type"), _time.perf_counter() - t_ch_start, _time.perf_counter() - t_flush, record_id)

    try:
        await asyncio.gather(*(_process_chapter(t) for t in audio_tasks))

        segments = _build_audio_segments(chapters)
        await _flush(record, topic, chapters, "ready", segments=segments)
        total_cost = _time.perf_counter() - _t_start
        audio_ready = sum(1 for c in chapters if c.get("is_audio_ready"))
        total_segments = len(segments)
        total_dur = sum(s.get("duration_ms", 0) for s in segments)
        logger.info("[课件] 完成 record=%d chapters=%d/%d segments=%d duration=%dms cost=%.1fs",
                    record_id, audio_ready, len(chapters), total_segments, total_dur, total_cost)
        await Notification.create(
            type="resource",
            title="课件制作完成",
            content=f"「{topic}」课件已生成，共 {len(chapters)} 章，可播放",
            target_url=f"/presentation?id={record_id}",
            target_user_id=user_id,
        )

    except Exception as e:
        logger.exception("[课件] 生成失败 record=%d", record_id)
        await _flush(record, topic, chapters, "failed")
        record = await Presentation.filter(id=record_id).first()
        if record:
            record.error_message = str(e)[:500]
            await record.save()
        await _notify_sse(record_id, {"status": "failed", "error": str(e)[:200]})
        await Notification.create(
            type="resource",
            title="课件生成失败",
            content=f"「{topic}」课件生成失败：{str(e)[:100]}",
            target_url="/resource",
            target_user_id=user_id,
        )


def _build_audio_segments(chapters: list[dict]) -> list[dict]:
    """从章节中提取播放列表（每 slide 独立音频，不合并）"""
    segments: list[dict] = []
    for ci, ch in enumerate(chapters):
        if ch.get("slides"):
            for si, slide in enumerate(ch["slides"]):
                if slide.get("audio_url"):
                    segments.append({
                        "url": slide["audio_url"],
                        "duration_ms": slide.get("duration_ms", 0),
                        "chapter": ci,
                        "slide": si,
                    })
        if ch.get("audio_segments"):
            for seg in ch["audio_segments"]:
                if seg.get("audio_url"):
                    segments.append({
                        "url": seg["audio_url"],
                        "duration_ms": seg.get("duration_ms", 0),
                        "chapter": ci,
                        "slide": 0,
                    })
    return segments


def _real_duration_from_timestamps(word_timestamps: list[dict], fallback_ms: int) -> int:
    """从词级时间戳计算真实音频时长（最后一个词的 offset + duration），无时间戳时回退到估算值"""
    if word_timestamps:
        last = word_timestamps[-1]
        real = last.get("offset_ms", 0) + last.get("duration_ms", 0)
        if real > 0:
            return real
    return fallback_ms


async def _flush(record, topic: str, chapters: list, status: str, segments: list[dict] | None = None):
    """更新 HTML 文件 + DB + SSE 通知"""
    # 检测当前 HTML 是否使用视频模板，保持模板一致
    _tp = None
    try:
        fp = _presentation_file_path(record.file_url)
        if fp and fp.exists():
            _head = fp.read_text(encoding="utf-8", errors="ignore")[:200]
            if "template-version:video-v3" in _head or "template-version:video-v2" in _head:
                _tp = TEMPLATE_VIDEO_PATH
    except Exception:
        pass
    html = _render_html(topic, chapters, segments or [], template_path=_tp)
    file_path = _presentation_file_path(record.file_url)
    if file_path is None:
        return
    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)
    file_path.write_text(html, encoding="utf-8")

    record = await Presentation.filter(id=record.id).first()
    if not record:
        return
    record.status = status
    record.chapters_json = json.dumps(chapters, ensure_ascii=False)
    record.total_duration_ms = sum(c.get("total_duration_ms", 0) for c in chapters)
    await record.save()

    await _notify_sse(record.id, {
        "status": status,
        "chapters": len(chapters),
        "file_url": _versioned_presentation_url(record.file_url),
    })


# ═══════════════════════════════════════════════
#  异步工具
# ═══════════════════════════════════════════════

def asyncio_create_task(coro):
    """安全创建后台任务"""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        task = asyncio.ensure_future(coro, loop=loop)
        return task
    except RuntimeError:
        pass


# ═══════════════════════════════════════════════
#  资源获取
# ═══════════════════════════════════════════════

async def _fetch_resources(topic: str, user_id: int) -> tuple:
    records = await GeneratedResource.filter(
        user_id=user_id, topic=topic,
    ).order_by("-created_at").all()

    doc = mindmap_data = ppt_data = None
    for r in records:
        if r.resource_type == "document" and not doc:
            doc = r
        elif r.resource_type == "mindmap" and not mindmap_data:
            mindmap_data = r
        elif r.resource_type == "ppt" and not ppt_data:
            ppt_data = r
    return doc, mindmap_data, ppt_data


# ═══════════════════════════════════════════════
#  骨架构建 — 只解析内容，不生成音频
# ═══════════════════════════════════════════════

async def _build_portrait_intro(topic: str, user) -> dict | None:
    """根据用户画像生成个性化学习引入（第一章节）"""
    from backend.src.models.portraitmodel import User_picture

    picture = None
    try:
        picture = await user.picture
    except Exception:
        pass
    if not picture:
        picture = await User_picture.filter(id=getattr(user, 'picture_id', None) or 0).first()

    portrait_parts = []
    if user.major:
        portrait_parts.append(f"专业：{user.major}")
    if user.grade:
        portrait_parts.append(f"年级：{user.grade}")
    if picture:
        if picture.learning_goal:
            portrait_parts.append(f"学习目标：{picture.learning_goal}")
        if picture.cognition:
            portrait_parts.append(f"认知风格：{picture.cognition}")
        if picture.personality_tags:
            try:
                tags = json.loads(picture.personality_tags)
                portrait_parts.append(f"性格：{'、'.join(tags)}")
            except Exception:
                pass
        if picture.profile_summary:
            portrait_parts.append(f"学习画像：{picture.profile_summary}")
    portrait_text = "；".join(portrait_parts) if portrait_parts else "暂无画像数据"

    prompt = fill_prompt(
        load_prompt("presentation/portrait_intro"),
        topic=topic,
        portrait_text=portrait_text,
    )

    try:
        resp = await llm.ainvoke(prompt)
        intro_text = resp.content.strip()
        if intro_text.startswith("```"):
            intro_text = re.sub(r"^```\w*\n?", "", intro_text)
            intro_text = re.sub(r"\n?```$", "", intro_text)
    except Exception:
        logger.exception("生成画像引入失败")
        return None

    if not intro_text or len(intro_text) < 10:
        return None

    content_html = _md_to_html(intro_text)
    estimated_dur = int(len(intro_text) / 4 * 1000)

    return {
        "type": "intro",
        "title": f"学习引入",
        "slides": [{
            "title": topic,
            "intro_text": intro_text,
            "content_html": content_html,
            "audio_url": None,
            "duration_ms": estimated_dur,
            "word_timestamps": [],
        }],
        "total_duration_ms": estimated_dur,
        "is_audio_ready": False,
    }


def _build_intro_skeleton(record) -> dict:
    content = record.content or ""
    raw_parts = re.split(r"\n(?=## )", content.strip())
    if len(raw_parts) <= 1:
        raw_parts = re.split(r"\n(?=# )", content.strip())

    slides = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        html = _md_to_html(part)
        lines = part.split("\n")
        title = lines[0].lstrip("#").strip()
        text_len = len(part)
        estimated_dur = int(text_len / 4 * 1000)
        slides.append({
            "title": title,
            "content_html": html,
            "audio_url": None,
            "duration_ms": estimated_dur,
            "word_timestamps": [],
        })

    total_dur = sum(s.get("duration_ms", 0) for s in slides)
    return {
        "type": "intro",
        "title": record.topic,
        "slides": slides,
        "total_duration_ms": total_dur,
        "is_audio_ready": False,
    }


def _build_mindmap_skeleton(record, svg: str) -> dict:
    return {
        "type": "mindmap",
        "title": record.topic,
        "content_html": svg,
        "audio_segments": [],
        "total_duration_ms": 30000,
        "is_audio_ready": False,
    }


def _build_ppt_skeleton(record, plain: bool = False) -> dict:
    from backend.src.utils.tts_utils import parse_slides
    content = record.content or ""
    slides_meta = parse_slides(content)

    slides = []
    for meta in slides_meta:
        bullets = meta.get("bullets") or []
        text = meta.get("text", "")
        estimated_dur = len(text) / 4 * 1000 if text else 5000
        slide = {
            "title": meta.get("title", ""),
            "text": meta.get("text", ""),
            "bullets": bullets,
            "blocks": meta.get("blocks", []),
            "layout": meta.get("layout", "content_cards"),
            "theme": meta.get("theme", "academic_blue"),
            "palette": meta.get("palette", []),
            "visual": meta.get("visual", {}),
            "notes": meta.get("notes", ""),
            "audio_url": None,
            "duration_ms": int(estimated_dur),
            "word_timestamps": [],
        }
        if plain:
            slide["video_safe"] = True
        slides.append(slide)

    total_dur = sum(s.get("duration_ms", 0) for s in slides)
    return {
        "type": "ppt",
        "title": record.topic,
        "slides": slides,
        "total_duration_ms": total_dur,
        "is_audio_ready": False,
    }


# ═══════════════════════════════════════════════
#  音频补丁 — 把 narration 结果注入骨架
# ═══════════════════════════════════════════════

def _patch_intro_audio(ch: dict, narration: dict):
    segments = (narration or {}).get("sections", [])
    # 按 index 建立索引，避免 TTS 部分段失败导致位置错位
    seg_by_idx = {seg["index"]: seg for seg in segments if seg and "index" in seg}
    slides = ch.get("slides", [])
    for i, slide in enumerate(slides):
        seg = seg_by_idx.get(i)
        if seg:
            slide["audio_url"] = seg.get("audio_url")
            slide["duration_ms"] = seg.get("duration_ms", slide["duration_ms"])
            slide["word_timestamps"] = seg.get("word_timestamps", [])
    # total_duration_ms 只统计有音频的幻灯片（含无音频幻灯片的骨架估值）
    total = sum(s.get("duration_ms", 0) for s in slides)
    ch["total_duration_ms"] = total
    ch["audio_slide_count"] = sum(1 for s in slides if s.get("audio_url"))


def _patch_mindmap_audio(ch: dict, narration: dict):
    segments = (narration or {}).get("sections", [])
    ch["audio_segments"] = segments
    ch["total_duration_ms"] = sum(s.get("duration_ms", 0) for s in segments)


def _patch_ppt_audio(ch: dict, narration: dict):
    segments = (narration or {}).get("sections", [])
    seg_by_idx = {seg["index"]: seg for seg in segments if seg and "index" in seg}
    slides = ch.get("slides", [])
    for i, slide in enumerate(slides):
        seg = seg_by_idx.get(i)
        if seg:
            slide["audio_url"] = seg.get("audio_url")
            slide["duration_ms"] = seg.get("duration_ms", slide["duration_ms"])
            slide["word_timestamps"] = seg.get("word_timestamps", [])
    total = sum(s.get("duration_ms", 0) for s in slides)
    ch["total_duration_ms"] = total
    ch["audio_slide_count"] = sum(1 for s in slides if s.get("audio_url"))


# ═══════════════════════════════════════════════
#  Markdown → HTML
# ═══════════════════════════════════════════════

def _md_to_html(md: str) -> str:
    lines = md.strip().split("\n")
    parts = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                parts.append("</ul>")
                in_list = False
            continue
        if stripped.startswith("# "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h1>{_escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h2>{_escape(stripped[3:])}</h2>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            text = _inline_bold(_escape(stripped[2:]))
            parts.append(f"<li>{text}</li>")
        elif stripped.startswith("> "):
            parts.append(f"<blockquote>{_escape(stripped[2:])}</blockquote>")
        else:
            if in_list:
                parts.append("</ul>")
                in_list = False
            text = _inline_bold(_escape(stripped))
            parts.append(f"<p>{text}</p>")
    if in_list:
        parts.append("</ul>")
    return "".join(parts)


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _inline_bold(text: str) -> str:
    import re
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


# ═══════════════════════════════════════════════
#  思维导图 → SVG
# ═══════════════════════════════════════════════

_NODE_COLORS = ["#4f8cff", "#a78bfa", "#34d399", "#f59e0b", "#ef4444", "#ec4899"]
_NODE_W = 140
_NODE_H = 42
_V_SPACING = 80
_H_SPACING = 24


def _mindmap_to_svg(data: dict) -> str:
    if not data or not data.get("topic"):
        return "<svg></svg>"
    data["_depth"] = 0
    _calc_leaf_x(data, 0)
    total_leaves = _count_leaves(data)
    _center_parents(data)

    pw = max(total_leaves * (_NODE_W + _H_SPACING) + 60, 600)
    ph = max((_max_depth(data) + 1) * (_NODE_H + _V_SPACING) + 40, 400)

    def to_px(node):
        leaves_before = _count_leaves_before(node)
        return leaves_before * (_NODE_W + _H_SPACING) + (_NODE_W / 2) + 30, node.get("_depth", 0) * (_NODE_H + _V_SPACING) + 30

    parts = [f'<svg viewBox="0 0 {pw} {ph}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">']
    parts.append(f'<rect width="{pw}" height="{ph}" fill="transparent"/>')

    def walk(node):
        x, y = to_px(node)
        depth = node.get("_depth", 0)
        color = _NODE_COLORS[depth % len(_NODE_COLORS)]
        children = node.get("children", [])

        if "_parent_x" in node:
            px = node["_parent_x"]
            py = node["_parent_y"]
            mid_y = (y + py) / 2
            parts.append(f'<path d="M{px},{py} L{px},{mid_y} L{x},{mid_y} L{x},{y}" stroke="{color}" stroke-width="1.5" fill="none" opacity="0.4"/>')

        text = _escape(node.get("topic", ""))
        rx = x - _NODE_W / 2
        ry = y - _NODE_H / 2
        parts.append(f'<rect x="{rx}" y="{ry}" width="{_NODE_W}" height="{_NODE_H}" rx="8" fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x}" y="{y + 5}" text-anchor="middle" fill="#e0e0e0" font-size="13" font-family="Microsoft YaHei, sans-serif">{text}</text>')

        for child in children:
            child["_parent_x"] = x
            child["_parent_y"] = y + _NODE_H / 2
            walk(child)

    data["_depth"] = 0
    walk(data)
    parts.append("</svg>")
    return "".join(parts)


def _calc_leaf_x(node, x_start=0):
    children = node.get("children", [])
    if not children:
        node["_leaf_x"] = x_start
        return x_start + 1
    for child in children:
        x_start = _calc_leaf_x(child, x_start)
    return x_start


def _center_parents(node):
    children = node.get("children", [])
    if not children:
        return
    for child in children:
        child["_depth"] = node.get("_depth", 0) + 1
        _center_parents(child)
    leaves = _count_leaves(node)
    first_x = _first_leaf_x(node)
    node["_leaf_x"] = first_x + (leaves - 1) / 2


def _count_leaves(node) -> int:
    children = node.get("children", [])
    return 1 if not children else sum(_count_leaves(c) for c in children)


def _count_leaves_before(node) -> int:
    return int(node.get("_leaf_x", 0))


def _first_leaf_x(node) -> int:
    children = node.get("children", [])
    if not children:
        return node.get("_leaf_x", 0)
    return _first_leaf_x(children[0])


def _max_depth(node) -> int:
    children = node.get("children", [])
    if not children:
        return node.get("_depth", 0)
    return max(_max_depth(c) for c in children)


# ═══════════════════════════════════════════════
#  HTML 渲染
# ═══════════════════════════════════════════════

def _versioned_presentation_url(url: str | None) -> str:
    if not url:
        return ""
    base = str(url).split("?", 1)[0]
    return f"{base}?v={PRESENTATION_TEMPLATE_VERSION}"


def _presentation_file_path(url: str | None) -> Path | None:
    if not url:
        return None
    fname = str(url).split("?", 1)[0].rsplit("/", 1)[-1]
    if not fname:
        return None
    return PRESENTATION_DIR / fname


def _presentation_file_matches_template(url: str | None, expected_tag: str | None = None) -> bool:
    path = _presentation_file_path(url)
    if not path or not path.exists():
        return False
    tag = expected_tag or f"template-version:{PRESENTATION_TEMPLATE_VERSION}"
    try:
        return tag in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def _render_video_slides_html(sections: list[dict]) -> str:
    """预渲染视频用纯文字 HTML，不依赖 JS，无任何卡片/装饰"""
    import re as _re

    def _extract_texts(sl: dict) -> list[str]:
        """从 slide 数据中统一提取要点文字，兼容旧版 bullets 和新版 blocks"""
        bullets = sl.get("bullets") or []
        if bullets:
            return [_re.sub(r"<!--[\s\S]*?-->", "", str(b).strip()) for b in bullets if str(b).strip()]

        # 新版 schema：blocks = [{"type": "key_point", "text": "..."}, ...]
        blocks = sl.get("blocks") or []
        if blocks:
            texts = []
            for blk in blocks:
                if isinstance(blk, dict):
                    t = str(blk.get("text", "")).strip()
                else:
                    t = str(blk).strip()
                if t and not t.startswith("<!--"):
                    texts.append(t)
            if texts:
                return texts

        # 回退：从 text 字段按句子拆分
        text = sl.get("text", "")
        return [l.strip() for l in text.replace("。", "\n").replace("；", "\n").split("\n") if l.strip()] if text else []

    parts: list[str] = []
    for sec in sections:
        sec_type = sec.get("type", "")
        if sec_type == "ppt":
            for sl in sec.get("slides", []):
                title = _re.sub(r"^##\s*", "", sl.get("title", ""))
                title = _re.sub(r"<!--[\s\S]*?-->", "", title).strip()
                texts = _extract_texts(sl)
                lis = "".join(
                    f"<li>{t}</li>"
                    for t in texts[:8] if t
                )
                parts.append(f'<div class="slide"><h2>{title}</h2><ul>{lis}</ul></div>')
        elif sec_type in ("intro", "reading"):
            for sl in sec.get("slides", []):
                title = _re.sub(r"^##\s*", "", sl.get("title", ""))
                title = _re.sub(r"<!--[\s\S]*?-->", "", title).strip()
                text = sl.get("text", "")
                paras = "".join(f"<p>{p.strip()}</p>" for p in text.split("。") if p.strip())
                parts.append(f'<div class="slide"><h2>{title}</h2>{paras}</div>')
        elif sec_type == "mindmap":
            html = sec.get("content_html", "")
            parts.append(f'<div class="slide"><h2>思维导图</h2><div id="mindmap-container">{html}</div></div>')
    return "\n".join(parts)


def _render_video_slides_html(sections: list[dict]) -> str:
    import re as _re

    def clean(value) -> str:
        text = str(value or "")
        text = _re.sub(r"<!--[\s\S]*?-->", " ", text)
        text = _re.sub(r"</?[^>\n]+>", " ", text)
        text = _re.sub(r"^\s*(layout|theme|visual)\s*:\s*.*$", " ", text, flags=_re.IGNORECASE | _re.MULTILINE)
        text = _re.sub(r"\s+", " ", text).strip()
        return text

    def safe(value) -> str:
        return _escape(clean(value))

    def slide_blocks(sl: dict) -> list[str]:
        texts: list[str] = []
        for block in sl.get("blocks") or []:
            raw = block.get("text") if isinstance(block, dict) else block
            text = clean(raw)
            if text:
                texts.append(text)
        if not texts:
            texts = [clean(item) for item in (sl.get("bullets") or [])]
            texts = [item for item in texts if item]
        if not texts:
            raw_text = clean(sl.get("text", ""))
            texts = [item.strip() for item in _re.split(r"[。；;]\s*|\n+", raw_text) if item.strip()]
        return texts[:8]

    def visual_html(sl: dict, block_id: str) -> str:
        visual = sl.get("visual") or {}
        kind = clean(visual.get("type") or "diagram")
        caption = safe(visual.get("caption") or visual.get("query") or sl.get("title"))
        return (
            f'<div class="video-visual video-visual--{_escape(kind)}" data-narration-block="{block_id}">'
            '<div class="visual-ring"></div><div class="visual-line visual-line--a"></div>'
            '<div class="visual-line visual-line--b"></div><div class="visual-dot visual-dot--a"></div>'
            '<div class="visual-dot visual-dot--b"></div><div class="visual-dot visual-dot--c"></div>'
            f'<p>{caption}</p></div>'
        )

    def item_html(tag: str, text: str, block_id: str, index: int | None = None) -> str:
        badge = f"<b>{index}</b>" if index is not None else ""
        return f'<{tag} data-narration-block="{block_id}">{badge}<span>{_escape(text)}</span></{tag}>'

    def render_ppt_slide(sl: dict, slide_index: int) -> str:
        title = safe(sl.get("title") or f"Slide {slide_index + 1}")
        layout = clean(sl.get("layout") or "content_cards")
        items = slide_blocks(sl)
        title_block = f"ppt-{slide_index}-title"

        if layout == "process_steps":
            cards = "".join(item_html("article", item, f"ppt-{slide_index}-block-{i}", i + 1) for i, item in enumerate(items[:4]))
            body = f'<div class="video-process">{cards}</div>'
        elif layout == "comparison":
            left = "".join(item_html("li", item, f"ppt-{slide_index}-left-{i}") for i, item in enumerate(items[::2][:3]))
            right = "".join(item_html("li", item, f"ppt-{slide_index}-right-{i}") for i, item in enumerate(items[1::2][:3]))
            body = (
                '<div class="video-compare">'
                f'<section><h3>A</h3><ul>{left}</ul></section>'
                f'<section><h3>B</h3><ul>{right}</ul></section>'
                '</div>'
            )
        elif layout == "formula_focus":
            formula = next((item for item in items if "=" in item or "$" in item or "\\" in item), items[0] if items else "")
            rest = [item for item in items if item != formula][:4]
            points = "".join(item_html("li", item, f"ppt-{slide_index}-formula-{i}") for i, item in enumerate(rest))
            body = (
                f'<div class="video-formula" data-narration-block="ppt-{slide_index}-formula-main">{_escape(formula)}</div>'
                f'<ul class="video-points">{points}</ul>'
            )
        elif layout == "concept_visual":
            bullets = "".join(item_html("li", item, f"ppt-{slide_index}-point-{i}") for i, item in enumerate(items[:5]))
            body = (
                '<div class="video-split">'
                f'<ul class="video-points">{bullets}</ul>'
                f'{visual_html(sl, f"ppt-{slide_index}-visual")}'
                '</div>'
            )
        else:
            cards = "".join(item_html("article", item, f"ppt-{slide_index}-card-{i}", i + 1) for i, item in enumerate(items[:6]))
            body = f'<div class="video-card-grid">{cards}</div>'

        return f'<div class="slide video-slide video-slide--{_escape(layout)}"><h2 data-narration-block="{title_block}">{title}</h2>{body}</div>'

    parts: list[str] = []
    ppt_index = 0
    for sec in sections:
        sec_type = sec.get("type", "")
        if sec_type == "ppt":
            for sl in sec.get("slides", []):
                parts.append(render_ppt_slide(sl, ppt_index))
                ppt_index += 1
        elif sec_type in ("intro", "reading"):
            for index, sl in enumerate(sec.get("slides", [])):
                title = safe(sl.get("title") or sec.get("title"))
                text = clean(sl.get("intro_text") or sl.get("text") or sl.get("content_html"))
                paras = "".join(f'<p data-narration-block="intro-{index}-{i}">{_escape(p.strip())}</p>' for i, p in enumerate(_re.split(r"[。；;]\s*", text)) if p.strip())
                parts.append(f'<div class="slide video-slide video-slide--intro"><h2 data-narration-block="intro-{index}-title">{title}</h2><div class="intro-content">{paras}</div></div>')
        elif sec_type == "mindmap":
            html = sec.get("content_html", "")
            parts.append(f'<div class="slide video-slide video-slide--mindmap"><h2 data-narration-block="mindmap-title">思维导图</h2><div id="mindmap-container" data-narration-block="mindmap-body">{html}</div></div>')
    return "\n".join(parts)


def _render_html(topic: str, sections: list[dict], segments: list[dict] | None = None, template_path: Path | None = None) -> str:
    template = (template_path or TEMPLATE_PATH).read_text(encoding="utf-8")
    sections_json = json.dumps(sections, ensure_ascii=False, indent=2)
    topic_json = json.dumps(topic, ensure_ascii=False)
    segments_json = json.dumps(segments or [], ensure_ascii=False)

    is_video = template_path == TEMPLATE_VIDEO_PATH
    slides_html = _render_video_slides_html(sections) if is_video else ""
    html = template.replace("{{SECTIONS}}", sections_json)
    html = html.replace("{{TITLE_JSON}}", topic_json)  # 必须在 {{TITLE}} 之前替换，否则 {{TITLE}} 会匹配到 {{TITLE_JSON}} 的前缀
    html = html.replace("{{TITLE}}", _escape(topic))
    html = html.replace("{{AUDIO_SEGMENTS}}", segments_json)
    html = html.replace("{{SLIDES_HTML}}", slides_html)
    version_tag = "<!-- template-version:video-v3 -->" if is_video else f"<!-- template-version:{PRESENTATION_TEMPLATE_VERSION} -->"
    return f"{version_tag}\n{html}"


def _safe_filename(topic: str) -> str:
    return "".join(c for c in topic if c.isalnum() or c in " _-")[:30]

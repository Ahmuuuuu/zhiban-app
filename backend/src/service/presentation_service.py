"""学习课件 HTML 生成服务 — 先出骨架，后台补音频"""

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
_sse_queues: dict[int, list] = {}


def _subscribe_sse(presentation_id: int):
    q = []
    _sse_queues.setdefault(presentation_id, []).append(q)
    return q


def _unsubscribe_sse(presentation_id: int, q: list):
    queues = _sse_queues.get(presentation_id, [])
    if q in queues:
        queues.remove(q)
    if not queues:
        _sse_queues.pop(presentation_id, None)


async def _notify_sse(presentation_id: int, data: dict):
    for q in _sse_queues.get(presentation_id, []):
        q.append(data)


# ═══════════════════════════════════════════════
#  对外 API
# ═══════════════════════════════════════════════

async def generate(topic: str, user_id: int, voice: str = "zh-CN-XiaoxiaoNeural",
                  chapters: list[str] | None = None, answers: dict | None = None,
                  chat_group_id: int = 0) -> dict:
    """创建课件记录 + 立即出骨架 + 后台补音频（可选 answers 裁剪内容）"""
    from backend.src.models.usermodel import User
    user = await User.filter(id=user_id).first()
    if not user:
        return {"error": "用户不存在"}

    doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
    if not any([doc, mindmap_data, ppt_data]):
        return {"error": f"话题「{topic}」暂无已生成的资源，请先通过 /resource/generate 生成"}

    # 用户作答 → 裁剪内容
    if answers:
        doc, mindmap_data, ppt_data = _crop_content_by_answers(doc, mindmap_data, ppt_data, answers)

    record = await Presentation.create(user=user, topic=topic, status="generating")

    # 保存初始骨架 HTML
    html = _render_html(topic, [])
    filename = f"{_safe_filename(topic)}_{uuid.uuid4().hex[:8]}.html"
    file_path = PRESENTATION_DIR / filename
    file_path.write_text(html, encoding="utf-8")

    record.file_url = f"/static/presentations/{filename}"
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
                "file_url": record.file_url,
                "status": "generating",
                "_video_hint": "动态课件已生成",
            }, ensure_ascii=False)
            await ChatHistory.create(
                user=user,
                chat_group_id=chat_group_id,
                req=req_text,
                res=res_json,
            )
        except Exception:
            logger.exception("保存课件到聊天历史失败")

    # 后台两阶段：先出骨架（秒级），再补音频
    asyncio_create_task(_generate_skeleton_then_audio(record.id, topic, user_id, voice, chapters, doc, mindmap_data, ppt_data))

    return {
        "id": record.id,
        "file_url": record.file_url,
        "status": "generating",
        "message": "课件骨架已生成，音频正在后台补充",
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
        "file_url": record.file_url,
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
            "file_url": r.file_url,
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
        fname = record.file_url.rsplit("/", 1)[-1]
        fp = PRESENTATION_DIR / fname
        if fp.exists():
            fp.unlink()

    await record.delete()
    return True


# ═══════════════════════════════════════════════
#  两阶段生成：骨架 → 音频
# ═══════════════════════════════════════════════

async def _generate_skeleton_then_audio(record_id: int, topic: str, user_id: int, voice: str,
                                         selected_chapters: list[str] | None = None,
                                         doc=None, mindmap_data=None, ppt_data=None):
    """阶段1：秒出骨架（不阻塞等音频）→ 阶段2：逐章补音频"""
    from backend.src.service.narration_service import narrate_resource, narrate_content
    from backend.src.utils.mindmap import parse_mindmap_text

    record = await Presentation.filter(id=record_id).first()
    if not record:
        return

    # 未传入则自行拉取
    if doc is None and mindmap_data is None and ppt_data is None:
        doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
    chapters = []
    # 每章：resource 对象 + 是否裁剪过（决定音频来源）
    audio_tasks: list[dict] = []

    try:
        # ── 阶段1：构建无音频骨架 ──
        if selected_chapters is None or "intro" in selected_chapters:
            if doc:
                ch = _build_intro_skeleton(doc)
                chapters.append(ch)
                audio_tasks.append({"chapter_idx": len(chapters) - 1, "resource": doc})
        if selected_chapters is None or "mindmap" in selected_chapters:
            if mindmap_data:
                parsed = parse_mindmap_text(mindmap_data.content or "")
                svg = _mindmap_to_svg(parsed)
                ch = _build_mindmap_skeleton(mindmap_data, svg)
                chapters.append(ch)
                audio_tasks.append({"chapter_idx": len(chapters) - 1, "resource": mindmap_data})
        if selected_chapters is None or "ppt" in selected_chapters:
            if ppt_data:
                ch = _build_ppt_skeleton(ppt_data)
                chapters.append(ch)
                audio_tasks.append({"chapter_idx": len(chapters) - 1, "resource": ppt_data})

        # 骨架立即可看，不阻塞等任何音频（阶段2预生成会提前缓存旁白）
        await _flush(record, topic, chapters, "generating")
        logger.info("[课件] 骨架已出 record=%d chapters=%d", record_id, len(chapters))

        # ── 阶段2：逐章补音频（预生成缓存命中则秒返）──
        for task in audio_tasks:
            res = task["resource"]
            try:
                if isinstance(res, SimpleNamespace):
                    narration = await narrate_content(res.content, res.resource_type, voice, res.id)
                else:
                    narration = await narrate_resource(res.id, voice)
            except Exception:
                logger.exception("[课件] 旁白生成失败 resource=%d", res.id)
                continue

            idx = task["chapter_idx"]
            ch = chapters[idx]
            ch_type = ch.get("type")

            if ch_type == "intro":
                _patch_intro_audio(ch, narration)
            elif ch_type == "mindmap":
                _patch_mindmap_audio(ch, narration)
            elif ch_type == "ppt":
                _patch_ppt_audio(ch, narration)

            ch["is_audio_ready"] = True
            await _flush(record, topic, chapters, "generating")
            logger.info("[课件] 音频已补 chapter=%d type=%s record=%d", idx, ch_type, record_id)

        await _flush(record, topic, chapters, "ready")
        logger.info("[课件] 全部完成 record=%d", record_id)
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


async def _flush(record, topic: str, chapters: list, status: str):
    """更新 HTML 文件 + DB + SSE 通知"""
    html = _render_html(topic, chapters)
    fname = record.file_url.rsplit("/", 1)[-1]
    file_path = PRESENTATION_DIR / fname
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
        "file_url": record.file_url,
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


def _build_ppt_skeleton(record) -> dict:
    from backend.src.utils.tts_utils import parse_slides
    content = record.content or ""
    slides_meta = parse_slides(content)

    slides = []
    for meta in slides_meta:
        bullets = meta.get("bullets") or []
        text = meta.get("text", "")
        estimated_dur = len(text) / 4 * 1000 if text else 5000
        slides.append({
            "title": meta.get("title", ""),
            "bullets": bullets,
            "notes": meta.get("notes", ""),
            "audio_url": None,
            "duration_ms": int(estimated_dur),
            "word_timestamps": [],
        })

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
    slides = ch.get("slides", [])
    for i, slide in enumerate(slides):
        seg = segments[i] if i < len(segments) else None
        if seg:
            slide["audio_url"] = seg.get("audio_url")
            slide["duration_ms"] = seg.get("duration_ms", slide["duration_ms"])
            slide["word_timestamps"] = seg.get("word_timestamps", [])
    total = sum(s.get("duration_ms", 0) for s in slides)
    ch["total_duration_ms"] = total


def _patch_mindmap_audio(ch: dict, narration: dict):
    segments = (narration or {}).get("sections", [])
    ch["audio_segments"] = segments
    ch["total_duration_ms"] = sum(s.get("duration_ms", 0) for s in segments)


def _patch_ppt_audio(ch: dict, narration: dict):
    segments = (narration or {}).get("sections", [])
    slides = ch.get("slides", [])
    for i, slide in enumerate(slides):
        seg = segments[i] if i < len(segments) else None
        if seg:
            slide["audio_url"] = seg.get("audio_url")
            slide["duration_ms"] = seg.get("duration_ms", slide["duration_ms"])
            slide["word_timestamps"] = seg.get("word_timestamps", [])
    total = sum(s.get("duration_ms", 0) for s in slides)
    ch["total_duration_ms"] = total


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

def _render_html(topic: str, sections: list[dict]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    sections_json = json.dumps(sections, ensure_ascii=False, indent=2)
    topic_json = json.dumps(topic, ensure_ascii=False)

    html = template.replace("{{SECTIONS}}", sections_json)
    html = html.replace("{{TITLE}}", _escape(topic))
    html = html.replace("{{TITLE_JSON}}", topic_json)
    return html


def _safe_filename(topic: str) -> str:
    return "".join(c for c in topic if c.isalnum() or c in " _-")[:30]

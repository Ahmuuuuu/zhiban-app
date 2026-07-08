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
from backend.src.models.chat_history_model import ChatHistory
from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.utils.exceptions import ServiceError
from backend.src.utils.chat_utils import allocate_chat_group_id
from backend.src.utils.redis_client import notify_sse as _redis_notify_sse, subscribe_sse, unsubscribe_sse
from backend.src.utils.constants import PRESENTATIONS_DIR

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent / "ai_core" / "prompts" / "presentation" / "template.html"
TEMPLATE_VIDEO_PATH = Path(__file__).parent.parent / "ai_core" / "prompts" / "presentation" / "template_video.html"
PRESENTATION_TEMPLATE_VERSION = "visual-v6"
VIDEO_TEMPLATE_VERSION = "video-v4"


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
                {"label": "极速概览，了解核心概念", "value": "overview"},
                {"label": "标准讲解，理解原理和应用", "value": "standard"},
                {"label": "逐页详解，包含推导和案例", "value": "deep"},
            ],
        }]

    # 写入聊天历史 — 新对话自动分配 chat_group_id
    chat_group_id = chat_group_id if chat_group_id and chat_group_id > 0 else await allocate_chat_group_id(user_id)
    logger.info("generate_questions() user_id=%d chat_group_id=%d topic=%s", user_id, chat_group_id, topic[:60])
    try:
        await ChatHistory.create(
            user=user,
            chat_group_id=chat_group_id,
            req="",
            res=json.dumps({"type": "presentation_questions", "topic": topic, "questions": questions_list, "_video_hint": "动态课件"}, ensure_ascii=False),
        )
    except Exception:
        logger.exception("保存追问到聊天历史失败")

    return {"questions": questions_list, "chat_group_id": chat_group_id}


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
        resp = await asyncio.wait_for(llm.ainvoke(prompt), timeout=8)
        raw = resp.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        questions_data = json.loads(raw)
        return questions_data.get("questions", [])
    except (asyncio.TimeoutError, json.JSONDecodeError):
        logger.warning("AI 问题生成超时或解析失败，降级为默认问题")
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
        resp = await asyncio.wait_for(llm.ainvoke(prompt), timeout=8)
        raw = resp.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        questions_data = json.loads(raw)
        return questions_data.get("questions", [])
    except (asyncio.TimeoutError, json.JSONDecodeError):
        logger.warning("AI 问题（话题模式）生成超时或解析失败")
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
            {"label": "极速概览，了解核心概念", "value": "overview"},
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
_sse_forward_tasks: dict[int, asyncio.Task] = {}


def _subscribe_sse(presentation_id: int) -> asyncio.Queue:
    """订阅课件 SSE（返回 asyncio.Queue，兼容现有路由）。
    同时在 redis_client 注册订阅，跨进程消息通过转发器到达本地队列。"""
    q = asyncio.Queue()
    _sse_queues.setdefault(presentation_id, []).append(q)

    # 注册 redis_client 统一订阅，使跨进程消息能转发到此队列
    _rq = subscribe_sse(f"pres:{presentation_id}")
    _chan = f"pres:{presentation_id}"

    async def _forward_loop():
        """将 redis_client 订阅队列中的消息转发到 asyncio.Queue"""
        try:
            while _chan in {c: qs for c, qs in _sse_queues.items() if q in qs}:
                while _rq:
                    msg = _rq.pop(0)
                    q.put_nowait(msg)
                await asyncio.sleep(0.2)
        except Exception:
            logger.debug("SSE 转发结束 presentation_id=%s", presentation_id)

    _sse_forward_tasks[presentation_id] = asyncio.ensure_future(_forward_loop())
    return q


def _unsubscribe_sse(presentation_id: int, q: asyncio.Queue):
    queues = _sse_queues.get(presentation_id, [])
    if q in queues:
        queues.remove(q)
    if not queues:
        _sse_queues.pop(presentation_id, None)
        # 清理 redis_client 订阅
        unsubscribe_sse(f"pres:{presentation_id}", q)
    # 取消转发任务
    task = _sse_forward_tasks.pop(presentation_id, None)
    if task and not task.done():
        task.cancel()


async def _notify_sse(presentation_id: int, data: dict):
    """统一走 redis_client 通知（本地队列 + Redis Pub/Sub + Stream）"""
    await _redis_notify_sse(f"pres:{presentation_id}", data)


def _push_progress(presentation_id: int, step: str, label: str, status: str = "running", elapsed_ms: int | None = None):
    """推送生成进度（统一走 redis_client，异步 fire-and-forget）"""
    event = {"type": "progress", "step": step, "label": label, "status": status, "elapsed_ms": elapsed_ms}
    asyncio.ensure_future(_redis_notify_sse(f"pres:{presentation_id}", event))


# ═══════════════════════════════════════════════
#  对外 API
# ═══════════════════════════════════════════════

async def generate(topic: str, user_id: int, voice: str = "zh-CN-XiaoxiaoNeural",
                  chapters: list[str] | None = None, answers: dict | None = None,
                  chat_group_id: int = 0, video_mode: bool = False,
                  background: bool = False) -> dict:
    """创建课件。background=True 立即返回 {id, status:'generating'}，进度走 SSE；background=False 同步等完整结果"""
    import time as _time
    from datetime import datetime, timedelta
    from backend.src.models.usermodel import User
    from backend.src.utils.mindmap import parse_mindmap_text

    user = await User.filter(id=user_id).first()
    if not user:
        raise ServiceError("用户不存在")

    # 去重
    _expected_tag = f"template-version:{VIDEO_TEMPLATE_VERSION}" if video_mode else f"template-version:{PRESENTATION_TEMPLATE_VERSION}"
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
            "template_version": VIDEO_TEMPLATE_VERSION if video_mode else PRESENTATION_TEMPLATE_VERSION,
        }

    # 立即创建记录，拿到 ID 用于 SSE 进度推送
    record = await Presentation.create(user=user, topic=topic, status="generating")
    pid = record.id
    _t_total = _time.perf_counter()

    async def _do_generate():
        nonlocal chat_group_id
        try:
            # — 第1步：获取资源 —
            t0 = _time.perf_counter()
            _push_progress(pid, "fetch_resources", "正在获取学习资源…", "running")
            doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
            if not any([doc, mindmap_data, ppt_data]):
                raise ServiceError(f"话题「{topic}」暂无已生成的资源，请先通过 /resource/generate 生成")
            _push_progress(pid, "fetch_resources", "学习资源获取完毕", "done", int((_time.perf_counter() - t0) * 1000))

            if answers:
                doc, mindmap_data, ppt_data = _crop_content_by_answers(doc, mindmap_data, ppt_data, answers)

            # — 第2步：个性化引入 —
            t0 = _time.perf_counter()
            _push_progress(pid, "portrait_intro", "正在生成个性化引入…", "running")
            portrait_intro = await _build_portrait_intro(topic, user)
            _push_progress(pid, "portrait_intro", "个性化引入生成完毕", "done", int((_time.perf_counter() - t0) * 1000))

            # — 第3-5步：逐个构建章节骨架 —
            chapters_list: list[dict] = []
            audio_tasks: list[dict] = []

            if doc:
                t0 = _time.perf_counter()
                _push_progress(pid, "build_intro", "正在构建文档章节…", "running")
                ch = _build_intro_skeleton(doc)
                chapters_list.append(ch)
                audio_tasks.append({"chapter_idx": len(chapters_list) - 1, "resource": doc})
                _push_progress(pid, "build_intro", "文档章节构建完毕", "done", int((_time.perf_counter() - t0) * 1000))

            if mindmap_data:
                t0 = _time.perf_counter()
                _push_progress(pid, "build_mindmap", "正在构建思维导图章节…", "running")
                parsed = parse_mindmap_text(mindmap_data.content or "")
                svg = _mindmap_to_svg(parsed)
                ch = _build_mindmap_skeleton(mindmap_data, svg)
                chapters_list.append(ch)
                audio_tasks.append({"chapter_idx": len(chapters_list) - 1, "resource": mindmap_data})
                _push_progress(pid, "build_mindmap", "思维导图章节构建完毕", "done", int((_time.perf_counter() - t0) * 1000))

            if ppt_data:
                t0 = _time.perf_counter()
                _push_progress(pid, "build_ppt", "正在构建PPT章节…", "running")
                ch = _build_ppt_skeleton(ppt_data, plain=video_mode)
                chapters_list.append(ch)
                audio_tasks.append({"chapter_idx": len(chapters_list) - 1, "resource": ppt_data})
                _push_progress(pid, "build_ppt", "PPT章节构建完毕", "done", int((_time.perf_counter() - t0) * 1000))

            # 画像引入置顶
            if portrait_intro:
                chapters_list.insert(0, portrait_intro)
                from types import SimpleNamespace as _SN
                intro_raw = portrait_intro.pop("_raw_text", "")
                intro_resource = _SN(id=0, content=intro_raw, resource_type="document")
                audio_tasks.insert(0, {"chapter_idx": 0, "resource": intro_resource})
                for t in audio_tasks[1:]:
                    t["chapter_idx"] += 1

            # — 第6步：渲染 HTML —
            file_url = ""
            if not video_mode:
                t0 = _time.perf_counter()
                _push_progress(pid, "render_html", "正在渲染课件…", "running")
                PRESENTATIONS_DIR.mkdir(parents=True, exist_ok=True)
                html = _render_html(topic, chapters_list, template_path=None)
                filename = f"{_safe_filename(topic)}_{uuid.uuid4().hex[:8]}.html"
                file_path = PRESENTATIONS_DIR / filename
                file_path.write_text(html, encoding="utf-8")
                file_url = f"/static/presentations/{filename}"
                _push_progress(pid, "render_html", "课件渲染完毕", "done", int((_time.perf_counter() - t0) * 1000))

            # 更新记录
            record.chapters_json = json.dumps(chapters_list, ensure_ascii=False)
            record.total_duration_ms = sum(c.get("total_duration_ms", 0) for c in chapters_list)
            record.status = "ready"
            if file_url:
                record.file_url = file_url
            await record.save()

            # 保存到聊天历史
            cgid = chat_group_id if chat_group_id and chat_group_id > 0 else await allocate_chat_group_id(user_id)
            chat_group_id = cgid
            try:
                req_text = topic
                if answers:
                    selected = []
                    for v in answers.values():
                        if isinstance(v, list):
                            selected.extend(str(x) for x in v)
                        elif v:
                            selected.append(str(v))
                    if selected:
                        req_text = f"{topic}（已选择：{' / '.join(selected)}）"
                res_json = json.dumps({
                    "type": "presentation",
                    "id": record.id,
                    "topic": topic,
                    "file_url": _versioned_presentation_url(record.file_url),
                    "status": "ready",
                    "_video_hint": "动态课件已生成，可立即查看",
                }, ensure_ascii=False)
                await ChatHistory.create(user=user, chat_group_id=cgid, req=req_text, res=res_json)
            except Exception:
                logger.exception("保存课件到聊天历史失败")

            # 推送通知
            try:
                await Notification.create(
                    type="resource",
                    title="课件已生成",
                    content=f"「{topic}」课件已生成，共 {len(chapters_list)} 章，可立即查看（音频后台补充中）",
                    target_url=f"/presentation?id={record.id}",
                    target_user_id=user_id,
                )
            except Exception:
                logger.exception("课件通知推送失败")

            # 后台补音频
            asyncio_create_task(_add_audio_to_presentation(record.id, topic, user_id, voice, chapters_list, audio_tasks))

            total_ms = int((_time.perf_counter() - _t_total) * 1000)
            chapter_names = [c.get("title", "") for c in chapters_list]
            _push_progress(pid, "done", f"课件生成完毕，共 {len(chapters_list)} 章（{' → '.join(chapter_names)}）", "done", total_ms)
            await _notify_sse(pid, {
                "status": "ready",
                "file_url": _versioned_presentation_url(file_url),
                "id": record.id,
                "chapters": len(chapters_list),
            })
            logger.info("[课件] 骨架生成完成 topic=%s record=%d chapters=%d 耗时=%.1fs",
                        topic, record.id, len(chapters_list), _time.perf_counter() - _t_total)

            return {
                "id": record.id,
                "file_url": _versioned_presentation_url(file_url),
                "status": "ready",
                "template_version": VIDEO_TEMPLATE_VERSION if video_mode else PRESENTATION_TEMPLATE_VERSION,
                "message": "课件已生成，音频在后台补充中",
            }

        except Exception as e:
            logger.exception("课件生成失败")
            record.status = "failed"
            record.error_message = str(e)
            await record.save()
            _push_progress(pid, "error", str(e), "error")
            await _notify_sse(pid, {"status": "failed", "error": str(e)})
            raise

    if background:
        asyncio_create_task(_do_generate())
        return {
            "id": record.id,
            "status": "generating",
            "template_version": VIDEO_TEMPLATE_VERSION if video_mode else PRESENTATION_TEMPLATE_VERSION,
            "message": "课件生成中，请通过 SSE 获取进度",
        }
    else:
        return await _do_generate()


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
    """更新 HTML 文件（如有）+ DB + SSE 通知"""
    file_path = _presentation_file_path(record.file_url)
    if file_path and file_path.exists():
        # 检测当前 HTML 是否使用视频模板，保持模板一致
        _tp = None
        try:
            _head = file_path.read_text(encoding="utf-8", errors="ignore")[:200]
            if f"template-version:{VIDEO_TEMPLATE_VERSION}" in _head or "template-version:video-v3" in _head or "template-version:video-v2" in _head:
                _tp = TEMPLATE_VIDEO_PATH
        except Exception:
            logger.warning("读取 HTML 模板版本失败，使用默认模板 record=%s", record.id)
        html = _render_html(topic, chapters, segments or [], template_path=_tp)
        PRESENTATIONS_DIR.mkdir(parents=True, exist_ok=True)
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
        logger.warning("获取用户画像失败 user_id=%s", user.id)
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
            except (json.JSONDecodeError, TypeError):
                logger.warning("解析性格标签失败 user_id=%s", user.id)
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

    from backend.src.utils.tts_utils import parse_text_sections
    sections = parse_text_sections(intro_text)
    slides = []
    for sec in sections:
        slides.append({
            "title": sec.get("title") or topic,
            "content_html": _md_to_html(sec.get("text", "")),
            "audio_url": None,
            "duration_ms": sec.get("duration_ms", 5000),
            "word_timestamps": [],
        })

    total_dur = sum(s.get("duration_ms", 0) for s in slides)
    return {
        "type": "intro",
        "title": "学习引入",
        "slides": slides,
        "total_duration_ms": total_dur,
        "is_audio_ready": False,
        "_raw_text": intro_text,
    }


def _build_intro_skeleton(record, max_slides: int = 8) -> dict:
    from backend.src.utils.tts_utils import parse_text_sections
    content = record.content or ""

    # 先按标题切分，有标题时保留原始 markdown 给 HTML 渲染
    raw_parts = re.split(r"\n(?=## )", content.strip())
    if len(raw_parts) <= 1:
        raw_parts = re.split(r"\n(?=# )", content.strip())

    slides = []
    if len(raw_parts) > 1:
        # 有标题 → 和 parse_text_sections 一致，保留原始 markdown
        for part in raw_parts[:max_slides]:
            part = part.strip()
            if not part:
                continue
            lines = part.split("\n")
            title = lines[0].lstrip("#").strip()
            slides.append({
                "title": title,
                "content_html": _md_to_html(part),
                "audio_url": None,
                "duration_ms": int(len(part) / 4 * 1000),
                "word_timestamps": [],
            })
    else:
        # 无标题 → 用 parse_text_sections 确保 slide 数 = TTS 分段数
        sections = parse_text_sections(content)
        for sec in sections[:max_slides]:
            slides.append({
                "title": sec.get("title") or record.topic,
                "content_html": _md_to_html(sec.get("text", "")),
                "audio_url": None,
                "duration_ms": sec.get("duration_ms", 5000),
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
    path = _presentation_file_path(url)
    tag = PRESENTATION_TEMPLATE_VERSION
    if path and path.exists():
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:220]
            if f"template-version:{VIDEO_TEMPLATE_VERSION}" in head:
                tag = VIDEO_TEMPLATE_VERSION
        except Exception:
            logger.warning("读取 HTML 文件失败，使用默认版本号 url=%s", url)
    return f"{base}?v={tag}"


def _presentation_file_path(url: str | None) -> Path | None:
    if not url:
        return None
    fname = str(url).split("?", 1)[0].rsplit("/", 1)[-1]
    if not fname:
        return None
    return PRESENTATIONS_DIR / fname


def _presentation_file_matches_template(url: str | None, expected_tag: str | None = None) -> bool:
    path = _presentation_file_path(url)
    if not path or not path.exists():
        return False
    tag = expected_tag or f"template-version:{PRESENTATION_TEMPLATE_VERSION}"
    try:
        return tag in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        logger.warning("读取 HTML 模板版本失败 url=%s", url)
        return False



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

    def stage_chrome(slide_index: int) -> str:
        progress = min(94, max(12, 18 + slide_index * 9))
        wave = "".join(f'<i style="--i:{i}"></i>' for i in range(1, 19))
        return (
            '<div class="video-slide__meta">'
            f'<span>AI 课程视频</span><b>第 {slide_index + 1} 页</b>'
            '</div>'
            f'<div class="video-slide__wave">{wave}</div>'
            f'<div class="video-slide__progress"><i style="--progress:{progress}%"></i></div>'
        )

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

        return f'<div class="slide video-slide video-slide--{_escape(layout)}">{stage_chrome(slide_index)}<h2 data-narration-block="{title_block}">{title}</h2>{body}</div>'

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
                parts.append(f'<div class="slide video-slide video-slide--intro">{stage_chrome(len(parts))}<h2 data-narration-block="intro-{index}-title">{title}</h2><div class="intro-content">{paras}</div></div>')
        elif sec_type == "mindmap":
            html = sec.get("content_html", "")
            parts.append(f'<div class="slide video-slide video-slide--mindmap">{stage_chrome(len(parts))}<h2 data-narration-block="mindmap-title">思维导图</h2><div id="mindmap-container" data-narration-block="mindmap-body">{html}</div></div>')
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
    version_tag = f"<!-- template-version:{VIDEO_TEMPLATE_VERSION} -->" if is_video else f"<!-- template-version:{PRESENTATION_TEMPLATE_VERSION} -->"
    return f"{version_tag}\n{html}"


def _safe_filename(topic: str) -> str:
    return "".join(c for c in topic if c.isalnum() or c in " _-")[:30]

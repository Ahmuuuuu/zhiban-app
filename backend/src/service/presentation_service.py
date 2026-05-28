"""学习课件 HTML 生成服务 — 增量生成，产出一章推送一章"""
import json
import logging
import re
import uuid
from pathlib import Path

from backend.src.models.presentation_model import Presentation
from backend.src.models.resource_model import GeneratedResource

logger = logging.getLogger(__name__)

PRESENTATION_DIR = Path(__file__).parent.parent.parent / "static" / "presentations"
TEMPLATE_PATH = Path(__file__).parent.parent / "ai_core" / "prompts" / "presentation" / "template.html"


# ─── SSE 通知队列 ───
_sse_queues: dict[int, list] = {}


def _subscribe_sse(presentation_id: int):
    """为 SSE 客户端创建消息队列"""
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
    """通知所有 SSE 客户端"""
    for q in _sse_queues.get(presentation_id, []):
        q.append(data)


# ═══════════════════════════════════════════════
#  对外 API
# ═══════════════════════════════════════════════

async def generate(topic: str, user_id: int, voice: str = "zh-CN-XiaoxiaoNeural") -> dict:
    """创建课件记录 + 启动后台生成，立即返回"""
    from backend.src.models.usermodel import User
    user = await User.filter(id=user_id).first()
    if not user:
        return {"error": "用户不存在"}

    # 检查话题是否有资源
    doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
    if not any([doc, mindmap_data, ppt_data]):
        return {"error": f"话题「{topic}」暂无已生成的资源，请先通过 /resource/generate 生成"}

    # 创建 DB 记录
    record = await Presentation.create(user=user, topic=topic, status="generating")

    # 保存骨架 HTML（空章节，显示加载中）
    html = _render_html(topic, [])
    filename = f"{_safe_filename(topic)}_{uuid.uuid4().hex[:8]}.html"
    file_path = PRESENTATION_DIR / filename
    file_path.write_text(html, encoding="utf-8")

    record.file_url = f"/static/presentations/{filename}"
    await record.save()

    # 启动后台生成
    asyncio_create_task(_generate_chapters(record.id, topic, user_id, voice))

    return {
        "id": record.id,
        "file_url": record.file_url,
        "status": "generating",
        "message": "课件生成已启动，可通过 SSE 实时跟踪进度",
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

    # 删文件
    if record.file_url:
        fname = record.file_url.rsplit("/", 1)[-1]
        fp = PRESENTATION_DIR / fname
        if fp.exists():
            fp.unlink()

    await record.delete()
    return True


# ═══════════════════════════════════════════════
#  后台增量生成
# ═══════════════════════════════════════════════

async def _generate_chapters(record_id: int, topic: str, user_id: int, voice: str):
    """逐章生成：每完成一章就更新 HTML + 通知 SSE"""
    from backend.src.service.narration_service import narrate_resource
    from backend.src.utils.mindmap import parse_mindmap_text

    record = await Presentation.filter(id=record_id).first()
    if not record:
        return

    doc, mindmap_data, ppt_data = await _fetch_resources(topic, user_id)
    chapters = []

    try:
        # ── Ch1: 学科介绍 ──
        if doc:
            logger.info("[课件] 开始生成学科介绍 narration resource=%d", doc.id)
            narration = await narrate_resource(doc.id, voice)
            ch = _build_intro_section(doc, narration)
            chapters.append(ch)
            await _flush(record, topic, chapters, "generating")

        # ── Ch2: 思维导图 ──
        if mindmap_data:
            logger.info("[课件] 开始生成思维导图 narration resource=%d", mindmap_data.id)
            narration = await narrate_resource(mindmap_data.id, voice)
            parsed = parse_mindmap_text(mindmap_data.content or "")
            svg = _mindmap_to_svg(parsed)
            ch = _build_mindmap_section(mindmap_data, svg, narration)
            chapters.append(ch)
            await _flush(record, topic, chapters, "generating")

        # ── Ch3: PPT讲解 ──
        if ppt_data:
            logger.info("[课件] 开始生成 PPT 讲解 narration resource=%d", ppt_data.id)
            narration = await narrate_resource(ppt_data.id, voice)
            ch = await _build_ppt_section(ppt_data, narration)
            chapters.append(ch)
            await _flush(record, topic, chapters, "generating")

        # 全部完成
        await _flush(record, topic, chapters, "ready")
        logger.info("[课件] 全部生成完成 record=%d", record_id)

    except Exception as e:
        logger.exception("[课件] 生成失败 record=%d", record_id)
        await _flush(record, topic, chapters, "failed")
        record = await Presentation.filter(id=record_id).first()
        if record:
            record.error_message = str(e)[:500]
            await record.save()
        await _notify_sse(record_id, {"status": "failed", "error": str(e)[:200]})


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
#  资源获取 + 章节构建（同之前）
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
#  章节构建（与之前一致）
# ═══════════════════════════════════════════════

def _build_intro_section(record, narration) -> dict:
    content = record.content or ""
    segments = (narration or {}).get("sections", [])

    # 按 ## 标题切分为多页
    raw_parts = re.split(r"\n(?=## )", content.strip())
    if len(raw_parts) <= 1:
        raw_parts = re.split(r"\n(?=# )", content.strip())

    slides = []
    for i, part in enumerate(raw_parts):
        part = part.strip()
        if not part:
            continue
        html = _md_to_html(part)
        lines = part.split("\n")
        title = lines[0].lstrip("#").strip()
        seg = segments[i] if i < len(segments) else None
        slides.append({
            "title": title,
            "content_html": html,
            "audio_url": seg["audio_url"] if seg else None,
            "duration_ms": seg["duration_ms"] if seg else 5000,
            "word_timestamps": seg.get("word_timestamps", []) if seg else [],
        })

    total_dur = sum(s.get("duration_ms", 0) for s in slides)
    return {
        "type": "intro",
        "title": record.topic,
        "slides": slides,
        "total_duration_ms": total_dur,
    }


def _build_mindmap_section(record, svg: str, narration) -> dict:
    segments = (narration or {}).get("sections", [])
    total_dur = sum(s.get("duration_ms", 0) for s in segments)
    return {
        "type": "mindmap",
        "title": record.topic,
        "content_html": svg,
        "audio_segments": segments,
        "total_duration_ms": total_dur,
    }


async def _build_ppt_section(record, narration) -> dict:
    from backend.src.utils.tts_utils import parse_slides
    content = record.content or ""
    slides_meta = parse_slides(content)
    segments = (narration or {}).get("sections", [])

    slides = []
    for i, meta in enumerate(slides_meta):
        bullets = meta.get("bullets") or []
        seg = segments[i] if i < len(segments) else None
        slides.append({
            "title": meta.get("title", ""),
            "bullets": bullets,
            "notes": meta.get("notes", ""),
            "audio_url": seg["audio_url"] if seg else None,
            "duration_ms": seg["duration_ms"] if seg else 5000,
            "word_timestamps": seg.get("word_timestamps", []) if seg else [],
        })

    total_dur = sum(s.get("duration_ms", 0) for s in slides)
    return {
        "type": "ppt",
        "title": record.topic,
        "slides": slides,
        "total_duration_ms": total_dur,
    }


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

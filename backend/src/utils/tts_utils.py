"""EdgeTTS 工具 — 文本转语音、幻灯片/文档章节解析"""

import asyncio
import hashlib
import logging
import os
import re

logger = logging.getLogger(__name__)

# 可用语音列表
VOICES = [
    # 中文
    "zh-CN-XiaoxiaoNeural",   # 女声，温柔自然（默认）
    "zh-CN-YunxiNeural",      # 男声，沉稳
    "zh-CN-XiaoyiNeural",     # 女声，活泼
    "zh-CN-YunjianNeural",    # 男声，年轻
    "zh-CN-XiaochenNeural",   # 女声，成熟
    "zh-CN-YunyangNeural",    # 男声，新闻播报
    # 英文
    "en-US-AriaNeural",       # 美音女声，自然
    "en-US-GuyNeural",        # 美音男声，沉稳
    "en-US-JennyNeural",      # 美音女声，亲切
    "en-GB-SoniaNeural",      # 英音女声
    "en-GB-RyanNeural",       # 英音男声
]

# 支持生成旁白的资源类型
NARRATABLE_TYPES = {"ppt", "document", "case", "reading", "mindmap"}


def clean_for_tts(text: str) -> str:
    """清洗 markdown 文本，去掉不适合朗读的格式"""
    text = re.sub(r"```[\s\S]*?```", "，代码示例请见原文，", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\$\$[\s\S]*?\$\$", "，公式请见原文，", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    # 去掉水平分隔线（---、***、___ 单独成行）
    text = re.sub(r"^[-\*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # 去掉表格对齐行（| :--- | :--- |）
    text = re.sub(r"^\|[\s:\-]+\|.*$", "", text, flags=re.MULTILINE)
    # 表格行：去掉首尾 |，竖线变逗号
    text = re.sub(r"^\|(.+)\|$", lambda m: m.group(1).strip(), text, flags=re.MULTILINE)
    text = text.replace("|", "，")
    # HTML 实体
    text = re.sub(r"<!--[\s\S]*?-->", "", text)  # 去掉 HTML 注释（layout/theme/visual 等视觉元数据）
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&nbsp;", " ")
    text = re.sub(r"\n+", "，", text)
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"^[，、；\s]+", "", text)
    text = re.sub(r"[，、；\s]+$", "", text)
    return text.strip()


def parse_slides_plain(markdown: str) -> list[dict]:
    """解析 PPT markdown 为纯文本幻灯片 — 不注入任何视觉组件，供视频/TTS 使用"""
    raw_slides = re.split(r"\n---\n", markdown.strip())
    slides = []

    def _strip_comments(s: str) -> str:
        return re.sub(r"<!--[\s\S]*?-->", "", s).strip()

    for block in raw_slides:
        block = block.strip()
        if not block:
            continue

        title = ""
        bullets: list[str] = []
        notes: list[str] = []
        body_lines: list[str] = []

        for line in block.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # 跳过 HTML 注释和元数据行（layout/theme/visual）
            if re.match(r"^<!--\s*(layout|theme|visual)\s*:", stripped):
                continue
            if stripped.startswith("# ") or stripped.startswith("## "):
                title = _strip_comments(stripped.lstrip("#").strip())
            elif stripped.startswith("> "):
                notes.append(_strip_comments(stripped[2:].strip()))
            elif stripped.startswith("- ") or stripped.startswith("* "):
                bullets.append(_strip_comments(stripped[2:].strip()))
            elif re.match(r"^\d+[.)]\s", stripped):
                bullets.append(_strip_comments(stripped))
            else:
                body_lines.append(_strip_comments(stripped))

        if body_lines and not title:
            title = body_lines[0]
            body_lines = body_lines[1:]

        content_items = bullets if bullets else body_lines
        text = title
        if content_items:
            text += "。" + "，".join(content_items[:6])
        if notes:
            text += "。" + "，".join(notes)
        text = clean_for_tts(text)

        duration_ms = int(len(text) / 4 * 1000)
        slides.append({"title": title, "text": text, "bullets": bullets, "notes": "\n".join(notes), "duration_ms": duration_ms})

    return slides


def parse_slides(markdown: str) -> list[dict]:
    """解析 PPT markdown 并注入视觉布局元数据（layout/theme/visual/blocks）"""
    from backend.src.utils.slide_schema import parse_markdown_slides

    slides = []
    for slide in parse_markdown_slides(markdown):
        content_items = slide.get("bullets") or [
            line.strip() for line in str(slide.get("text") or "").splitlines() if line.strip()
        ]
        tts_text = slide.get("title") or ""
        if content_items:
            tts_text += " " + " ".join(content_items[:6])
        if slide.get("notes"):
            tts_text += " " + str(slide.get("notes"))
        tts_text = clean_for_tts(tts_text)
        slides.append({
            **slide,
            "text": tts_text,
            "duration_ms": int(len(tts_text) / 4 * 1000),
        })

    return slides


def parse_text_sections(markdown: str) -> list[dict]:
    """将非 PPT 的文本类内容拆分为可朗读的章节

    策略（按优先级）：
    1. 有 ## 标题 → 按 ## 标题切分
    2. 有 # 标题 → 按 # 标题切分
    3. 都没有 → 每 300 字切一段
    """
    content = markdown.strip()
    if not content:
        return []

    sections: list[dict] = []

    # 按二级标题切分
    parts = re.split(r"\n(?=## )", content)
    if len(parts) <= 1:
        parts = re.split(r"\n(?=# )", content)

    if len(parts) > 1:
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            lines = part.split("\n")
            title = lines[0].lstrip("#").strip()
            body = clean_for_tts("\n".join(lines[1:]))
            text = f"{title}。" + body if body else title
            sections.append({
                "title": title,
                "text": text,
                "notes": "",
                "duration_ms": int(len(text) / 4 * 1000),
            })
    else:
        # 无标题，按字符数切分
        cleaned = clean_for_tts(content)
        chunk_size = 300
        start = 0
        i = 0
        while start < len(cleaned):
            end = min(start + chunk_size, len(cleaned))
            if end < len(cleaned):
                # 尽量在句号或逗号处断句
                for sep in ["。", "，", "；"]:
                    last = cleaned.rfind(sep, start, end)
                    if last > start + chunk_size // 2:
                        end = last + 1
                        break
            chunk = cleaned[start:end].strip("，。")
            if chunk:
                sections.append({
                    "title": f"第{i + 1}段",
                    "text": chunk,
                    "notes": "",
                    "duration_ms": int(len(chunk) / 4 * 1000),
                })
                i += 1
            start = end

    return sections


def parse_by_type(markdown: str, resource_type: str) -> list[dict]:
    """根据资源类型选择解析策略"""
    if resource_type == "ppt":
        return parse_slides(markdown)
    return parse_text_sections(markdown)


async def generate_audio(text: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%"):
    """调用 EdgeTTS 将文本转为 MP3 音频（带超时，自动绕过代理）"""
    output_path, _ = await _generate_audio_impl(text, output_path, voice, rate)
    return output_path


async def generate_audio_with_timestamps(text: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%"):
    """调用 EdgeTTS stream 模式生成音频并收集词级时间戳

    Returns:
        (output_path, word_timestamps)
        word_timestamps: [{"text": str, "offset_ms": int, "duration_ms": int}, ...]
    """
    return await _generate_audio_impl(text, output_path, voice, rate, capture_words=True)


async def _generate_audio_impl(text: str, output_path: str, voice: str, rate: str, capture_words: bool = False):
    """EdgeTTS 统一实现：支持普通模式和词级时间戳模式（带 Redis 缓存）"""
    import edge_tts

    # Redis 缓存：相同文本相同语音 7 天内不重复生成（仅限无时间戳模式）
    _cache_hit = False
    _tts_ck = None
    if not capture_words and text and voice:
        try:
            from backend.src.utils.redis_client import cache_get, cache_set, _cache_key, _text_hash
            from backend.src.utils.constants import TTS_CACHE_TTL
            _tts_ck = _cache_key("tts", _text_hash(text.strip()), voice, rate)
            _cached_path = await cache_get(_tts_ck)
            if _cached_path and os.path.isfile(_cached_path):
                output_path = _cached_path
                _cache_hit = True
        except Exception:
            logger.debug("TTS 缓存读取失败，跳过缓存（降级运行）")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if _cache_hit:
        return output_path, []

    try:
        _tts_timeout = 120
        communicate = edge_tts.Communicate(text, voice, rate=rate)

        if not capture_words:
            await asyncio.wait_for(communicate.save(output_path), timeout=_tts_timeout)
            # 缓存生成的音频路径
            if text and voice and _tts_ck:
                try:
                    await cache_set(_tts_ck, output_path, TTS_CACHE_TTL)
                except Exception:
                    logger.debug("TTS 缓存写入失败（降级运行）")
            return output_path, []

        # stream 模式：启用 WordBoundary 收集词级时间戳
        communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        audio_data = bytearray()
        word_timestamps = []

        async def _stream_collect():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_timestamps.append({
                        "text": chunk["text"],
                        "offset_ms": chunk["offset"] // 10000,
                        "duration_ms": chunk["duration"] // 10000,
                    })

        await asyncio.wait_for(_stream_collect(), timeout=_tts_timeout)

        with open(output_path, "wb") as f:
            f.write(audio_data)

        return output_path, word_timestamps
    except asyncio.TimeoutError:
        logger.error("[TTS] 超时 (%ds): text_len=%d voice=%s", _tts_timeout, len(text), voice)
        raise

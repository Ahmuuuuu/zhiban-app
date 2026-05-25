"""EdgeTTS 工具 — 文本转语音、幻灯片/文档章节解析"""

import logging
import re

logger = logging.getLogger(__name__)

# 可用的中文语音列表
VOICES = [
    "zh-CN-XiaoxiaoNeural",   # 女声，温柔自然（默认）
    "zh-CN-YunxiNeural",      # 男声，沉稳
    "zh-CN-XiaoyiNeural",     # 女声，活泼
    "zh-CN-YunjianNeural",    # 男声，年轻
    "zh-CN-XiaochenNeural",   # 女声，成熟
    "zh-CN-YunyangNeural",    # 男声，新闻播报
]

# 支持生成旁白的资源类型
NARRATABLE_TYPES = {"ppt", "document", "case", "reading", "mindmap"}


def clean_for_tts(text: str) -> str:
    """清洗 markdown 文本，去掉不适合朗读的格式"""
    text = re.sub(r"```[\s\S]*?```", "，代码示例见课件，", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\$\$[\s\S]*?\$\$", "，公式见课件，", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"\n+", "，", text)
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"，$", "", text)
    return text.strip()


def parse_slides(markdown: str) -> list[dict]:
    """解析 PPT markdown，返回每页的 {title, text, notes, duration_ms}"""
    raw_slides = re.split(r"\n---\n", markdown.strip())
    slides = []

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
            if stripped.startswith("# ") or stripped.startswith("## "):
                title = stripped.lstrip("#").strip()
            elif stripped.startswith("> "):
                notes.append(stripped[2:].strip())
            elif stripped.startswith("- ") or stripped.startswith("* "):
                bullets.append(stripped[2:].strip())
            elif re.match(r"^\d+[.)]\s", stripped):
                bullets.append(stripped)
            else:
                body_lines.append(stripped)

        if body_lines and not title:
            title = body_lines[0]
            body_lines = body_lines[1:]

        content_items = bullets if bullets else body_lines
        text = title
        if content_items:
            text += "。" + "，".join(content_items[:6])
        if notes:
            text += "。" + "，".join(notes)

        duration_ms = int(len(text) / 4 * 1000)
        slides.append({"title": title, "text": text, "notes": "\n".join(notes), "duration_ms": duration_ms})

    return slides


def parse_text_sections(markdown: str, resource_type: str = "document") -> list[dict]:
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
    return parse_text_sections(markdown, resource_type)


async def generate_audio(text: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%"):
    """调用 EdgeTTS 将文本转为 MP3 音频"""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path

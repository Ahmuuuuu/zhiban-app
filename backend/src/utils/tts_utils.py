"""EdgeTTS 工具 — 文本转语音、PPT 幻灯片解析"""

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


def clean_for_tts(text: str) -> str:
    """清洗 markdown 文本，去掉不适合朗读的格式"""
    # 代码块 → 占位
    text = re.sub(r"```[\s\S]*?```", "，代码示例见课件，", text)
    # 行内代码
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # LaTeX 公式
    text = re.sub(r"\$\$[\s\S]*?\$\$", "，公式见课件，", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    # Markdown 格式符 — 去掉 **bold** *italic* # headers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    # 链接
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # 多余空白和标点
    text = re.sub(r"\n+", "，", text)
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"，$", "", text)
    return text.strip()


def parse_slides(markdown: str) -> list[dict]:
    """解析 PPT markdown，返回每页的 {title, text, notes}"""
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

        # 估算时长（中文约 4 字/秒）
        duration_ms = int(len(text) / 4 * 1000)
        slides.append({"title": title, "text": text, "notes": "\n".join(notes), "duration_ms": duration_ms})

    return slides


async def generate_audio(text: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%"):
    """调用 EdgeTTS 将文本转为 MP3 音频"""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path

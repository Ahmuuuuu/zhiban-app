"""Shared slide normalization helpers for PPT preview/export.

The app still accepts the old markdown/title/text shape. These helpers add a
small visual schema on top so renderers can choose richer layouts without
breaking existing resources.
"""

from __future__ import annotations

import json
import logging
import os
import re
from html import unescape
from typing import Any


LAYOUTS = {
    "intro",
    "keypoint",
    "formula",
    "vocabulary",
    # backward compat — old PPT pipeline
    "title_cover",
    "concept_visual",
    "process_steps",
    "comparison",
    "formula_focus",
    "content_cards",
}

THEME_PALETTES = {
    "academic_blue": ["#163f8f", "#2f80ed", "#44c2ff", "#f7fbff"],
    "science_green": ["#11695f", "#28b487", "#a7f3d0", "#f6fffb"],
    "warm_case": ["#93491f", "#e86c00", "#ffd166", "#fff8ed"],
    "graphite": ["#17202a", "#566573", "#aeb6bf", "#f7f9fb"],
    "coral": ["#9f1239", "#fb7185", "#fbbf24", "#fff1f2"],
    "violet": ["#4c1d95", "#8b5cf6", "#38bdf8", "#f5f3ff"],
    "sunlit": ["#854d0e", "#f59e0b", "#84cc16", "#fffbeb"],
    "minimal-white": ["#111216", "#3b3f4a", "#6b6f7a", "#ffffff"],
    "academic-paper": ["#1a3a7a", "#0a0a0a", "#8a1a1a", "#fdfcf8"],
    "arctic-cool": ["#1e6fb0", "#17b1b1", "#6f8aa6", "#f2f6fb"],
    "aurora": ["#5ef2c6", "#7aa2ff", "#c984ff", "#06091c"],
    "bauhaus": ["#e03c27", "#f4c430", "#1d4eaf", "#f4efe3"],
    "blueprint": ["#ffffff", "#aee1ff", "#ffd27a", "#0b3a6f"],
    "catppuccin-latte": ["#8839ef", "#1e66f5", "#ea76cb", "#eff1f5"],
    "catppuccin-mocha": ["#cba6f7", "#89b4fa", "#f5c2e7", "#1e1e2e"],
    "corporate-clean": ["#0a2540", "#1d4ed8", "#64748b", "#ffffff"],
    "cyberpunk-neon": ["#ff2bd6", "#00f0ff", "#f9f871", "#000000"],
    "dracula": ["#bd93f9", "#ff79c6", "#8be9fd", "#282a36"],
    "editorial-serif": ["#8a2a1c", "#c97a4a", "#1b1410", "#faf7f2"],
    "engineering-whiteprint": ["#0a1e46", "#1e5ac4", "#c42a10", "#ffffff"],
    "glassmorphism": ["#7dd3fc", "#c084fc", "#f0abfc", "#0b1024"],
    "gruvbox-dark": ["#fe8019", "#fabd2f", "#b8bb26", "#282828"],
    "japanese-minimal": ["#d93a2a", "#1a1a18", "#c9a961", "#fafaf5"],
    "magazine-bold": ["#ea5a1a", "#0a0a0a", "#c42a10", "#f5efe2"],
    "memphis-pop": ["#ff3d8b", "#37c2d7", "#ffcc00", "#fef6e8"],
    "midcentury": ["#d4902a", "#2a7a7f", "#c7502a", "#f3ead8"],
    "neo-brutalism": ["#ffd400", "#ff5ca8", "#3a7cff", "#fffef0"],
    "news-broadcast": ["#e11d2d", "#0a0a0a", "#ffd100", "#ffffff"],
    "nord": ["#88c0d0", "#81a1c1", "#b48ead", "#2e3440"],
    "pitch-deck-vc": ["#0070f3", "#7928ca", "#ff4ecb", "#ffffff"],
    "rainbow-gradient": ["#ff4d8b", "#7a5cff", "#36b6ff", "#ffffff"],
    "retro-tv": ["#c73a1f", "#e67e14", "#f2b544", "#f5ecd7"],
    "rose-pine": ["#ebbcba", "#c4a7e7", "#9ccfd8", "#191724"],
    "sharp-mono": ["#000000", "#000000", "#ff2200", "#ffffff"],
    "soft-pastel": ["#f49bb8", "#b5d5f0", "#f7d08a", "#fdf7fb"],
    "solarized-light": ["#268bd2", "#2aa198", "#d33682", "#fdf6e3"],
    "sunset-warm": ["#d94860", "#e36a2d", "#f2a341", "#fff7ef"],
    "swiss-grid": ["#d6001c", "#111111", "#888888", "#ffffff"],
    "terminal-green": ["#00ff88", "#67ffd0", "#b6ff6b", "#030a04"],
    "tokyo-night": ["#7aa2f7", "#bb9af7", "#7dcfff", "#1a1b26"],
    "vaporwave": ["#ff6ec7", "#00f5ff", "#ffd166", "#1a0938"],
    "xiaohongshu-white": ["#ff2742", "#ff7a90", "#ffb38a", "#fffdfb"],
    "y2k-chrome": ["#8a5cff", "#3ccfd8", "#ff84c4", "#dfe4ec"],
}

THEMES = set(THEME_PALETTES.keys())


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


PPT_SPEAKER_NOTES_MIN_CHARS = max(1, _int_env("PPT_SPEAKER_NOTES_MIN_CHARS", 120))
PPT_SPEAKER_NOTES_MAX_CHARS = max(
    PPT_SPEAKER_NOTES_MIN_CHARS,
    _int_env("PPT_SPEAKER_NOTES_MAX_CHARS", 220),
)


def _clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"</?[^>\n]+>", " ", text)
    text = re.sub(r"<[^>\n]*$", " ", text)
    text = re.sub(r"^\s*(layout|theme|visual)\s*:\s*.*$", " ", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_NOTE_SENTENCE_BREAKS = set(".!?;,\u3002\uff01\uff1f\uff1b\uff0c\u3001")
_NOTE_TRAILING_PUNCTUATION = " \t\r\n,.;:!?\u3002\uff0c\uff1b\uff1a\u3001\uff01\uff1f"


def limit_speaker_notes(value: Any, max_chars: int | None = None) -> str:
    text = _clean_text(value)
    text = re.sub(r"\s+", " ", text).strip()
    limit = max(1, max_chars or PPT_SPEAKER_NOTES_MAX_CHARS)
    if len(text) <= limit:
        return text

    lower_bound = max(0, limit - 36)
    cut_at = limit
    for index in range(limit, lower_bound, -1):
        if text[index - 1] in _NOTE_SENTENCE_BREAKS:
            cut_at = index
            break

    trimmed = text[:cut_at].rstrip(_NOTE_TRAILING_PUNCTUATION)
    return trimmed or text[:limit].strip()


_NOTE_LABEL_RE = re.compile(
    "^\\s*(?:[-*+\u2022]\\s*)?(?:>\\s*)?"
    "(?:\u8bb2\u7a3f|\u5907\u6ce8|\u6f14\u8bb2\u7a3f|speaker\\s*notes?|speaker_notes?|notes?)"
    "\\s*[:\uff1a]\\s*(.*)$",
    re.IGNORECASE,
)


def _split_speaker_notes(value: Any) -> tuple[str, str]:
    body: list[str] = []
    notes: list[str] = []
    reading_quoted_note = False

    for raw_line in str(value or "").splitlines():
        match = _NOTE_LABEL_RE.match(raw_line)
        if match:
            note_text = match.group(1).strip()
            if note_text:
                notes.append(note_text)
            reading_quoted_note = bool(re.match(r"^\s*>", raw_line))
            continue

        if reading_quoted_note and re.match(r"^\s*>", raw_line):
            note_text = re.sub(r"^\s*>\s?", "", raw_line).strip()
            if note_text:
                notes.append(note_text)
            continue

        reading_quoted_note = False
        body.append(raw_line)

    return "\n".join(body).strip(), "\n".join(notes).strip()


def _merge_notes(*values: Any) -> str:
    return "\n".join(str(value or "").strip() for value in values if str(value or "").strip())


def _line_value(line: str, key: str) -> str:
    patterns = [
        rf"^<!--\s*{key}\s*:\s*(.*?)\s*-->$",
        rf"^\[{key}\s*:\s*(.*?)\]$",
        rf"^{key}\s*:\s*(.*?)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _looks_like_formula(text: str) -> bool:
    return bool(re.search(r"\$[^$]+\$|\\frac|\\sum|=|≈|≤|≥|\^|_", text))


def _looks_like_vocabulary(title: str, bullets: list[str]) -> bool:
    joined = f"{title}\n" + "\n".join(bullets)
    english_terms = re.findall(r"[A-Za-z][A-Za-z-]{2,}", joined)
    return bool(re.search(r"词汇|单词|英语|例句|短语|vocabulary|word|phrase", joined, re.IGNORECASE)) or len(english_terms) >= 5


def _choose_layout(index: int, title: str, bullets: list[str]) -> str:
    joined = f"{title}\n" + "\n".join(bullets)
    if index == 0:
        return "intro"
    if _looks_like_formula(joined):
        return "formula"
    if _looks_like_vocabulary(title, bullets):
        return "vocabulary"
    return "keypoint"


def _choose_theme(index: int, title: str) -> str:
    text = title.lower()
    if re.search(r"案例|场景|story|case", title, re.IGNORECASE):
        return "warm_case"
    if re.search(r"生物|化学|物理|science|实验|细胞", title, re.IGNORECASE):
        return "science_green"
    return ["academic_blue", "aurora", "coral", "violet", "sunlit", "science_green", "warm_case", "graphite"][index % 8]


def _visual_type(layout: str, text: str) -> str:
    if layout == "formula":
        return "formula"
    if re.search(r"地图|历史|区域|地理|位置", text):
        return "map"
    return "diagram"


def _blocks_from_bullets(bullets: list[str], text: str) -> list[dict]:
    source = bullets[:]
    if not source and text:
        source = [line.strip() for line in re.split(r"\r?\n|[;；]", text) if line.strip()]
    return [{"type": "key_point", "text": item} for item in source[:8]]


def normalize_slide(slide: dict, index: int = 0, total: int = 0) -> dict:
    title = _clean_text(slide.get("title") or slide.get("heading"))
    bullets: list[str] = []
    bullet_notes: list[str] = []
    for item in (slide.get("bullets") or []):
        bullet_body, bullet_note = _split_speaker_notes(item.get("text") if isinstance(item, dict) else item)
        if bullet_note:
            bullet_notes.append(bullet_note)
        bullet_text = _clean_text(bullet_body)
        if bullet_text:
            bullets.append(bullet_text)

    raw_text, text_notes = _split_speaker_notes(slide.get("text") or slide.get("content"))
    text = _clean_text(raw_text)
    if not text and bullets:
        text = "\n".join(bullets)
    if not bullets and text:
        bullets = [line.strip() for line in re.split(r"\r?\n|[;；]", text) if line.strip()]

    layout = _clean_text(slide.get("layout"))
    if layout not in LAYOUTS:
        layout = _choose_layout(index, title, bullets)

    theme = _clean_text(slide.get("theme"))
    if theme not in THEMES:
        theme = _choose_theme(index, title)

    visual = slide.get("visual") if isinstance(slide.get("visual"), dict) else {}
    visual_query = _clean_text(
        visual.get("query")
        or visual.get("asset_query")
        or slide.get("visual_hint")
        or slide.get("visual")
        or title
    )
    visual = {
        "type": _clean_text(visual.get("type")) or _visual_type(layout, f"{title}\n{text}"),
        "query": visual_query,
        "caption": _clean_text(visual.get("caption")) or (bullets[0] if bullets else title),
    }
    visual["image"] = {
        "kind": visual["type"],
        "style": "generated_illustration",
        "alt": visual_query or title,
    }

    raw_blocks = slide.get("blocks") if isinstance(slide.get("blocks"), list) else []
    blocks = []
    block_notes: list[str] = []
    for block in raw_blocks:
        raw_block_text = (block.get("text") or block.get("content")) if isinstance(block, dict) else block
        block_body, block_note = _split_speaker_notes(raw_block_text)
        if block_note:
            block_notes.append(block_note)
        block_text = _clean_text(block_body)
        if not block_text:
            continue
        if isinstance(block, dict):
            blocks.append({**block, "text": block_text, "content": block_text})
        else:
            blocks.append({"type": "key_point", "text": block_text})
    if not blocks:
        blocks = _blocks_from_bullets(bullets, text)

    notes = limit_speaker_notes(_merge_notes(slide.get("notes"), slide.get("speaker_notes"), text_notes, *bullet_notes, *block_notes))

    return {
        **slide,
        "index": int(slide.get("index", index) or index),
        "title": title,
        "text": text,
        "content": text,
        "bullets": bullets,
        "notes": notes,
        "speaker_notes": notes,
        "layout": layout,
        "theme": theme,
        "palette": THEME_PALETTES.get(theme, THEME_PALETTES["academic_blue"]),
        "visual": visual,
        "blocks": blocks,
        "schema_version": 2,
    }


def normalize_slides(slides: list[dict]) -> list[dict]:
    total = len(slides or [])
    return [normalize_slide(slide or {}, index, total) for index, slide in enumerate(slides or [])]


def parse_markdown_slides(markdown: str) -> list[dict]:
    content = (markdown or "").strip()
    if not content:
        return []

    if content[:1] in "[{":
        try:
            data = json.loads(content)
            raw_slides = data.get("slides", data) if isinstance(data, dict) else data
            if isinstance(raw_slides, list):
                return normalize_slides([item for item in raw_slides if isinstance(item, dict)])
        except json.JSONDecodeError:
            logging.getLogger("slide_schema").debug("JSON 解析失败，回退到正则解析 content[:100]=%s", content[:100])

    raw_slides = re.split(r"\n---\n", content)
    slides: list[dict] = []
    for index, block in enumerate(raw_slides):
        title = ""
        bullets: list[str] = []
        notes: list[str] = []
        body_lines: list[str] = []
        meta: dict[str, Any] = {}

        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            layout = _line_value(line, "layout")
            theme = _line_value(line, "theme")
            visual = _line_value(line, "visual")
            if layout:
                meta["layout"] = layout
                continue
            if theme:
                meta["theme"] = theme
                continue
            if visual:
                meta["visual_hint"] = visual
                continue
            if line.startswith("# ") or line.startswith("## "):
                title = line.lstrip("#").strip()
            elif line.startswith("> "):
                notes.append(line[2:].strip())
            elif line.startswith("- ") or line.startswith("* "):
                bullets.append(line[2:].strip())
            elif re.match(r"^\d+[.)]\s", line):
                bullets.append(line)
            else:
                body_lines.append(line)

        if body_lines and not title:
            title = body_lines[0]
            body_lines = body_lines[1:]

        text = "\n".join(bullets or body_lines)
        slides.append(normalize_slide({
            **meta,
            "index": index,
            "title": title,
            "text": text,
            "bullets": bullets,
            "notes": "\n".join(notes),
        }, index, len(raw_slides)))

    return [slide for slide in slides if slide.get("title") or slide.get("text")]


def slides_to_markdown(title: str, slides: list[dict]) -> str:
    blocks: list[str] = []
    for index, slide in enumerate(normalize_slides(slides or [])):
        slide_title = slide.get("title") or title or f"Slide {index + 1}"
        lines = [
            f"<!-- layout: {slide.get('layout', 'keypoint')} -->",
            f"<!-- theme: {slide.get('theme', 'academic_blue')} -->",
        ]
        visual_query = (slide.get("visual") or {}).get("query")
        if visual_query:
            lines.append(f"<!-- visual: {visual_query} -->")
        lines.append(f"# {slide_title}")

        for block in slide.get("blocks") or []:
            text = _clean_text(block.get("text") if isinstance(block, dict) else block)
            if text:
                lines.append(f"- {text}")

        if not any(line.startswith("- ") for line in lines):
            for raw_line in re.split(r"\r?\n|[;；]", slide.get("text") or ""):
                text = re.sub(r"^[-*•\s]+", "", raw_line).strip()
                if text:
                    lines.append(f"- {text}")

        for note_line in (slide.get("notes") or "").splitlines():
            note_line = note_line.strip()
            if note_line:
                lines.append(f"> {note_line}")
        blocks.append("\n".join(lines))
    return "\n---\n".join(blocks)

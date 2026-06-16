"""Shared slide normalization helpers for PPT preview/export.

The app still accepts the old markdown/title/text shape. These helpers add a
small visual schema on top so renderers can choose richer layouts without
breaking existing resources.
"""

from __future__ import annotations

import json
import logging
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

THEMES = {
    "academic_blue",
    "science_green",
    "warm_case",
    "graphite",
    "aurora",
    "coral",
    "violet",
    "sunlit",
}

THEME_PALETTES = {
    "academic_blue": ["#163f8f", "#2f80ed", "#44c2ff", "#f7fbff"],
    "science_green": ["#11695f", "#28b487", "#a7f3d0", "#f6fffb"],
    "warm_case": ["#93491f", "#e86c00", "#ffd166", "#fff8ed"],
    "graphite": ["#17202a", "#566573", "#aeb6bf", "#f7f9fb"],
    "aurora": ["#0f766e", "#22d3ee", "#a78bfa", "#f0fdfa"],
    "coral": ["#9f1239", "#fb7185", "#fbbf24", "#fff1f2"],
    "violet": ["#4c1d95", "#8b5cf6", "#38bdf8", "#f5f3ff"],
    "sunlit": ["#854d0e", "#f59e0b", "#84cc16", "#fffbeb"],
}


def _clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"</?[^>\n]+>", " ", text)
    text = re.sub(r"<[^>\n]*$", " ", text)
    text = re.sub(r"^\s*(layout|theme|visual)\s*:\s*.*$", " ", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
    bullets = [
        _clean_text(item.get("text") if isinstance(item, dict) else item)
        for item in (slide.get("bullets") or [])
        if _clean_text(item.get("text") if isinstance(item, dict) else item)
    ]
    text = _clean_text(slide.get("text") or slide.get("content"))
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

    blocks = slide.get("blocks") if isinstance(slide.get("blocks"), list) else []
    if not blocks:
        blocks = _blocks_from_bullets(bullets, text)

    return {
        **slide,
        "index": int(slide.get("index", index) or index),
        "title": title,
        "text": text,
        "content": text,
        "bullets": bullets,
        "notes": _clean_text(slide.get("notes") or slide.get("speaker_notes")),
        "speaker_notes": _clean_text(slide.get("speaker_notes") or slide.get("notes")),
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

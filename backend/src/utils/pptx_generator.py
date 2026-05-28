"""将 Markdown 格式的幻灯片内容转换为真正的 .pptx 二进制文件"""
import io
import re

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE


# 颜色方案
DARK_BLUE = RGBColor(0x1A, 0x3C, 0x6E)
ACCENT_BLUE = RGBColor(0x2B, 0x5C, 0x9E)
LIGHT_BLUE = RGBColor(0xE8, 0xF0, 0xFE)
DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
MEDIUM_GRAY = RGBColor(0x66, 0x66, 0x66)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF7, 0xF9, 0xFC)
ACCENT_ORANGE = RGBColor(0xE8, 0x6C, 0x00)


def _parse_slides(markdown: str) -> list[dict]:
    """解析 markdown，返回幻灯片列表 [{title, bullets, notes}]"""
    raw_slides = re.split(r'\n---\n', markdown.strip())

    slides = []
    first = True
    for block in raw_slides:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')
        title = ""
        bullets: list[str] = []
        notes: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('# '):
                title = stripped[2:].strip()
            elif stripped.startswith('## '):
                title = stripped[3:].strip()
            elif stripped.startswith('> '):
                notes.append(stripped[2:].strip())
            elif stripped.startswith('- ') or stripped.startswith('* '):
                bullets.append(stripped[2:].strip())
            elif re.match(r'^\d+[.)]\s', stripped):
                bullets.append(stripped)
            else:
                bullets.append(stripped)

        if first and not title and bullets:
            title = bullets[0]
            bullets = bullets[1:]

        slides.append({
            "title": title,
            "bullets": bullets,
            "notes": "\n".join(notes),
        })
        first = False

    return slides


def _add_dark_bg(slide, prs):
    """深色背景"""
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = DARK_BLUE
    bg.line.fill.background()


def _add_light_bg(slide, prs):
    """浅色背景"""
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = LIGHT_BG
    bg.line.fill.background()


def _add_top_bar(slide, prs):
    """顶部装饰色条"""
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, Inches(0.12)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = DARK_BLUE
    bar.line.fill.background()


def _add_title(slide, title_text, left=Inches(0.8), top=Inches(0.4),
               width=Inches(11.7), height=Inches(0.9), font_size=Pt(32)):
    """添加标题"""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = font_size
    p.font.bold = True
    p.font.color.rgb = DARK_BLUE
    return box


def _add_title_line(slide, left=Inches(0.8), top=Inches(1.3), width=Inches(11.7)):
    """标题下分隔线"""
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, Inches(0.04)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_BLUE
    line.line.fill.background()


def _add_bullets(slide, bullets, left=Inches(0.8), top=Inches(1.8),
                 width=Inches(11.7), height=Inches(5.2), max_items=10):
    """添加要点文本，关键术语加粗，层级清晰"""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    first_item = True
    for i, bullet in enumerate(bullets[:max_items]):
        if first_item:
            p = tf.paragraphs[0]
            first_item = False
        else:
            p = tf.add_paragraph()

        # 彩色序号圆点
        run_dot = p.add_run()
        run_dot.text = "● "
        run_dot.font.size = Pt(10)
        run_dot.font.color.rgb = ACCENT_BLUE
        run_dot.font.vertical_offset = Pt(-2)

        # 尝试按中文冒号分割：加粗前半部分（关键术语）
        parts = bullet.split("：", 1) if "：" in bullet else bullet.split(":", 1)
        if len(parts) == 2:
            run_key = p.add_run()
            run_key.text = parts[0] + "："
            run_key.font.size = Pt(17)
            run_key.font.bold = True
            run_key.font.color.rgb = DARK_BLUE

            run_val = p.add_run()
            run_val.text = parts[1]
            run_val.font.size = Pt(16)
            run_val.font.color.rgb = DARK_GRAY
        else:
            run_val = p.add_run()
            run_val.text = bullet
            run_val.font.size = Pt(16)
            run_val.font.color.rgb = DARK_GRAY

        p.space_after = Pt(6)
        p.space_before = Pt(4)
        p.level = 0
    return box


def _build_title_slide(prs, slide_data: dict):
    """标题页 — 深色背景 + 居中主标题 + 副标题"""
    layout = prs.slide_layouts[6]  # 空白布局
    slide = prs.slides.add_slide(layout)
    _add_dark_bg(slide, prs)

    # 装饰元素 - 右上角小色块
    decor = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(10.5), Inches(0), Inches(2.8), Inches(0.06)
    )
    decor.fill.solid()
    decor.fill.fore_color.rgb = ACCENT_ORANGE
    decor.line.fill.background()

    # 标题
    box = slide.shapes.add_textbox(Inches(1.5), Inches(2.0), Inches(10.3), Inches(2.5))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = slide_data["title"] or "课件"
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER

    # 副标题或第一要点
    subtitle_text = ""
    if slide_data["bullets"]:
        subtitle_text = slide_data["bullets"][0]
    if subtitle_text:
        sub_box = slide.shapes.add_textbox(Inches(1.5), Inches(4.5), Inches(10.3), Inches(1.5))
        stf = sub_box.text_frame
        stf.word_wrap = True
        sp = stf.paragraphs[0]
        sp.text = subtitle_text
        sp.font.size = Pt(22)
        sp.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        sp.alignment = PP_ALIGN.CENTER

        for extra in slide_data["bullets"][1:3]:
            sp2 = stf.add_paragraph()
            sp2.text = extra
            sp2.font.size = Pt(18)
            sp2.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
            sp2.alignment = PP_ALIGN.CENTER

    _add_notes(slide, slide_data)


def _build_content_slide(prs, slide_data: dict, index: int, total: int):
    """纯内容页：标题 + 要点 + 页码"""
    layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(layout)
    _add_light_bg(slide, prs)
    _add_top_bar(slide, prs)
    _add_title(slide, slide_data["title"] or f"第 {index} 页")
    _add_title_line(slide)
    _add_bullets(slide, slide_data["bullets"])
    _add_page_number(slide, index, total)
    _add_notes(slide, slide_data)


def _add_page_number(slide, index: int, total: int):
    """右下角页码"""
    box = slide.shapes.add_textbox(Inches(11.5), Inches(7.0), Inches(1.5), Inches(0.4))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.text = f"{index} / {total}"
    p.font.size = Pt(11)
    p.font.color.rgb = MEDIUM_GRAY
    p.alignment = PP_ALIGN.RIGHT


def _add_notes(slide, slide_data: dict):
    """添加备注"""
    if slide_data["notes"]:
        try:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = slide_data["notes"]
        except Exception:
            pass


def markdown_to_pptx(markdown: str) -> bytes:
    """将 markdown 幻灯片内容转换为 .pptx 二进制数据"""
    slides_data = _parse_slides(markdown)
    if not slides_data:
        return b""

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    total = len(slides_data)
    for i, slide_data in enumerate(slides_data):
        if i == 0:
            _build_title_slide(prs, slide_data)
        else:
            _build_content_slide(prs, slide_data, i, total)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()

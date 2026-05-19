"""将 Markdown 格式的幻灯片内容转换为真正的 .pptx 二进制文件"""
import io
import re

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


def _parse_slides(markdown: str) -> list[dict]:
    """解析 markdown，返回幻灯片列表 [{title, bullets, notes}]"""
    # 按 --- 分隔幻灯片（单独一行的 ---）
    raw_slides = re.split(r'\n---\n', markdown.strip())

    slides = []
    first = True
    for block in raw_slides:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')
        title = ""
        subtitle = ""
        bullets: list[str] = []
        notes: list[str] = []
        body_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('# '):
                title = stripped[2:].strip()
                # 也作为标题页的主体（去掉可能的层级前缀）
            elif stripped.startswith('## '):
                title = stripped[3:].strip()
            elif stripped.startswith('> '):
                notes.append(stripped[2:].strip())
            elif stripped.startswith('- ') or stripped.startswith('* '):
                bullets.append(stripped[2:].strip())
            elif re.match(r'^\d+[.)]\s', stripped):
                bullets.append(stripped)
            elif stripped.startswith('**') and '**' in stripped[2:]:
                # 粗体文本行作为要点的补充
                body_lines.append(stripped)
            else:
                # 非要点行：作为正文段落
                body_lines.append(stripped)

        if first and not title and bullets:
            # 没有标题的首页：第一行作为标题
            title = bullets[0]
            bullets = bullets[1:]
        if first and not title and body_lines:
            title = body_lines[0]
            body_lines = body_lines[1:]

        # 如果有 body_lines 但没 title，第一行当 title
        if body_lines and not title and not bullets:
            title = body_lines[0]
            body_lines = body_lines[1:]

        slides.append({
            "title": title,
            "bullets": bullets if bullets else body_lines,
            "notes": "\n".join(notes),
        })
        first = False

    return slides


def markdown_to_pptx(markdown: str) -> bytes:
    """将 markdown 幻灯片内容转换为 .pptx 二进制数据"""
    slides_data = _parse_slides(markdown)
    if not slides_data:
        return b""

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 颜色
    DARK_BLUE = RGBColor(0x1A, 0x3C, 0x6E)
    ACCENT_BLUE = RGBColor(0x2B, 0x5C, 0x9E)
    DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    LIGHT_GRAY = RGBColor(0xF0, 0xF0, 0xF0)

    for i, slide_data in enumerate(slides_data):
        if i == 0:
            # 标题页：居中大标题
            layout = prs.slide_layouts[6]  # 空白布局
            slide = prs.slides.add_slide(layout)

            # 背景色块
            bg_shape = slide.shapes.add_shape(
                1, Inches(0), Inches(0), prs.slide_width, prs.slide_height
            )
            bg_shape.fill.solid()
            bg_shape.fill.fore_color.rgb = DARK_BLUE
            bg_shape.line.fill.background()

            # 标题文本框
            title_box = slide.shapes.add_textbox(
                Inches(1.5), Inches(2.0), Inches(10.3), Inches(2.5)
            )
            tf = title_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = slide_data["title"] or "课件"
            p.font.size = Pt(44)
            p.font.bold = True
            p.font.color.rgb = WHITE
            p.alignment = PP_ALIGN.CENTER

            # 副标题（用第一条要点或备注作为副标题）
            if slide_data["bullets"]:
                subtitle_box = slide.shapes.add_textbox(
                    Inches(1.5), Inches(4.5), Inches(10.3), Inches(1.5)
                )
                stf = subtitle_box.text_frame
                stf.word_wrap = True
                sp = stf.paragraphs[0]
                sp.text = slide_data["bullets"][0] if slide_data["bullets"] else ""
                sp.font.size = Pt(22)
                sp.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
                sp.alignment = PP_ALIGN.CENTER

                # 剩余要点作为小标题
                for extra in slide_data["bullets"][1:3]:
                    sp2 = stf.add_paragraph()
                    sp2.text = extra
                    sp2.font.size = Pt(18)
                    sp2.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
                    sp2.alignment = PP_ALIGN.CENTER
        else:
            # 内容页
            layout = prs.slide_layouts[6]
            slide = prs.slides.add_slide(layout)

            # 顶部色条
            bar = slide.shapes.add_shape(
                1, Inches(0), Inches(0), prs.slide_width, Inches(0.15)
            )
            bar.fill.solid()
            bar.fill.fore_color.rgb = DARK_BLUE
            bar.line.fill.background()

            # 标题
            title_box = slide.shapes.add_textbox(
                Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.9)
            )
            tf = title_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = slide_data["title"] or f"第 {i} 页"
            p.font.size = Pt(32)
            p.font.bold = True
            p.font.color.rgb = DARK_BLUE

            # 分隔线
            line = slide.shapes.add_shape(
                1, Inches(0.8), Inches(1.3), Inches(11.7), Inches(0.04)
            )
            line.fill.solid()
            line.fill.fore_color.rgb = ACCENT_BLUE
            line.line.fill.background()

            # 要点正文
            body_box = slide.shapes.add_textbox(
                Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0)
            )
            btf = body_box.text_frame
            btf.word_wrap = True
            first_item = True
            for bullet in slide_data["bullets"][:6]:  # 每页最多 6 条
                if first_item:
                    bp = btf.paragraphs[0]
                    first_item = False
                else:
                    bp = btf.add_paragraph()
                bp.text = bullet
                bp.font.size = Pt(22)
                bp.font.color.rgb = DARK_GRAY
                bp.space_after = Pt(14)
                bp.level = 0

        # 备注
        if slide_data["notes"]:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = slide_data["notes"]

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()

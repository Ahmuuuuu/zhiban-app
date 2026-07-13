"""
文档文本提取 + 智能切片
支持 .txt / .pdf / .docx
"""
from pathlib import Path
import re


# ── 文本提取 ──

def extract_text(file_path: str | Path) -> str:
    """根据文件后缀提取文本内容"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text("utf-8", errors="replace")

    elif suffix == ".pdf":
        return _extract_pdf(path)

    elif suffix == ".docx":
        return _extract_docx(path)

    else:
        raise ValueError(f"不支持的文件格式: {suffix}（仅支持 .txt .pdf .docx）")


def _extract_pdf(path: Path) -> str:
    try:
        from pdfminer.high_level import extract_text as pdf_extract
    except ImportError:
        raise ImportError("请安装 pdfminer.six：pip install pdfminer.six")

    return pdf_extract(str(path))


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError:
        raise ImportError("请安装 python-docx：pip install python-docx")

    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


# ── 文本切片 ──

def chunk_text(text: str, max_chars: int = 1000, overlap_chars: int = 150) -> list[str]:
    """
    将长文本按语义段落切分成块。
    策略：保留标题路径，按段落聚合，长段落按句子切分，并给相邻块少量 overlap。
    """
    paragraphs = _paragraphs_with_heading_path(text)
    chunks = []
    current = ""

    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for sub in _split_long_paragraph(para, max_chars, overlap_chars):
                chunks.append(sub)
            continue

        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    return _add_overlap(chunks, overlap_chars) or [text]


def _paragraphs_with_heading_path(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", str(text or ""))
    raw_parts = [p.strip() for p in re.split(r"\n{2,}", normalized) if p.strip()]
    heading_path: list[str] = []
    parts: list[str] = []

    for part in raw_parts:
        lines = [line.strip() for line in part.splitlines() if line.strip()]
        if not lines:
            continue

        first = lines[0]
        heading = _parse_heading(first)
        if heading:
            level, title = heading
            heading_path = heading_path[: max(0, level - 1)]
            heading_path.append(title)
            body = "\n".join(lines[1:]).strip()
            if not body:
                continue
            part = body

        if heading_path:
            parts.append(f"标题路径：{' > '.join(heading_path)}\n{part}")
        else:
            parts.append(part)

    return parts


def _parse_heading(line: str) -> tuple[int, str] | None:
    markdown = re.match(r"^(#{1,6})\s+(.+)$", line)
    if markdown:
        return len(markdown.group(1)), markdown.group(2).strip()

    chapter = re.match(r"^第[一二三四五六七八九十百千万\d]+[章节篇讲课]\s*[：:、.]?\s*(.+)$", line)
    if chapter:
        return 1, line.strip()

    numbered = re.match(r"^(\d+(?:\.\d+){0,4})[、.)．]\s*(.+)$", line)
    if numbered:
        return min(numbered.group(1).count(".") + 1, 6), line.strip()

    cn_numbered = re.match(r"^[一二三四五六七八九十]+[、.．]\s*(.+)$", line)
    if cn_numbered and len(line) <= 40:
        return 2, line.strip()

    return None


def _split_long_paragraph(text: str, max_chars: int, overlap_chars: int = 150) -> list[str]:
    """按句号、问号、叹号、分号、换行切割超长段落。"""
    sentences = re.split(r"(?<=[。！？!?；;\n])", text)
    chunks = []
    current = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) + 1 <= max_chars:
            current += sent
        else:
            if current:
                chunks.append(current)
            if len(sent) > max_chars:
                chunks.extend(_hard_split(sent, max_chars, overlap_chars))
                current = ""
            else:
                current = sent

    if current:
        chunks.append(current)

    return chunks


def _hard_split(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    step = max(1, max_chars - max(0, overlap_chars))
    return [text[start:start + max_chars].strip() for start in range(0, len(text), step) if text[start:start + max_chars].strip()]


def _add_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    if overlap_chars <= 0 or len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for idx in range(1, len(chunks)):
        prev_tail = chunks[idx - 1][-overlap_chars:].strip()
        current = chunks[idx]
        if prev_tail and prev_tail not in current[: overlap_chars * 2]:
            current = f"上文摘要：{prev_tail}\n{current}"
        overlapped.append(current)
    return overlapped

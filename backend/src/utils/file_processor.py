"""
文档文本提取 + 智能切片
支持 .txt / .pdf / .docx
"""
from pathlib import Path


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

def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """
    将长文本按段落切分成块，每块不超过 max_chars 字符。
    策略：按双换行分段，再合并小段直到接近上限。
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        # 单段超长则按句号/换行切
        if len(para) > max_chars:
            # 先把 current 存起来
            if current:
                chunks.append(current)
                current = ""
            # 再切这段
            for sub in _split_long_paragraph(para, max_chars):
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

    return chunks or [text]


def _split_long_paragraph(text: str, max_chars: int) -> list[str]:
    """按句号、换行、逗号切割超长段落"""
    import re
    # 先按句号分割
    sentences = re.split(r"(?<=[。！？\n])", text)
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
            current = sent

    if current:
        chunks.append(current)

    return chunks

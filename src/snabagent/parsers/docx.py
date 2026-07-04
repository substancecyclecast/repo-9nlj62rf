from __future__ import annotations


def parse_docx(path: str) -> str:
    try:
        from docx import Document
    except ImportError:
        return ""
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

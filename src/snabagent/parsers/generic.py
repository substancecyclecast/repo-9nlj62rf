from __future__ import annotations

from pathlib import Path

from .docx import parse_docx
from .pdf import parse_pdf


def extract_text_from_path(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(str(p))
    if suffix in (".docx", ".doc"):
        return parse_docx(str(p))
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

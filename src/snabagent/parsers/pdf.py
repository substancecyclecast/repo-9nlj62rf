from __future__ import annotations


def parse_pdf(path: str) -> str:
    """Извлекает текст и таблицы из PDF. Fallback на pypdf при отсутствии pdfplumber."""
    parts: list[str] = []
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
                for table in page.extract_tables() or []:
                    for row in table:
                        parts.append(" | ".join((c or "") for c in row))
    except Exception:
        try:
            from pypdf import PdfReader

            r = PdfReader(path)
            for p in r.pages:
                parts.append(p.extract_text() or "")
        except Exception:
            return ""
    return "\n".join(parts)

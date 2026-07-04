"""Конвертирует data/sample_tz/*.txt в .docx и .pdf для демо."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "sample_tz"


def to_docx(src_txt: Path, dst: Path) -> None:
    try:
        from docx import Document
    except ImportError:
        print("python-docx не установлен — пропускаем DOCX-генерацию")
        return
    text = src_txt.read_text(encoding="utf-8")
    doc = Document()
    doc.add_heading("Заявка на закупку (внутренний документ)", level=1)
    for line in text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
        else:
            doc.add_paragraph("")
    doc.save(dst)
    print(f"DOCX -> {dst}")


def to_pdf(src_txt: Path, dst: Path) -> None:
    """Минимальный PDF без сторонних библиотек (Helvetica/Latin-1)."""
    text = src_txt.read_text(encoding="utf-8")
    # Latin-1 fallback для PDF (русские символы заменяем на транслит).
    try:
        import unicodedata

        norm = unicodedata.normalize("NFKD", text)
        ascii_text = norm.encode("ascii", "ignore").decode("ascii")
    except Exception:
        ascii_text = text

    # Очень простой PDF
    content_stream = (
        "BT\n"
        "/F1 11 Tf\n"
        "72 770 Td\n"
        "14 TL\n"
    )
    for line in ascii_text.splitlines():
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_stream += f"({safe}) Tj T*\n"
    content_stream += "ET\n"

    objects = []

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    objects.append(
        f"<< /Length {len(content_stream)} >>\nstream\n{content_stream}endstream"
    )
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = "%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf.encode("latin-1")))
        pdf += f"{i} 0 obj\n{obj}\nendobj\n"
    xref_start = len(pdf.encode("latin-1"))
    pdf += "xref\n"
    pdf += f"0 {len(objects) + 1}\n"
    pdf += "0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n"
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    dst.write_bytes(pdf.encode("latin-1", errors="replace"))
    print(f"PDF  -> {dst}")


def main() -> None:
    pairs = [
        ("tz_metal_dirty.txt", "tz_metal_dirty.docx", "tz_metal_dirty.pdf"),
        ("tz_it_dirty.txt", "tz_it_dirty.docx", "tz_it_dirty.pdf"),
        ("tz_chemistry_dirty.txt", "tz_chemistry_dirty.docx", "tz_chemistry_dirty.pdf"),
    ]
    for txt, docx, pdf in pairs:
        src = SRC / txt
        to_docx(src, SRC / docx)
        to_pdf(src, SRC / pdf)


if __name__ == "__main__":
    main()

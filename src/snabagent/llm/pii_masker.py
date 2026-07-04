"""Простейший PII-masker. На проде заменить на Microsoft Presidio."""
from __future__ import annotations

import re

INN_RE = re.compile(r"\b\d{10}\b|\b\d{12}\b")
OGRN_RE = re.compile(r"\b\d{13}\b|\b\d{15}\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
PHONE_RE = re.compile(r"(?:\+7|8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")


def mask_pii(text: str) -> tuple[str, dict[str, str]]:
    """Заменяет PII на плейсхолдеры. Возвращает (masked_text, mapping)."""
    mapping: dict[str, str] = {}
    counter = {"INN": 0, "OGRN": 0, "EMAIL": 0, "PHONE": 0}

    def _replace(pat: re.Pattern, kind: str, s: str) -> str:
        def sub(m: re.Match) -> str:
            counter[kind] += 1
            placeholder = f"<{kind}_{counter[kind]}>"
            mapping[placeholder] = m.group(0)
            return placeholder

        return pat.sub(sub, s)

    text = _replace(EMAIL_RE, "EMAIL", text)
    text = _replace(PHONE_RE, "PHONE", text)
    text = _replace(OGRN_RE, "OGRN", text)
    text = _replace(INN_RE, "INN", text)
    return text, mapping


def unmask_pii(text: str, mapping: dict[str, str]) -> str:
    for placeholder, original in mapping.items():
        text = text.replace(placeholder, original)
    return text

"""Auto-detect language of procurement request text (RU/EN/KZ)."""
from __future__ import annotations

import re

# Character range heuristics
_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_LATIN = re.compile(r"[a-zA-Z]")
_KAZAKH_SPECIFIC = re.compile(
    r"[\u04D8\u04D9\u0492\u0493\u049A\u049B\u04A2\u04A3"
    r"\u04E8\u04E9\u04B0\u04B1\u04AE\u04AF\u04BA\u04BB\u0406\u0456]"
)

# Common Kazakh words (not shared with Russian)
_KZ_MARKERS = {
    "және", "бойынша", "жоба", "қажеттілік", "мемлекеттік", "тауар",
    "көрсетілетін", "қызмет", "сатып", "алу", "бағасы", "жеткізу",
}


def detect_language(text: str) -> str:
    """Detect language of input text.

    Returns:
        "ru" for Russian, "en" for English, "kk" for Kazakh.
    """
    if not text or not text.strip():
        return "ru"

    words = text.lower().split()

    # Check Kazakh markers first
    kz_count = sum(1 for w in words if w in _KZ_MARKERS)
    if kz_count >= 2:
        return "kk"

    # Check for Kazakh-specific characters
    kz_chars = len(_KAZAKH_SPECIFIC.findall(text))
    if kz_chars >= 3:
        return "kk"

    # Count Cyrillic vs Latin characters
    cyrillic_count = len(_CYRILLIC.findall(text))
    latin_count = len(_LATIN.findall(text))

    if cyrillic_count == 0 and latin_count == 0:
        return "ru"

    total = cyrillic_count + latin_count
    if total == 0:
        return "ru"

    latin_ratio = latin_count / total

    if latin_ratio > 0.7:
        return "en"
    return "ru"

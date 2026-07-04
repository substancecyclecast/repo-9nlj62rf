"""Tests for language detection service."""
from __future__ import annotations

from snabagent.services.language import detect_language


def test_detect_russian():
    assert detect_language("Нужны трубы стальные 108х4 ГОСТ") == "ru"


def test_detect_english():
    assert detect_language("We need steel pipes for the project") == "en"


def test_detect_kazakh():
    assert detect_language("Жоба бойынша тауар сатып алу қажеттілік") == "kk"


def test_detect_kazakh_chars():
    assert detect_language("Қазақстан Республикасының мемлекеттік") == "kk"


def test_detect_empty():
    assert detect_language("") == "ru"


def test_detect_whitespace():
    assert detect_language("   ") == "ru"


def test_detect_numbers_only():
    assert detect_language("12345") == "ru"


def test_detect_mixed_cyrillic_latin():
    assert detect_language("Купить steel pipe трубу") == "ru"


def test_detect_mostly_latin():
    assert detect_language("Steel pipes for building construction project tender") == "en"

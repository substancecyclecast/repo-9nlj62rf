"""PII-маскинг audit-логов."""
from __future__ import annotations

from snabagent.audit.logger import _mask_value


def test_mask_string_pii() -> None:
    masked = _mask_value("ИНН 7728168971 email test@a.ru")
    assert "7728168971" not in masked
    assert "test@a.ru" not in masked
    assert "<INN_" in masked
    assert "<EMAIL_" in masked


def test_mask_nested_dict() -> None:
    payload = {"supplier": {"inn": "7728168971", "email": "sales@a.ru"}}
    masked = _mask_value(payload)
    s = str(masked)
    assert "7728168971" not in s
    assert "sales@a.ru" not in s


def test_mask_list_of_dicts() -> None:
    items = [{"phone": "+7 916 123 45 67"}, {"phone": "8 (495) 123 45 67"}]
    masked = _mask_value(items)
    s = str(masked)
    assert "<PHONE_" in s
    # обе строки сматчились
    assert s.count("<PHONE_") == 2


def test_mask_scalar_passthrough() -> None:
    assert _mask_value(42) == 42
    assert _mask_value(None) is None
    assert _mask_value(True) is True


def test_mask_string_without_pii_unchanged() -> None:
    text = "Категория: металлопрокат, объём 10 тонн."
    masked = _mask_value(text)
    assert masked == text

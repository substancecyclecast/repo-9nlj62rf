"""Tests for PII masker."""
from __future__ import annotations

from snabagent.llm.pii_masker import mask_pii, unmask_pii


def test_mask_email():
    text = "Контакт: john@example.com"
    masked, mapping = mask_pii(text)
    assert "john@example.com" not in masked
    assert "<EMAIL_1>" in masked
    assert mapping["<EMAIL_1>"] == "john@example.com"


def test_mask_inn_10():
    text = "ИНН 1234567890"
    masked, mapping = mask_pii(text)
    assert "1234567890" not in masked
    assert "<INN_1>" in masked


def test_mask_phone():
    text = "Звонить +7 (999) 123-45-67"
    masked, mapping = mask_pii(text)
    assert "+7 (999) 123-45-67" not in masked


def test_no_pii():
    text = "Обычный текст без PII"
    masked, mapping = mask_pii(text)
    assert masked == text
    assert len(mapping) == 0


def test_unmask():
    text = "Email: user@test.com"
    masked, mapping = mask_pii(text)
    restored = unmask_pii(masked, mapping)
    assert restored == text


def test_multiple_pii():
    text = "ИНН 1234567890, email: a@b.com, ИНН 9876543210"
    masked, mapping = mask_pii(text)
    assert "1234567890" not in masked
    assert "a@b.com" not in masked
    assert len(mapping) >= 3

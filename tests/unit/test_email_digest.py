"""Tests for email digest rendering."""
from __future__ import annotations

from snabagent.services.email_digest import render_digest_html


def test_render_digest_html_contains_user_name():
    html = render_digest_html("Иван Иванов", 3, 5, 1)
    assert "Иван Иванов" in html


def test_render_digest_html_contains_counts():
    html = render_digest_html("Test User", 10, 20, 5)
    assert "10" in html
    assert "20" in html
    assert "5" in html


def test_render_digest_html_is_valid_html():
    html = render_digest_html("User", 0, 0, 0)
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_render_digest_html_custom_urls():
    html = render_digest_html("U", 0, 0, 0, app_url="https://app.snabagent.ru", unsubscribe_url="https://unsub")
    assert "https://app.snabagent.ru" in html
    assert "https://unsub" in html


def test_render_digest_html_default_urls():
    html = render_digest_html("U", 0, 0, 0)
    assert "http://localhost:8501" in html

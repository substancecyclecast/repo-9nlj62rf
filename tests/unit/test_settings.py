"""Tests for settings module."""
from __future__ import annotations

from snabagent.settings import settings


def test_settings_loaded():
    assert settings is not None


def test_settings_cors_origins():
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0


def test_settings_frontend_url():
    assert isinstance(settings.frontend_url, str)
    assert settings.frontend_url.startswith("http")


def test_settings_app_base_url():
    assert isinstance(settings.app_base_url, str)

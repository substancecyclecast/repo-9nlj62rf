"""Шаблоны промптов (Jinja2)."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent

env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(disabled_extensions=("j2",)),
)


def thousands(n: int | float) -> str:
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", " ")


env.filters["thousands"] = thousands


def render(name: str, **ctx) -> str:
    template = env.get_template(name)
    return template.render(**ctx)

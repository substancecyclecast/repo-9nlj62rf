"""Веб-скрейпер контактных данных. Playwright опционален — для оффлайн-режима возвращаем None."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ...settings import settings

EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w{2,}")
CONTACT_PATHS = ["/contacts", "/contact", "/about", "/o-kompanii", "/kontakty"]


async def find_email(website: str) -> str | None:
    """Возвращает наиболее релевантный e-mail с сайта. None если Playwright недоступен."""
    if not website:
        return None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None
    if not website.startswith("http"):
        website = "https://" + website
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(user_agent=settings.web_scraper_user_agent)
            page = await ctx.new_page()
            for path in [""] + CONTACT_PATHS:
                try:
                    url = urljoin(website, path)
                    await page.goto(url, timeout=settings.web_scraper_timeout_sec * 1000)
                    content = await page.content()
                    emails = EMAIL_RE.findall(content)
                    emails = [
                        e for e in emails
                        if not any(s in e.lower() for s in ["example", "noreply", "wixsite", "sentry"])
                    ]
                    if emails:
                        for pref in ["sales@", "opt@", "zakaz@", "info@", "office@"]:
                            for e in emails:
                                if e.startswith(pref):
                                    await browser.close()
                                    return e
                        await browser.close()
                        return emails[0]
                except Exception:
                    continue
            await browser.close()
    except Exception:
        return None
    return None

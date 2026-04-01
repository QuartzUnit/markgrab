"""Browser engine — Playwright headless for JS-rendered and bot-protected pages."""

import logging
from urllib.parse import urlparse

from markgrab.engine.base import Engine, FetchResult

logger = logging.getLogger(__name__)

# Locale → timezone mapping for browser context
_LOCALE_TIMEZONE: dict[str, str] = {
    "ko-KR": "Asia/Seoul",
    "ja-JP": "Asia/Tokyo",
    "zh-CN": "Asia/Shanghai",
    "en-US": "America/New_York",
}


def _detect_locale(url: str) -> str:
    """Auto-detect locale from URL hostname TLD."""
    hostname = urlparse(url).hostname or ""
    if hostname.endswith(".kr") or any(k in hostname for k in ("naver", "daum", "kakao")):
        return "ko-KR"
    if hostname.endswith(".jp"):
        return "ja-JP"
    if hostname.endswith(".cn"):
        return "zh-CN"
    return "en-US"


class BrowserEngine(Engine):
    """Playwright-based browser engine for JS-heavy and bot-protected sites.

    Requires: pip install markgrab[browser]
    Playwright is imported lazily — the class can be imported without playwright installed.

    Args:
        proxy: Proxy URL.
        stealth: Apply anti-bot stealth scripts (default: False).
        locale: Browser locale (default: auto-detect from URL TLD).
    """

    def __init__(self, *, proxy: str | None = None, stealth: bool = False, locale: str | None = None):
        super().__init__(proxy=proxy)
        self.stealth = stealth
        self.locale = locale  # None = auto-detect per request

    async def fetch(self, url: str, *, timeout: float = 30.0) -> FetchResult:
        from playwright.async_api import async_playwright

        timeout_ms = int(timeout * 1000)
        locale = self.locale or _detect_locale(url)
        timezone_id = _LOCALE_TIMEZONE.get(locale, "America/New_York")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context_kwargs: dict = {
                    "viewport": {"width": 1920, "height": 1080},
                    "locale": locale,
                    "timezone_id": timezone_id,
                    "user_agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                        " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                }
                if self.proxy:
                    context_kwargs["proxy"] = {"server": self.proxy}

                context = await browser.new_context(**context_kwargs)
                if self.stealth:
                    from markgrab.anti_bot.stealth import apply_stealth

                    await apply_stealth(context)

                page = await context.new_page()
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )

                # Best-effort wait for JS rendering (max 8s or half timeout)
                networkidle_ms = min(8000, timeout_ms // 2)
                try:
                    await page.wait_for_load_state("networkidle", timeout=networkidle_ms)
                except Exception:
                    pass  # DOM content is enough

                html = await page.content()

                # CloudFlare/bot challenge retry — if page is suspiciously small,
                # wait for challenge script to resolve and re-read (max 3 retries)
                for _ in range(3):
                    if len(html) >= 20_000:
                        break
                    import asyncio as _aio

                    await _aio.sleep(2)
                    html = await page.content()
                status = response.status if response else 200
                headers = response.headers if response else {}

                return FetchResult(
                    html=html,
                    status_code=status,
                    content_type=headers.get("content-type", "text/html"),
                    final_url=page.url,
                )
            finally:
                await browser.close()

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Optional
from app.config import settings
from app.core.logging import logger
from app.core.exceptions import BrowserError


class BrowserService:
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self, headless: Optional[bool] = None) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless if headless is not None else settings.playwright_headless
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        self._page = await self._context.new_page()
        logger.info("browser_started")

    async def navigate(self, url: str) -> None:
        if not self._page:
            raise BrowserError("Browser not started")
        try:
            await self._page.goto(url, wait_until="networkidle")
            logger.info("navigated_to", url=url)
        except Exception as e:
            raise BrowserError(f"Navigation failed: {e}") from e

    async def get_page_content(self) -> str:
        if not self._page:
            raise BrowserError("Browser not started")
        return await self._page.content()

    async def get_visible_text(self) -> str:
        if not self._page:
            raise BrowserError("Browser not started")
        return await self._page.inner_text("body")

    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> None:
        if not self._page:
            raise BrowserError("Browser not started")
        await self._page.wait_for_selector(selector, timeout=timeout)

    async def click(self, selector: str) -> None:
        if not self._page:
            raise BrowserError("Browser not started")
        await self._page.click(selector)

    async def evaluate(self, script: str):
        if not self._page:
            raise BrowserError("Browser not started")
        return await self._page.evaluate(script)

    async def screenshot(self, path: str) -> None:
        if not self._page:
            raise BrowserError("Browser not started")
        await self._page.screenshot(path=path, full_page=True)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("browser_stopped")

    @property
    def page(self) -> Page:
        if not self._page:
            raise BrowserError("Browser not started")
        return self._page


browser_service = BrowserService()

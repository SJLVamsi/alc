from typing import Optional
from app.services.browser import browser_service
from app.core.logging import logger
from app.core.exceptions import NavigationError


class CourseNavigator:
    async def detect_platform(self, url: str) -> str:
        if "udemy.com" in url:
            return "udemy"
        if "coursera.org" in url:
            return "coursera"
        if "udacity.com" in url:
            return "udacity"
        if "edx.org" in url:
            return "edx"
        if "pluralsight.com" in url:
            return "pluralsight"
        return "generic"

    async def get_course_title(self) -> str:
        try:
            text = await browser_service.get_visible_text()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            return lines[0] if lines else "Unknown Course"
        except Exception as e:
            raise NavigationError(f"Could not get course title: {e}") from e

    async def get_module_list(self) -> list[dict]:
        modules = []
        try:
            page = browser_service.page
            module_elements = await page.query_selector_all(
                '[class*="module"], [class*="section"], [class*="chapter"]'
            )
            for el in module_elements:
                title = await el.inner_text()
                modules.append({"name": title.strip(), "url": page.url})
        except Exception as e:
            logger.warning("module_list_fallback", error=str(e))
        return modules

    async def get_lessons_in_module(self, module_selector: str = "") -> list[dict]:
        lessons = []
        try:
            page = browser_service.page
            lesson_elements = await page.query_selector_all(
                f'{module_selector} [class*="lesson"], [class*="lecture"], [class*="video"]'
            )
            for el in lesson_elements:
                title = await el.inner_text()
                href = await el.get_attribute("href") or ""
                lessons.append({"title": title.strip(), "url": href})
        except Exception as e:
            logger.warning("lesson_list_fallback", error=str(e))
        return lessons

    async def detect_lesson_completion(self) -> bool:
        try:
            page = browser_service.page
            completed = await page.query_selector(
                '[class*="completed"], [class*="checked"], [aria-label*="completed"]'
            )
            return completed is not None
        except Exception:
            return False

    async def open_next_lesson(self) -> Optional[str]:
        try:
            page = browser_service.page
            next_btn = await page.query_selector(
                '[class*="next"], [aria-label*="Next"], [data-purpose*="next"]'
            )
            if next_btn:
                await next_btn.click()
                await page.wait_for_load_state("networkidle")
                return page.url
            return None
        except Exception as e:
            raise NavigationError(f"Could not open next lesson: {e}") from e

    async def extract_lesson_content(self) -> dict:
        try:
            title_el = await browser_service.page.query_selector("h1")
            title = await title_el.inner_text() if title_el else "Untitled Lesson"
            text = await browser_service.get_visible_text()
            return {"title": title.strip(), "text": text}
        except Exception as e:
            raise NavigationError(f"Could not extract lesson content: {e}") from e


course_navigator = CourseNavigator()

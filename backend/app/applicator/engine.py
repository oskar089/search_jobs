import asyncio
import logging
import random

logger = logging.getLogger(__name__)


class AutoApplicator:
    """Playwright-based automated job application submitter.

    - Navigates to the job posting URL
    - Finds and clicks the apply button
    - Fills name, email, and cover letter fields with human-like typing delays
    - Submits the form
    - Returns submission status
    """

    def __init__(self, headless: bool = True, timeout: int = 30000) -> None:
        self.headless = headless
        self.timeout = timeout
        self._browser = None
        self._playwright = None

    async def _get_browser(self):
        """Lazy-init the Playwright browser instance."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
            )
        return self._browser

    async def apply(
        self,
        job_url: str,
        cover_letter: str,
        name: str,
        email: str,
    ) -> dict:
        """Submit a job application via browser automation.

        Returns ``{"status": "submitted"}`` on success,
        or ``{"status": "failed", "error": "..."}`` on failure.
        """
        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            await page.goto(job_url, timeout=self.timeout, wait_until="domcontentloaded")

            # --- Find & click apply button ---
            apply_selectors = [
                "button:has-text('Apply')",
                "a:has-text('Apply')",
                "[data-testid*='apply']",
                "[class*='apply']",
                "button:has-text('Postular')",
                "a:has-text('Postular')",
                "button:has-text('Solicitar')",
                "a:has-text('Solicitar')",
            ]

            apply_clicked = False
            for sel in apply_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        await btn.click()
                        apply_clicked = True
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            if not apply_clicked:
                logger.info("No apply button found — attempting direct form fill")

            # --- Fill form fields ---
            await self._type_with_delay(
                page,
                'input[name="name"], input[id*="name"]',
                name,
            )
            await self._type_with_delay(
                page,
                'input[type="email"], input[name="email"]',
                email,
            )
            await self._type_with_delay(
                page,
                'textarea[name*="cover"], textarea[id*="cover"], '
                'textarea[class*="cover"], textarea[name*="message"], '
                'textarea[id*="message"]',
                cover_letter,
            )

            # --- Find & click submit ---
            submit_selectors = [
                "button[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Send')",
                "button:has-text('Enviar')",
                "button:has-text('Apply')",
                "button:has-text('Postular')",
            ]

            submitted = False
            for sel in submit_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        await btn.click()
                        submitted = True
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            if not submitted:
                return {"status": "failed", "error": "Submit button not found"}

            return {"status": "submitted"}

        except Exception as exc:
            logger.error("Auto-apply failed for %s: %s", job_url, exc)
            return {"status": "failed", "error": str(exc)}

        finally:
            await context.close()

    async def _type_with_delay(self, page, selector: str, text: str) -> None:
        """Type text into a field with 50–150 ms random keystroke delays."""
        try:
            el = await page.wait_for_selector(selector, timeout=10000)
            if not el:
                logger.debug("Field not found: %s", selector)
                return
            await el.click()
            await el.fill("")
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
        except Exception as exc:
            logger.debug("Could not fill field %s: %s", selector, exc)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self) -> "AutoApplicator":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

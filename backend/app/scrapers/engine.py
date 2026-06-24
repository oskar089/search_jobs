import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PortalSelectors:
    """Selectors used by the scraper to extract job fields from a portal page."""

    job_card: str
    title: str
    company: str
    location: str | None = None
    description: str = ""
    url: str = ""
    salary: str | None = None
    posted_date: str | None = None
    apply_button: str | None = None


@dataclass
class ScrapedJob:
    """Structured result from a single job listing scrape."""

    external_id: str | None = None
    title: str = ""
    company: str = ""
    location: str | None = None
    description: str = ""
    url: str = ""
    salary_range: str | None = None
    posted_at: str | None = None  # Kept as string for flexibility across portals
    language: str = "en"


class ScraperEngine:
    """Async Playwright-based scraping engine with configurable selectors.

    Usage:
        async with ScraperEngine(headless=True, timeout=30000) as engine:
            jobs = await engine.scrape(url, selectors, max_results=25)
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        linkedin_email: str | None = None,
        linkedin_password: str | None = None,
    ) -> None:
        self.headless = headless
        self.timeout = timeout
        self._linkedin_email = linkedin_email
        self._linkedin_password = linkedin_password
        self._browser = None
        self._playwright = None

    async def _get_browser(self) -> Any:
        """Lazy-init the Playwright browser instance."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
            )
        return self._browser

    async def scrape(
        self,
        url: str,
        selectors: PortalSelectors,
        max_results: int = 25,
    ) -> list[ScrapedJob]:
        """Scrape a portal page and return parsed job listings.

        Retries up to 3 times with exponential backoff on failure.
        """
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self._scrape_page(url, selectors, max_results)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Scrape attempt %d/3 failed for %s: %s",
                    attempt + 1,
                    url,
                    exc,
                )
                if attempt < 2:
                    await asyncio.sleep(2**attempt)  # 1s, 2s
        raise RuntimeError(
            f"Scrape failed after 3 retries for {url}: {last_error}",
        ) from last_error

    async def dry_run(
        self,
        url: str,
        selectors: PortalSelectors,
    ) -> list[ScrapedJob]:
        """Run a dry-run scrape for testing purposes.

        Identical to scrape() but explicitly named to signal that results
        should NOT be persisted by the caller.
        """
        return await self.scrape(url, selectors, max_results=10)

    async def _login_linkedin(self, context: Any) -> None:
        """Log into LinkedIn before scraping, if credentials are configured.

        LinkedIn's login page uses dynamic Sdui-generated field IDs,
        so we locate by input[type=email] and input[type=password].
        """
        if not self._linkedin_email or not self._linkedin_password:
            return
        page = await context.new_page()
        try:
            logger.info("Logging into LinkedIn...")
            await page.goto("https://www.linkedin.com/login", timeout=self.timeout)
            await page.wait_for_timeout(5000)

            email_input = page.locator("input[type=email]").first
            password_input = page.locator("input[type=password]").first
            await email_input.wait_for(state="attached", timeout=15000)
            await password_input.wait_for(state="attached", timeout=5000)

            # LinkedIn uses Sdui with hidden fields — force=True bypasses visibility check
            await email_input.fill(self._linkedin_email, force=True)
            await password_input.fill(self._linkedin_password, force=True)
            await password_input.press("Enter")
            await page.wait_for_timeout(5000)

            current = page.url
            if "/login" in current and "linkedin.com" in current:
                logger.warning("LinkedIn login failed — still on login page")
            else:
                logger.info("LinkedIn login successful")
        finally:
            await page.close()

    async def _scrape_page(
        self,
        url: str,
        selectors: PortalSelectors,
        max_results: int,
    ) -> list[ScrapedJob]:
        """Perform a single scrape attempt against the given URL."""
        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )

        # LinkedIn login (if configured)
        if "linkedin.com" in url:
            await self._login_linkedin(context)

        page = await context.new_page()

        try:
            await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")

            # Wait for the job card container to appear
            await page.wait_for_selector(selectors.job_card, timeout=self.timeout)

            cards = await page.query_selector_all(selectors.job_card)
            cards = cards[:max_results]

            jobs: list[ScrapedJob] = []
            for card in cards:
                try:
                    job = await self._extract_job(card, selectors)
                    if job.title and job.company:
                        jobs.append(job)
                except Exception as exc:
                    logger.debug("Skipping malformed card: %s", exc)
                    continue

            return jobs
        finally:
            await context.close()

    async def _extract_job(
        self,
        card: Any,
        selectors: PortalSelectors,
    ) -> ScrapedJob:
        """Extract job fields from a single card element using the given selectors."""
        title_el = await card.query_selector(selectors.title)
        company_el = await card.query_selector(selectors.company)
        url_el = await card.query_selector(selectors.url) if selectors.url else None

        title = await title_el.inner_text() if title_el else ""
        company = await company_el.inner_text() if company_el else ""
        href = await url_el.get_attribute("href") if url_el else ""

        location = None
        if selectors.location:
            loc_el = await card.query_selector(selectors.location)
            if loc_el:
                location = (await loc_el.inner_text()).strip()

        description = ""
        if selectors.description:
            desc_el = await card.query_selector(selectors.description)
            if desc_el:
                description = await desc_el.inner_text()

        salary_range = None
        if selectors.salary:
            sal_el = await card.query_selector(selectors.salary)
            if sal_el:
                salary_range = (await sal_el.inner_text()).strip()

        posted_at = None
        if selectors.posted_date:
            date_el = await card.query_selector(selectors.posted_date)
            if date_el:
                posted_attr = await date_el.get_attribute("datetime")
                posted_at = posted_attr or (await date_el.inner_text()).strip()

        return ScrapedJob(
            title=title.strip(),
            company=company.strip(),
            location=location,
            description=description.strip() if description else "",
            url=href.strip() if href else "",
            salary_range=salary_range,
            posted_at=posted_at,
            language="en",
        )

    async def close(self) -> None:
        """Close the browser and Playwright instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self) -> "ScraperEngine":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

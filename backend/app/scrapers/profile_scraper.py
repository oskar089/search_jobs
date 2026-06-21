"""Profile scraping abstraction for public profile pages.

Follows the same Playwright-based pattern as the job listing scraper
(``ScraperEngine``) but targets individual profile pages rather than
job search result listings.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.profiles.schemas import ImportedProfile, SkillItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_SKILL_LEVEL = "advanced"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class ProfileScraper(ABC):
    """Abstract base for scraping public profile pages.

    Subclasses MUST implement ``_scrape_profile()`` and define
    ``profile_selectors`` — a dict mapping logical field names
    (e.g. ``headline``, ``skills``) to CSS selectors on the target
    portal.

    Usage::

        scraper = SomeProfileScraper()
        profile = await scraper.parse_profile("https://...")
    """

    # Subclasses MUST override with portal-specific CSS selectors.
    profile_selectors: dict[str, str] = {}

    async def parse_profile(self, url: str) -> ImportedProfile:
        """Navigate to the profile URL and extract fields.

        Parameters
        ----------
        url:
            Full URL to a public profile page on the target portal.

        Returns
        -------
        ImportedProfile
            The extracted profile data.
        """
        return await self._scrape_profile(url)

    # ------------------------------------------------------------------
    # Subclass API
    # ------------------------------------------------------------------

    @abstractmethod
    async def _scrape_profile(self, url: str) -> ImportedProfile:
        """Implement the scraping strategy for the target portal.

        Subclasses use Playwright, httpx+BeautifulSoup, or any other
        method to extract profile data from the page.
        """
        ...

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    async def _get_text(self, page: object, field: str) -> str | None:
        """Extract inner text of the first matching selector, or ``None``."""
        sel = self.profile_selectors.get(field)
        if not sel:
            return None
        el = await page.query_selector(sel)
        if el is None:
            return None
        return (await el.inner_text()).strip() or None

    async def _get_text_or_none(self, page: object, field: str) -> str | None:
        """Like ``_get_text`` but always returns str | None (never empty)."""
        return await self._get_text(page, field)

    async def _get_all_text(self, page: object, field: str) -> list[str]:
        """Extract inner text from all elements matching the selector."""
        sel = self.profile_selectors.get(field)
        if not sel:
            return []
        els = await page.query_selector_all(sel)
        results: list[str] = []
        for el in els:
            text = (await el.inner_text()).strip()
            if text:
                results.append(text)
        return results

    async def _extract_experience(self, page: object) -> list:
        """Extract work experience cards from the profile page.

        Override ``profile_selectors`` keys ``experience_card``,
        ``experience_title``, ``experience_company``,
        ``experience_description`` to customise for each portal.
        """
        from app.profiles.schemas import ExperienceItem

        card_sel = self.profile_selectors.get("experience_card")
        if not card_sel:
            return []

        cards = await page.query_selector_all(card_sel)
        results: list = []
        for card in cards:
            title_el = await card.query_selector(
                self.profile_selectors.get("experience_title", ""),
            )
            company_el = await card.query_selector(
                self.profile_selectors.get("experience_company", ""),
            )
            desc_el = await card.query_selector(
                self.profile_selectors.get("experience_description", ""),
            )

            title = (await title_el.inner_text()).strip() if title_el else ""
            company = (await company_el.inner_text()).strip() if company_el else ""

            if not title and not company:
                continue

            description = (
                (await desc_el.inner_text()).strip() if desc_el else None
            )

            results.append(
                ExperienceItem(
                    company=company or "Unknown",
                    role=title or "Unknown",
                    description=description,
                ),
            )

        return results


# ---------------------------------------------------------------------------
# Infojobs implementation
# ---------------------------------------------------------------------------


class InfojobsProfileScraper(ProfileScraper):
    """Scraper for Infojobs Argentina public profile pages.

    CSS selectors target the public profile page structure at the time
    of writing. Infojobs may update its DOM — verify selectors if
    scraping returns empty results.
    """

    profile_selectors: dict[str, str] = {
        # Main fields
        "headline": "h1.profile-name",
        "summary": "div.profile-summary",
        "skills": "span.skill-tag",
        "location": "span.profile-location",
        # Experience cards
        "experience_card": "div.experience-item",
        "experience_title": "h3.experience-title",
        "experience_company": "span.experience-company",
        "experience_description": "p.experience-description",
    }

    async def _scrape_profile(self, url: str) -> ImportedProfile:
        """Extract profile data using Playwright."""
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                # --- Headline ---
                headline = await self._get_text(page, "headline")

                # --- Summary ---
                summary = await self._get_text(page, "summary")

                # --- Skills ---
                raw_skills = await self._get_all_text(page, "skills")
                skills = [
                    SkillItem(name=s, level=_DEFAULT_SKILL_LEVEL)
                    for s in raw_skills
                    if s
                ]

                # --- Location (optional) ---

                # --- Work experience ---
                work_experience = await self._extract_experience(page)

                return ImportedProfile(
                    headline=headline,
                    summary=summary,
                    skills=skills,
                    work_experience=work_experience,
                    infojobs_url=url,
                )
            finally:
                await context.close()
                await browser.close()

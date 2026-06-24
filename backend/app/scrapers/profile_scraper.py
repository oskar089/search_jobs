"""Profile scraping abstraction for public profile pages.

Follows the same Playwright-based pattern as the job listing scraper
(``ScraperEngine``) but targets individual profile pages rather than
job search result listings.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.profiles.schemas import ImportedProfile, SkillItem

if TYPE_CHECKING:
    from playwright.async_api import Page as PwPage

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

    async def _get_text(self, page: "PwPage", field: str) -> str | None:
        """Extract inner text of the first matching selector, or ``None``."""
        sel = self.profile_selectors.get(field)
        if not sel:
            return None
        el = await page.query_selector(sel)
        if el is None:
            return None
        return (await el.inner_text()).strip() or None

    async def _get_text_or_none(self, page: "PwPage", field: str) -> str | None:
        """Like ``_get_text`` but always returns str | None (never empty)."""
        return await self._get_text(page, field)

    async def _get_all_text(self, page: "PwPage", field: str) -> list[str]:
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

    async def _extract_experience(self, page: "PwPage") -> list:
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


# ---------------------------------------------------------------------------
# LinkedIn implementation (free, Playwright-based)
# ---------------------------------------------------------------------------


class LinkedInProfileScraper(ProfileScraper):
    """Scraper for LinkedIn public profile pages using Playwright.

    NOTE: LinkedIn requires login to view most profiles and employs
    aggressive anti-bot measures. This scraper works BEST when:
      - The target profile is set to "public" in LinkedIn's privacy settings
      - You are running from a residential IP (no datacenter VPN)
      - LinkedIn hasn't changed their DOM recently

    If the scraper returns empty or hits a login wall, the profile
    likely requires authentication. Consider:
      1. Setting the ``LINKEDIN_EMAIL`` and ``LINKEDIN_PASSWORD`` env vars
         to auto-login before scraping.
      2. Using the Scrapin.io API (paid) if you need reliable LinkedIn data.

    CSS selectors target LinkedIn's public profile page as of 2025.
    LinkedIn changes their DOM frequently — verify selectors if scraping
    returns empty results.
    """

    profile_selectors: dict[str, str] = {
        # Main fields (public profile)
        "headline": "div.text-body-medium",
        "summary": "section.summary div.inline-show-more-text",
        "skills": "span.pill.pill--expandable",
        "location": "span.text-body-small.inline t-black--light",
        # Experience cards
        "experience_card": "li.profile-section-card",
        "experience_title": "h3.profile-section-card__title",
        "experience_company": "p.profile-section-card__subtitle",
        "experience_description": "div.inline-show-more-text",
    }

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
    ) -> None:
        self._email = email or ""
        self._password = password or ""

    async def _scrape_profile(self, url: str) -> ImportedProfile:
        """Extract profile data using Playwright, with optional login."""
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()

            try:
                # --- Optional login (helps with public profile access) ---
                if self._email and self._password:
                    await self._login(page)

                # --- Navigate to profile ---
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                # Wait a moment for dynamic content to render
                await page.wait_for_timeout(3000)

                # Check if we hit a login/auth wall (redirected to /login or /authwall)
                current_url = page.url.lower()
                if ("/login" in current_url or "/authwall" in current_url or "/signup" in current_url) and "linkedin.com" in current_url:
                    raise ValueError(
                        "LinkedIn requires login to view this profile. "
                        "Check your LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env, "
                        "or use the Scrapin.io API key for reliable access.",
                    )

                # --- Extract fields ---
                headline = await self._get_text(page, "headline")
                summary = await self._get_text(page, "summary")

                raw_skills = await self._get_all_text(page, "skills")
                skills = [
                    SkillItem(name=s, level=_DEFAULT_SKILL_LEVEL)
                    for s in raw_skills
                    if s
                ]

                work_experience = await self._extract_experience(page)

                return ImportedProfile(
                    headline=headline,
                    summary=summary,
                    skills=skills,
                    work_experience=work_experience,
                    linkedin_url=url,
                )
            finally:
                await context.close()
                await browser.close()

    async def _login(self, page: "PwPage") -> None:
        """Log into LinkedIn and wait until login completes or fail.

        Raises
        ------
        ValueError
            If login fails (wrong credentials, challenge page, or timeout).
        """
        await page.goto("https://www.linkedin.com/login", timeout=20000)
        await page.wait_for_timeout(3000)

        # LinkedIn uses dynamic Sdui-generated IDs. Find fields by type.
        email_input = page.locator("input[type=email]").first
        password_input = page.locator("input[type=password]").first
        await email_input.wait_for(state="attached", timeout=15000)
        await password_input.wait_for(state="attached", timeout=5000)

        # LinkedIn uses Sdui with hidden fields — force=True bypasses visibility check
        await email_input.fill(self._email, force=True)
        await password_input.fill(self._password, force=True)
        await password_input.press("Enter")

        # Wait for URL to change away from /login (indicates login processed)
        try:
            await page.wait_for_function(
                "() => !window.location.href.includes('/login')",
                timeout=15000,
            )
        except Exception:
            # Timeout means we never left /login — credentials likely wrong
            raise ValueError(
                "LinkedIn login failed — wrong credentials or expired password. "
                "Update LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env",
            )

        # Additional wait for any post-login redirects (2FA, feed, etc.)
        await page.wait_for_timeout(3000)

        # Check for common post-login challenge pages
        current_url = page.url.lower()
        if "checkpoint" in current_url or "challenge" in current_url:
            raise ValueError(
                "LinkedIn requires additional verification (2FA or device challenge). "
                "Try logging in manually in a regular browser first, or use the Scrapin.io API key.",
            )

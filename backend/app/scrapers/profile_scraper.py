"""Profile scraping abstraction for public profile pages.

Follows the same Playwright-based pattern as the job listing scraper
(``ScraperEngine``) but targets individual profile pages rather than
job search result listings.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from app.profiles.schemas import ImportedProfile, SkillItem

if TYPE_CHECKING:
    from playwright.async_api import Page as PwPage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_SKILL_LEVEL = "advanced"

# Path for persistent LinkedIn auth state (saved after first successful login)
_LINKEDIN_AUTH_FILE = Path(__file__).parents[2] / "linkedin_auth.json"

# Anti-headless stealth script that runs on every page in the context.
# LinkedIn and other sites check these properties to detect automation.
_STEALTH_SCRIPT = """
// Hide Playwright automation痕迹
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});
// Restore plugins (headless has 0 by default)
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
// Restore languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['es-AR', 'en-US', 'en'],
});
// Chromium headless check (chrome might not exist on all pages)
if (typeof chrome !== 'undefined') {
    Object.defineProperty(chrome, 'runtime', {
        get: () => ({
            connect: () => ({}),
            sendMessage: () => ({}),
        }),
    });
}
// WebGL vendor — headless returns "Google Inc. (ANGLE)"
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter(param);
};
"""


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
        # LinkedIn uses CSS-in-JS with hashed class names — semantic selectors
        # don't work. Instead we use stable data-testid attributes.
        "headline": "",  # Handled by JS extraction below
        "summary": "",
        "skills": "",  # Handled by JS extraction below
        "experience_section": "[data-testid^='profile_ExperienceTopLevelSection_']",
        "skills_section": "[data-testid^='profile_Skills_']",
        "education_section": "[data-testid^='profile_EducationTopLevelSection_']",
    }

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        auth_file: str | None = None,
    ) -> None:
        self._email = email or ""
        self._password = password or ""
        self._auth_file = Path(auth_file) if auth_file else _LINKEDIN_AUTH_FILE

    async def _scrape_profile(self, url: str) -> ImportedProfile:
        """Extract profile data using Playwright, with optional login."""
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--window-size=1280,720",
                ],
            )

            # --- Try loading persistent auth state ---
            storage_state = None
            if self._auth_file.exists():
                logger.info("Loading persistent LinkedIn auth from %s", self._auth_file)
                storage_state = str(self._auth_file)

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
                storage_state=storage_state,
            )

            # Inject anti-headless stealth script on every page
            await context.add_init_script(_STEALTH_SCRIPT)

            page = await context.new_page()

            try:
                # --- Optional login (fresh, not needed if auth_file works) ---
                login_was_performed = False
                if self._email and self._password and not storage_state:
                    await self._login(page)
                    login_was_performed = True

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

                # --- Scroll workspace to trigger lazy section loading ---
                await page.evaluate("""
                    const ws = document.getElementById('workspace');
                    if (ws) {
                        ws.scrollTo(0, ws.scrollHeight);
                    } else {
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                """)
                await page.wait_for_timeout(2000)

                # --- Extract headline via JS (classes are hashed) ---
                headline = await page.evaluate("""
                    () => {
                        const els = document.querySelectorAll('p');
                        for (const el of els) {
                            const text = el.textContent.trim();
                            if (text.length > 10 && text.length < 200
                                && !text.includes('http')
                                && el.closest('[data-testid]') === null) {
                                return text;
                            }
                        }
                        return null;
                    }
                """) or None

                # --- Extract skills from data-testid section ---
                raw_skills = await page.evaluate("""
                    () => {
                        const section = document.querySelector('[data-testid^="profile_Skills_"]');
                        if (!section) return [];
                        const items = section.querySelectorAll('[data-testid^="profile_Skill_"]');
                        if (items.length > 0) {
                            return Array.from(items).map(el => el.textContent.trim()).filter(Boolean);
                        }
                        // Fallback: extract all visible text items
                        const texts = new Set();
                        section.querySelectorAll('span, p, div[class*="_52e8c184"]').forEach(el => {
                            const t = el.textContent.trim();
                            // Filter out section headings, empty text, and boilerplate
                            if (t && t.length > 1 && t.length < 100
                                && !t.startsWith('Aptitudes')
                                && !t.startsWith('Skills')
                                && !t.startsWith('Mostrar')
                                && t !== '·') {
                                texts.add(t);
                            }
                        });
                        return Array.from(texts);
                    }
                """) or []
                skills = [
                    SkillItem(name=s, level=_DEFAULT_SKILL_LEVEL)
                    for s in raw_skills
                    if s
                ]

                # --- Extract experience by parsing section text ---
                work_experience = await self._extract_linkedin_experience(page)

                return ImportedProfile(
                    headline=headline,
                    summary="",
                    skills=skills,
                    work_experience=work_experience,
                    linkedin_url=url,
                )
            finally:
                # If we just logged in successfully, save the session for future runs
                if login_was_performed and self._auth_file:
                    try:
                        await context.storage_state(path=str(self._auth_file))
                        logger.info("Saved LinkedIn auth state to %s", self._auth_file)
                    except Exception as exc:
                        logger.warning("Could not save LinkedIn auth state: %s", exc)
                await context.close()
                await browser.close()

    async def _login(self, page: "PwPage") -> None:
        """Log into LinkedIn and wait until login completes or fail.

        Uses multiple strategies to overcome LinkedIn's headless detection:
        1. Type fields slowly (more human than fill)
        2. Click the submit button explicitly (more reliable than Enter)
        3. Fallback to pressing Enter if button is hidden
        4. Diagnose what went wrong (wrong creds, browser blocked, challenge)

        Raises
        ------
        ValueError
            If login fails with details about the failure reason.
        """
        await page.goto("https://www.linkedin.com/login", timeout=20000)
        await page.wait_for_timeout(3000)

        # --- Wait for the form to be ready ---
        email_input = page.locator("input[type=email]").first
        password_input = page.locator("input[type=password]").first
        await email_input.wait_for(state="attached", timeout=15000)
        await password_input.wait_for(state="attached", timeout=5000)

        # Small human-like pause before typing
        await page.wait_for_timeout(500)

        # Use type() instead of fill() — simulates real keystrokes,
        # which LinkedIn's Sdui form handler expects
        await email_input.type(self._email, delay=40)
        await page.wait_for_timeout(300)
        await password_input.type(self._password, delay=30)
        await page.wait_for_timeout(600)

        # --- Submit ---
        # Try clicking the submit button first
        submit_btn = page.locator("button[type=submit]").first
        btn_visible = False
        try:
            await submit_btn.wait_for(state="visible", timeout=3000)
            btn_visible = True
        except Exception:
            pass

        # Try to ensure the form processes our input before submitting
        await page.wait_for_timeout(300)

        if btn_visible:
            await submit_btn.click()
        else:
            # Fallback: press Enter
            logger.info("Submit button not visible, pressing Enter")
            await password_input.press("Enter")

        # --- Wait for navigation result ---
        await page.wait_for_timeout(3000)

        # Quick check: are we on a checkpoint/challenge page?
        current_url = page.url.lower()
        if "checkpoint" in current_url or "challenge" in current_url:
            raise ValueError(
                "LinkedIn requires additional verification (2FA or device challenge). "
                "Run `python backend/tools/setup_linkedin_auth.py` to log in manually "
                "in a visible browser window — 2FA will work there.",
            )

        # Longer wait: wait for ANY navigation away from /login
        if "/login" in current_url:
            try:
                await page.wait_for_function(
                    "() => !window.location.href.includes('/login')",
                    timeout=12000,
                )
            except Exception:
                # Still on /login after submit — diagnose
                body_text = await page.inner_text("body")

                if any(w in body_text.lower() for w in ("incorrect", "not match", "wrong password")):
                    raise ValueError(
                        "LinkedIn says the email or password is incorrect. "
                        "Verify your LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env",
                    )
                raise ValueError(
                    "LinkedIn login blocked — the browser automation was detected.\n\n"
                    "  Your credentials are probably correct, but LinkedIn's anti-bot "
                    "system rejected the headless login.\n\n"
                    "  Solution — run this once to save a real browser session:\n\n"
                    "    python backend/tools/setup_linkedin_auth.py\n\n"
                    "  It opens a visible Chromium window for manual login (2FA works too).\n"
                    "  After that, the scraper reuses the saved session automatically.",
                )

        # Final check for challenge pages (post-navigation)
        current_url = page.url.lower()
        if "checkpoint" in current_url or "challenge" in current_url:
            raise ValueError(
                "LinkedIn requires additional verification (2FA or device challenge). "
                "Run `python backend/tools/setup_linkedin_auth.py` to log in manually "
                "in a visible browser window.",
            )

    async def _extract_linkedin_experience(self, page: "PwPage") -> list:
        """Extract work experience from LinkedIn's current DOM.

        LinkedIn uses CSS-in-JS with hashed class names, so we can't
        rely on semantic selectors. Instead, we parse the text content
        of the experience section and split it into cards using <hr>
        separators.
        """
        from app.profiles.schemas import ExperienceItem

        cards = await page.evaluate("""
            () => {
                const section = document.querySelector(
                    '[data-testid^="profile_ExperienceTopLevelSection_"]'
                );
                if (!section) return [];

                // Get the card container (second div inside the section)
                const container = section.children[1];
                if (!container) return [];

                // Split cards by <hr> separator
                const cards = [];
                let currentCard = [];

                for (const child of container.children) {
                    if (child.tagName === 'HR') {
                        if (currentCard.length > 0) {
                            cards.push(currentCard.join('\\n'));
                            currentCard = [];
                        }
                        continue;
                    }
                    const text = child.textContent.trim();
                    if (text && !text.startsWith('·')) {
                        currentCard.push(text);
                    }
                }
                if (currentCard.length > 0) {
                    cards.push(currentCard.join('\\n'));
                }
                return cards;
            }
        """) or []

        results = []
        for card_text in cards:
            lines = [l.strip() for l in card_text.split('\n') if l.strip()]
            if not lines:
                continue

            # First line is usually the role/title
            role = lines[0] if len(lines) > 0 else "Unknown"
            # Second line is usually the company
            company_text = lines[1] if len(lines) > 1 else ""
            # Remove date ranges (e.g. "· 2 yrs 6 mos" or "· 2020 - 2023")
            # Dates appear at the end of the company line or as separate lines
            description = '\n'.join(lines[2:]) if len(lines) > 2 else None
            # Clean up date ranges from company
            if '·' in company_text:
                company_text = company_text.split('·')[0].strip()

            results.append(
                ExperienceItem(
                    company=company_text or "Unknown",
                    role=role or "Unknown",
                    description=description,
                ),
            )

        return results

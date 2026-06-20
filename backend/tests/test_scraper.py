"""Integration tests for the scraper engine's selector parsing logic.

Tests that each built-in portal selector set correctly extracts job data
from static HTML fixture files using BeautifulSoup — no browser needed.

This validates the *parsing contract*: given the same HTML structure each
portal's selectors claim to target, do the selectors produce the expected
output? A passing test means the selectors match the DOM assumptions in the
design. A failing test means either the selectors or the fixtures need
updating.
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.scrapers.builtin.bumeran import BUMERAN_SELECTORS
from app.scrapers.builtin.computrabajo import COMPUTRABAJO_SELECTORS
from app.scrapers.builtin.infojobs import INFOJOBS_SELECTORS
from app.scrapers.builtin.linkedin import LINKEDIN_SELECTORS

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ── Helper: mirror of ScraperEngine._extract_job using BeautifulSoup ────


def parse_jobs_from_html(html: str, selectors: dict) -> list[dict]:
    """Parse job cards from static HTML using CSS selectors via BeautifulSoup.

    Mirrors the extraction logic in ``ScraperEngine._extract_job`` so we
    can test selector correctness without launching a Playwright browser.

    Returns a list of dicts with keys matching ``ScrapedJob`` fields.
    """
    soup = BeautifulSoup(html, "html.parser")
    job_card_selector = selectors.get("job_card")
    if not job_card_selector:
        return []
    cards = soup.select(job_card_selector)
    jobs: list[dict] = []

    for card in cards:
        title_el = card.select_one(selectors["title"]) if selectors.get("title") else None
        company_el = card.select_one(selectors["company"]) if selectors.get("company") else None
        url_el = card.select_one(selectors["url"]) if selectors.get("url") else None

        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""
        href = url_el.get("href", "") if url_el else ""

        # Skip cards missing the minimum required fields
        if not title or not company:
            continue

        location: str | None = None
        if selectors.get("location"):
            loc_el = card.select_one(selectors["location"])
            if loc_el is not None:
                location = loc_el.get_text(strip=True)

        description = ""
        if selectors.get("description"):
            desc_el = card.select_one(selectors["description"])
            if desc_el is not None:
                description = desc_el.get_text(strip=True)

        salary_range: str | None = None
        if selectors.get("salary"):
            sal_el = card.select_one(selectors["salary"])
            if sal_el is not None:
                salary_range = sal_el.get_text(strip=True)

        posted_at: str | None = None
        if selectors.get("posted_date"):
            date_el = card.select_one(selectors["posted_date"])
            if date_el is not None:
                posted_at = date_el.get("datetime") or date_el.get_text(strip=True)

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "url": href,
                "salary_range": salary_range,
                "posted_at": posted_at,
            }
        )

    return jobs


# ── Built-in portal selector tests ──────────────────────────────────────


class TestLinkedInSelectors:
    """Validate LinkedIn selectors against linkedin_listing.html fixture."""

    def test_parses_two_job_cards(self) -> None:
        html = (FIXTURES_DIR / "linkedin_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, LINKEDIN_SELECTORS)
        assert len(jobs) == 2

    def test_extracts_title_and_company(self) -> None:
        html = (FIXTURES_DIR / "linkedin_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, LINKEDIN_SELECTORS)

        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[0]["company"] == "Acme Corp"
        assert jobs[1]["title"] == "Senior Backend Engineer"
        assert jobs[1]["company"] == "Tech Corp"

    def test_extracts_location_and_posted_date(self) -> None:
        html = (FIXTURES_DIR / "linkedin_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, LINKEDIN_SELECTORS)

        assert jobs[0]["location"] == "Buenos Aires, Argentina"
        assert jobs[0]["posted_at"] == "2026-06-18"
        assert jobs[1]["location"] == "Remote"
        assert jobs[1]["posted_at"] == "2026-06-15"

    def test_extracts_url_from_anchor(self) -> None:
        html = (FIXTURES_DIR / "linkedin_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, LINKEDIN_SELECTORS)

        assert jobs[0]["url"] == "/jobs/view/1"
        assert jobs[1]["url"] == "/jobs/view/2"

    def test_description_is_empty_string(self) -> None:
        """LinkedIn selectors deliberately omit description (None)."""
        html = (FIXTURES_DIR / "linkedin_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, LINKEDIN_SELECTORS)

        assert jobs[0]["description"] == ""


class TestInfojobsSelectors:
    """Validate Infojobs selectors against infojobs_listing.html fixture."""

    def test_parses_two_job_cards(self) -> None:
        html = (FIXTURES_DIR / "infojobs_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, INFOJOBS_SELECTORS)
        assert len(jobs) == 2

    def test_extracts_all_fields(self) -> None:
        html = (FIXTURES_DIR / "infojobs_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, INFOJOBS_SELECTORS)

        assert jobs[0]["title"] == "Backend Developer"
        assert jobs[0]["company"] == "Tech Co"
        assert jobs[0]["location"] == "Remote"
        assert jobs[0]["description"] == "We are looking for a skilled backend developer..."
        assert jobs[0]["salary_range"] == "$80,000 - $100,000"
        assert jobs[0]["posted_at"] == "2026-06-15"
        assert "/jobs/view/10" in jobs[0]["url"]

    def test_extracts_second_card_different_values(self) -> None:
        """Triangulation: different data on the second card."""
        html = (FIXTURES_DIR / "infojobs_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, INFOJOBS_SELECTORS)

        assert jobs[1]["title"] == "Frontend Engineer"
        assert jobs[1]["company"] == "Web Studio"
        assert jobs[1]["location"] == "Buenos Aires"


class TestComputrabajoSelectors:
    """Validate Computrabajo selectors against computrabajo_listing.html fixture."""

    def test_parses_two_job_cards(self) -> None:
        html = (FIXTURES_DIR / "computrabajo_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, COMPUTRABAJO_SELECTORS)
        assert len(jobs) == 2

    def test_extracts_all_fields(self) -> None:
        html = (FIXTURES_DIR / "computrabajo_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, COMPUTRABAJO_SELECTORS)

        assert jobs[0]["title"] == "Full Stack Developer"
        assert jobs[0]["company"] == "Startup XYZ"
        assert jobs[0]["location"] == "CABA"
        assert "building amazing products" in jobs[0]["description"]
        assert jobs[0]["posted_at"] == "1 week ago"
        assert "/empleos/123" in jobs[0]["url"]

    def test_salary_is_none_for_computrabajo(self) -> None:
        """Computrabajo selectors have salary=None, so field should be None."""
        html = (FIXTURES_DIR / "computrabajo_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, COMPUTRABAJO_SELECTORS)

        assert jobs[0]["salary_range"] is None


class TestBumeranSelectors:
    """Validate Bumeran selectors against bumeran_listing.html fixture."""

    def test_parses_two_job_cards(self) -> None:
        html = (FIXTURES_DIR / "bumeran_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, BUMERAN_SELECTORS)
        assert len(jobs) == 2

    def test_extracts_all_fields(self) -> None:
        html = (FIXTURES_DIR / "bumeran_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, BUMERAN_SELECTORS)

        assert jobs[0]["title"] == "Data Scientist"
        assert jobs[0]["company"] == "DataCorp"
        assert jobs[0]["location"] == "Bogotá"
        assert "machine learning" in jobs[0]["description"].lower()
        assert jobs[0]["salary_range"] == "$120,000"
        assert jobs[0]["posted_at"] == "3 days ago"

    def test_data_attribute_selectors(self) -> None:
        """Bumeran uses data-testid attributes; verify they match."""
        html = (FIXTURES_DIR / "bumeran_listing.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, BUMERAN_SELECTORS)

        assert jobs[0]["url"] == "/empleos/data-scientist-001"


# ── Error handling tests ────────────────────────────────────────────────


class TestErrorHandling:
    """Graceful handling of empty, malformed, or mismatched HTML."""

    def test_empty_html_returns_no_jobs(self) -> None:
        """A page with no body content should yield an empty result list."""
        html = (FIXTURES_DIR / "empty.html").read_text(encoding="utf-8")
        jobs = parse_jobs_from_html(html, LINKEDIN_SELECTORS)
        assert jobs == []

    def test_malformed_html_does_not_raise(self) -> None:
        """Broken HTML should be parsed gracefully by BeautifulSoup."""
        html = (FIXTURES_DIR / "malformed.html").read_text(encoding="utf-8")
        # Should not raise any exception
        jobs = parse_jobs_from_html(html, LINKEDIN_SELECTORS)
        assert isinstance(jobs, list)

    def test_nonexistent_selectors_return_empty_list(self) -> None:
        """Selectors that do not match any elements return no results."""
        selectors = LINKEDIN_SELECTORS.copy()
        selectors["job_card"] = ".does-not-exist"
        html = "<html><body><div>No jobs here</div></body></html>"
        jobs = parse_jobs_from_html(html, selectors)
        assert jobs == []

    def test_empty_selector_dict_handled_gracefully(self) -> None:
        """An empty/incomplete selectors dict should not crash."""
        html = "<html><body><div>Content</div></body></html>"
        jobs = parse_jobs_from_html(html, {})
        assert jobs == []

    def test_missing_required_fields_skips_card(self) -> None:
        """Cards without a title or company element are silently skipped."""
        html = """<html><body>
            <ul>
                <li class="card"><span class="title">Only Title</span></li>
                <li class="card"><span class="company">Only Company</span></li>
                <li class="card">
                    <span class="title">Both</span>
                    <span class="company">Present</span>
                </li>
            </ul>
        </body></html>"""
        selectors = {
            "job_card": "li.card",
            "title": ".title",
            "company": ".company",
            "location": None,
            "description": None,
            "url": None,
            "salary": None,
            "posted_date": None,
        }
        jobs = parse_jobs_from_html(html, selectors)
        # Only the card with both title and company should be parsed
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Both"
        assert jobs[0]["company"] == "Present"


# ── Fixture validation ──────────────────────────────────────────────────


class TestFixtureFiles:
    """Verify that all required fixture files exist and are loadable."""

    FIXTURE_NAMES = [
        "linkedin_listing.html",
        "infojobs_listing.html",
        "computrabajo_listing.html",
        "bumeran_listing.html",
        "empty.html",
        "malformed.html",
    ]

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_all_fixtures_exist(self, name: str) -> None:
        path = FIXTURES_DIR / name
        assert path.exists(), f"Missing fixture: {path}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 0, f"Empty fixture file: {path}"

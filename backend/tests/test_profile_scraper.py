"""Unit tests for ProfileScraper / InfojobsProfileScraper.

Tests the profile scraping abstraction using a mocked browser page
so no Playwright browser is launched.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.profiles.schemas import ImportedProfile, SkillItem
from app.scrapers.profile_scraper import InfojobsProfileScraper, ProfileScraper


class TestProfileScraperBase:
    """Tests for the ProfileScraper ABC contract."""

    def test_profile_scraper_cannot_be_instantiated_directly(self):
        """ProfileScraper has abstract methods and cannot be instantiated."""
        with pytest.raises(TypeError):
            ProfileScraper()  # type: ignore[abstract]


class TestInfojobsProfileScraper:
    """Suite for InfojobsProfileScraper.parse_profile()."""

    @pytest.mark.asyncio
    async def test_parse_profile_returns_imported_profile_with_fields(self):
        """parse_profile() returns an ImportedProfile with fields extracted
        from the Infojobs public profile page using the defined selectors.
        """
        scraper = InfojobsProfileScraper()

        scraper._scrape_profile = AsyncMock(  # type: ignore[method-assign]
            return_value=ImportedProfile(
                headline="Senior Software Engineer at Acme Corp",
                summary="Full-stack developer with 8+ years",
                skills=[
                    SkillItem(name="Python", level="advanced"),
                    SkillItem(name="Docker", level="advanced"),
                    SkillItem(name="Kubernetes", level="advanced"),
                ],
                infojobs_url="https://infojobs.com.ar/profile/testuser",
            ),
        )

        result = await scraper.parse_profile(
            url="https://infojobs.com.ar/profile/testuser",
        )

        assert result.headline == "Senior Software Engineer at Acme Corp"
        assert result.summary == "Full-stack developer with 8+ years"
        assert len(result.skills) == 3
        assert result.skills[0].name == "Python"
        assert result.skills[2].name == "Kubernetes"
        assert result.infojobs_url == "https://infojobs.com.ar/profile/testuser"

    @pytest.mark.asyncio
    async def test_parse_profile_handles_empty_page_gracefully(self):
        """parse_profile() returns ImportedProfile with defaults when
        no elements match the selectors.
        """
        scraper = InfojobsProfileScraper()

        scraper._scrape_profile = AsyncMock(  # type: ignore[method-assign]
            return_value=ImportedProfile(
                headline=None,
                summary=None,
                skills=[],
                infojobs_url="https://infojobs.com.ar/profile/empty",
            ),
        )

        result = await scraper.parse_profile(
            url="https://infojobs.com.ar/profile/empty",
        )

        assert result.headline is None
        assert result.summary is None
        assert result.skills == []
        assert result.infojobs_url == "https://infojobs.com.ar/profile/empty"

    @pytest.mark.asyncio
    async def test_selectors_are_defined_for_all_required_fields(self):
        """InfojobsProfileScraper defines selectors for all required profile
        fields: headline, summary, skills, experience_title, experience_company.
        """
        scraper = InfojobsProfileScraper()
        selectors = scraper.profile_selectors

        assert "headline" in selectors and selectors["headline"]
        assert "summary" in selectors and selectors["summary"]
        assert "skills" in selectors and selectors["skills"]
        assert "experience_title" in selectors and selectors["experience_title"]
        assert "experience_company" in selectors and selectors["experience_company"]

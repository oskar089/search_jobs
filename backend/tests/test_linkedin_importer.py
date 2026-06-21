"""Unit tests for LinkedInImporter.

Tests the URL validation, API response mapping, and error handling
using a mocked httpx client so no real API calls are made.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.profiles.linkedin_importer import LinkedInImporter


class TestLinkedInImporter:
    """Suite for LinkedInImporter import operations."""

    # ------------------------------------------------------------------
    # Successful import
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_import_returns_imported_profile_with_mapped_fields(self):
        """ImportProfile() returns an ImportedProfile with fields mapped from
        the Scrapin.io API response.

        Given a valid LinkedIn URL and a mock API response with headline,
        summary, skills, education, and experience, the importer MUST map
        all fields correctly to the ImportedProfile schema.
        """
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "person": {
                "headline": "Senior Software Engineer",
                "summary": "Experienced full-stack developer with 10+ years",
                "skills": ["Python", "Docker", "Kubernetes"],
                "education": [
                    {
                        "institution": "MIT",
                        "degree": "BS Computer Science",
                        "field": "Computer Science",
                        "start_date": "2015",
                        "end_date": "2019",
                    },
                ],
                "experiences": [
                    {
                        "company": "Google",
                        "title": "Software Engineer",
                        "location": "Mountain View",
                        "start_date": "2020-01",
                        "end_date": None,
                        "description": "Worked on search infrastructure",
                    },
                ],
            },
        }
        mock_client.get.return_value = mock_response

        importer = LinkedInImporter(api_key="test-key", client=mock_client)
        result = await importer.import_profile(
            url="https://linkedin.com/in/testuser",
        )

        assert result.headline == "Senior Software Engineer"
        assert result.summary == "Experienced full-stack developer with 10+ years"
        assert len(result.skills) == 3
        assert result.skills[0].name == "Python"
        assert result.skills[0].level == "advanced"  # mapped from present skill
        assert result.skills[1].name == "Docker"
        assert len(result.education) == 1
        assert result.education[0].institution == "MIT"
        assert result.education[0].degree == "BS Computer Science"
        assert len(result.work_experience) == 1
        assert result.work_experience[0].company == "Google"
        assert result.work_experience[0].role == "Software Engineer"
        assert result.linkedin_url == "https://linkedin.com/in/testuser"

    @pytest.mark.asyncio
    async def test_import_handles_missing_optional_fields(self):
        """ImportProfile() gracefully handles API responses with missing fields.

        When the API response is missing optional fields like skills,
        education, or headline, the importer MUST return an ImportedProfile
        with defaults (empty lists or None) instead of crashing.
        """
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "person": {
                "headline": None,
                "summary": None,
                "skills": None,
                "education": None,
                "experiences": None,
            },
        }
        mock_client.get.return_value = mock_response

        importer = LinkedInImporter(api_key="test-key", client=mock_client)
        result = await importer.import_profile(
            url="https://linkedin.com/in/empty",
        )

        assert result.headline is None
        assert result.summary is None
        assert result.skills == []
        assert result.education == []
        assert result.work_experience == []

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_import_raises_on_invalid_url(self):
        """ImportProfile() raises ValueError for non-LinkedIn URLs.

        Given a URL that does not contain 'linkedin.com', the importer
        MUST reject it with a descriptive error.
        """
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        importer = LinkedInImporter(api_key="test-key", client=mock_client)

        with pytest.raises(ValueError, match="Invalid LinkedIn URL"):
            await importer.import_profile(url="https://example.com/not-linkedin")

    @pytest.mark.asyncio
    async def test_import_raises_on_api_error(self):
        """ImportProfile() raises ValueError when the API returns an error.

        Given a LinkedIn URL that causes the Scrapin.io API to return a
        non-2xx status, the importer MUST raise an error with the status.
        """
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        mock_client.get.return_value = mock_response

        importer = LinkedInImporter(api_key="test-key", client=mock_client)

        with pytest.raises(ValueError, match="LinkedIn API error"):
            await importer.import_profile(url="https://linkedin.com/in/missing")

    @pytest.mark.asyncio
    async def test_import_raises_on_rate_limit(self):
        """ImportProfile() raises ValueError when rate limited.

        Given a LinkedIn URL that causes a 429 rate limit response,
        the importer MUST raise an error that mentions rate limiting.
        """
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )
        mock_client.get.return_value = mock_response

        importer = LinkedInImporter(api_key="test-key", client=mock_client)

        with pytest.raises(ValueError, match="rate limit"):
            await importer.import_profile(url="https://linkedin.com/in/rate-limited")

    @pytest.mark.asyncio
    async def test_import_raises_on_timeout(self):
        """ImportProfile() raises ValueError on timeout.

        Given a LinkedIn URL that causes an httpx timeout,
        the importer MUST raise an error mentioning the timeout.
        """
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.TimeoutException(
            "Request timed out after 30s",
        )

        importer = LinkedInImporter(api_key="test-key", client=mock_client)

        with pytest.raises(ValueError, match="timed out"):
            await importer.import_profile(url="https://linkedin.com/in/timeout")

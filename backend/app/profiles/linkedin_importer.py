"""LinkedIn profile importer via third-party API (Scrapin.io / ProxyCurl).

Wraps HTTP calls behind a ``LinkedInImporter`` class so the provider
can be swapped by changing the ``api_key`` and ``api_url``.  No OAuth
flow — API-key based per scope.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

import httpx

from app.profiles.schemas import (
    EducationItem,
    ExperienceItem,
    ImportedProfile,
    SkillItem,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default skill level mapping — skills from LinkedIn don't include levels,
# so we infer from common patterns or default to "advanced" for listed skills.
_DEFAULT_SKILL_LEVEL = "advanced"

# ---------------------------------------------------------------------------
# Abstract protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LinkedInImporterProtocol(Protocol):
    """Interface for LinkedIn profile importers.

    Implementations can wrap Scrapin.io, ProxyCurl, or any other
    LinkedIn data provider.
    """

    async def import_profile(self, url: str) -> ImportedProfile:
        """Fetch and map a LinkedIn profile to ``ImportedProfile``."""
        ...


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------


class LinkedInImporter:
    """Import LinkedIn profile data via the Scrapin.io API.

    Parameters
    ----------
    api_key:
        The API key for the third-party LinkedIn data provider.
    api_url:
        Base URL for the API (defaults to Scrapin.io).
    client:
        An optional ``httpx.AsyncClient`` instance.  If not provided,
        one will be created.
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.scrapin.io",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_url = api_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def import_profile(self, url: str) -> ImportedProfile:
        """Fetch and parse a LinkedIn profile.

        Parameters
        ----------
        url:
            A full LinkedIn profile URL
            (e.g. ``https://linkedin.com/in/username``).

        Returns
        -------
        ImportedProfile
            The mapped profile data.

        Raises
        ------
        ValueError
            If the URL is not a valid LinkedIn URL, the API returns an
            error, or the request times out.
        """
        self._validate_url(url)

        try:
            response = await self._client.get(
                f"{self._api_url}/enrich",
                params={"apiKey": self._api_key, "linkedInUrl": url},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise ValueError(
                    f"LinkedIn API rate limit exceeded. Try again later.",
                ) from exc
            raise ValueError(
                f"LinkedIn API error: HTTP {status}. Could not fetch profile.",
            ) from exc
        except httpx.TimeoutException as exc:
            raise ValueError(
                "LinkedIn API request timed out. Please try again.",
            ) from exc

        data = response.json()
        return self._map_response(data, url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_url(url: str) -> None:
        """Validate that the URL points to a LinkedIn profile."""
        if "linkedin.com" not in url:
            raise ValueError(
                f"Invalid LinkedIn URL: '{url}'. URL must contain 'linkedin.com'.",
            )

    @staticmethod
    def _map_response(data: dict, url: str) -> ImportedProfile:
        """Map a Scrapin.io API response to an ``ImportedProfile``.

        The Scrapin.io response format uses ``person`` as the root key:
        .. code-block:: json
            {
                "person": {
                    "headline": "...",
                    "summary": "...",
                    "skills": ["Python", ...],
                    "education": [{...}],
                    "experiences": [{...}]
                }
            }
        """
        person = data.get("person") or {}

        # --- Skills ---
        raw_skills: list = person.get("skills") or []
        skills = [
            SkillItem(name=s, level=_DEFAULT_SKILL_LEVEL)
            for s in raw_skills
            if s
        ]

        # --- Education ---
        raw_education: list = person.get("education") or []
        education = [
            EducationItem(
                institution=e.get("institution", ""),
                degree=e.get("degree", ""),
                field=e.get("field"),
                start_date=e.get("start_date", ""),
                end_date=e.get("end_date"),
            )
            for e in raw_education
            if e.get("institution")
        ]

        # --- Work experience ---
        raw_experience: list = person.get("experiences") or []
        work_experience = [
            ExperienceItem(
                company=e.get("company", ""),
                role=e.get("title", ""),
                location=e.get("location"),
                start_date=e.get("start_date", ""),
                end_date=e.get("end_date"),
                description=e.get("description"),
                current=e.get("current", False),
            )
            for e in raw_experience
            if e.get("company")
        ]

        return ImportedProfile(
            headline=person.get("headline"),
            summary=person.get("summary"),
            skills=skills,
            education=education,
            work_experience=work_experience,
            linkedin_url=url,
        )

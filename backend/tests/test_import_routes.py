"""Integration tests for profile import and CV management routes.

Covers:
  - POST /api/profiles/import/linkedin  (Task 3.1)
  - POST /api/profiles/import/infojobs  (Task 3.1)
  - POST /api/profiles/import/preview-save  (Task 3.3)
  - POST /api/profiles/cv/upload  (Task 3.5)
  - GET  /api/profiles/cv/download/{id}  (Task 3.5)
  - DELETE /api/profiles/cv/{id}  (Task 3.5)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models import CurriculumVitae, Profile
from app.profiles.schemas import (
    CVParseResult,
    EducationItem,
    ExperienceItem,
    ImportedProfile,
    SkillItem,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TINY_PDF = b"%PDF-1.4 fake pdf payload for testing"

_MOCK_IMPORTED_PROFILE = ImportedProfile(
    headline="Software Engineer at Acme",
    summary="Experienced Python developer with 8+ years",
    skills=[
        SkillItem(name="Python", level="advanced"),
        SkillItem(name="Docker", level="advanced"),
    ],
    education=[
        EducationItem(
            institution="University of Technology",
            degree="BSc Computer Science",
            start_date="2012",
        ),
    ],
    work_experience=[
        ExperienceItem(
            company="Acme Corp",
            role="Senior Engineer",
            start_date="2018",
            description="Built microservices",
            current=True,
        ),
    ],
    linkedin_url="https://linkedin.com/in/testuser",
)

_MOCK_CV_PARSE_RESULT = CVParseResult(
    id="cv-parse-id-123",
    file_name="resume.pdf",
    file_size=456,
    parsed_data=ImportedProfile(
        headline="CV Parsed Headline",
        summary="CV parsed summary",
        skills=[SkillItem(name="Python", level="advanced")],
    ),
)


# ===================================================================
# Task 3.1 — Import endpoints
# ===================================================================


class TestImportLinkedIn:
    """POST /api/profiles/import/linkedin"""

    async def test_import_linkedin_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Import from a valid LinkedIn URL returns ``ImportedProfile``."""
        with patch(
            "app.profiles.linkedin_importer.LinkedInImporter.import_profile",
            new=AsyncMock(return_value=_MOCK_IMPORTED_PROFILE),
        ):
            resp = await async_client.post(
                "/api/profiles/import/linkedin",
                json={"url": "https://linkedin.com/in/testuser"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["headline"] == "Software Engineer at Acme"
        assert body["summary"] == "Experienced Python developer with 8+ years"
        assert len(body["skills"]) == 2
        assert body["skills"][0]["name"] == "Python"
        assert body["skills"][0]["level"] == "advanced"
        assert len(body["education"]) == 1
        assert body["education"][0]["institution"] == "University of Technology"
        assert len(body["work_experience"]) == 1
        assert body["work_experience"][0]["company"] == "Acme Corp"
        assert body["linkedin_url"] == "https://linkedin.com/in/testuser"

    async def test_import_linkedin_invalid_url_returns_422(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Import with a URL that does not contain 'linkedin.com' returns 422."""
        with patch(
            "app.profiles.linkedin_importer.LinkedInImporter.import_profile",
            new=AsyncMock(
                side_effect=ValueError(
                    "Invalid LinkedIn URL: 'https://example.com'. "
                    "URL must contain 'linkedin.com'.",
                ),
            ),
        ):
            resp = await async_client.post(
                "/api/profiles/import/linkedin",
                json={"url": "https://example.com"},
                headers=auth_headers,
            )

        assert resp.status_code == 422
        assert "Invalid LinkedIn URL" in resp.json()["detail"]

    async def test_import_linkedin_api_error_returns_502(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Import when the LinkedIn API returns an HTTP error returns 502."""
        with patch(
            "app.profiles.linkedin_importer.LinkedInImporter.import_profile",
            new=AsyncMock(
                side_effect=ValueError(
                    "LinkedIn API error: HTTP 500. Could not fetch profile.",
                ),
            ),
        ):
            resp = await async_client.post(
                "/api/profiles/import/linkedin",
                json={"url": "https://linkedin.com/in/testuser"},
                headers=auth_headers,
            )

        assert resp.status_code == 502
        assert "API error" in resp.json()["detail"]

    async def test_import_linkedin_timeout_returns_504(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Import when the LinkedIn API times out returns 504."""
        with patch(
            "app.profiles.linkedin_importer.LinkedInImporter.import_profile",
            new=AsyncMock(
                side_effect=ValueError(
                    "LinkedIn API request timed out. Please try again.",
                ),
            ),
        ):
            resp = await async_client.post(
                "/api/profiles/import/linkedin",
                json={"url": "https://linkedin.com/in/testuser"},
                headers=auth_headers,
            )

        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"]

    async def test_import_linkedin_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Import without auth returns 401/422."""
        resp = await async_client.post(
            "/api/profiles/import/linkedin",
            json={"url": "https://linkedin.com/in/testuser"},
        )
        assert resp.status_code in (401, 403, 422)


class TestImportInfojobs:
    """POST /api/profiles/import/infojobs"""

    async def test_import_infojobs_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Import from a valid Infojobs URL returns ``ImportedProfile``."""
        with patch(
            "app.scrapers.profile_scraper.InfojobsProfileScraper.parse_profile",
            new=AsyncMock(return_value=_MOCK_IMPORTED_PROFILE),
        ):
            resp = await async_client.post(
                "/api/profiles/import/infojobs",
                json={"url": "https://infojobs.com.ar/profile/testuser"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["headline"] == "Software Engineer at Acme"
        assert len(body["skills"]) == 2
        assert body["skills"][1]["name"] == "Docker"

    async def test_import_infojobs_scraping_failure_returns_502(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Import when scraping fails returns 502."""
        with patch(
            "app.scrapers.profile_scraper.InfojobsProfileScraper.parse_profile",
            new=AsyncMock(side_effect=RuntimeError("Playwright error")),
        ):
            resp = await async_client.post(
                "/api/profiles/import/infojobs",
                json={"url": "https://infojobs.com.ar/profile/testuser"},
                headers=auth_headers,
            )

        assert resp.status_code == 502

    async def test_import_infojobs_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Import Infojobs without auth returns 401/422."""
        resp = await async_client.post(
            "/api/profiles/import/infojobs",
            json={"url": "https://infojobs.com.ar/profile/testuser"},
        )
        assert resp.status_code in (401, 403, 422)


# ===================================================================
# Task 3.3 — Preview-save endpoint
# ===================================================================


class TestImportPreviewSave:
    """POST /api/profiles/import/preview-save"""

    async def _create_profile(
        self,
        db_session,
        test_user,
        **overrides,
    ) -> Profile:
        """Helper to create a profile in the test database."""
        fields = {
            "user_id": test_user.id,
            "experience_level": "senior",
            "target_roles": ["backend"],
        }
        fields.update(overrides)
        profile = Profile(**fields)
        db_session.add(profile)
        await db_session.flush()
        return profile

    async def test_preview_save_merges_imported_data(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers: dict[str, str],
    ):
        """Preview-save fills empty fields with imported data."""
        await self._create_profile(db_session, test_user)

        imported = ImportedProfile(
            headline="Engineer at Acme",
            summary="Backend developer",
            skills=[SkillItem(name="Go", level="intermediate")],
            education=[EducationItem(
                institution="MIT", degree="BS", start_date="2010",
            )],
            linkedin_url="https://linkedin.com/in/testuser",
        )
        resp = await async_client.post(
            "/api/profiles/import/preview-save",
            json={"preview_data": imported.model_dump()},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["headline"] == "Engineer at Acme"
        assert body["summary"] == "Backend developer"
        assert len(body["skills"]) == 1
        assert body["skills"][0]["name"] == "Go"
        assert len(body["education"]) == 1
        assert body["linkedin_url"] == "https://linkedin.com/in/testuser"

    async def test_preview_save_no_overwrite_existing(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers: dict[str, str],
    ):
        """Preview-save does NOT overwrite populated fields."""
        await self._create_profile(
            db_session,
            test_user,
            headline="Existing Headline",
            summary="Existing summary",
            linkedin_url="https://linkedin.com/in/existing",
        )

        imported = ImportedProfile(
            headline="New Headline",
            summary="New summary",
            linkedin_url="https://linkedin.com/in/new",
        )
        resp = await async_client.post(
            "/api/profiles/import/preview-save",
            json={"preview_data": imported.model_dump()},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        # Existing fields must be preserved
        assert body["headline"] == "Existing Headline"
        assert body["summary"] == "Existing summary"
        assert body["linkedin_url"] == "https://linkedin.com/in/existing"

    async def test_preview_save_empty_preview_returns_profile(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers: dict[str, str],
    ):
        """Preview-save with empty preview_data still returns existing profile."""
        await self._create_profile(
            db_session,
            test_user,
            headline="My Headline",
        )

        # Empty imported profile — all fields are None or []
        resp = await async_client.post(
            "/api/profiles/import/preview-save",
            json={"preview_data": {}},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["headline"] == "My Headline"

    async def test_preview_save_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Preview-save without auth returns 401/422."""
        resp = await async_client.post(
            "/api/profiles/import/preview-save",
            json={"preview_data": {}},
        )
        assert resp.status_code in (401, 403, 422)


# ===================================================================
# Task 3.5 — CV upload / download / delete
# ===================================================================


class TestCVUpload:
    """POST /api/profiles/cv/upload"""

    async def test_upload_cv_success(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers: dict[str, str],
    ):
        """Upload a valid PDF returns CVParseResult with metadata + parsed data."""
        # Create a profile first so the route can update cv_file_url
        profile = Profile(user_id=test_user.id, experience_level="mid")
        db_session.add(profile)
        await db_session.flush()

        with (
            patch(
                "app.profiles.cv_parser.CVParser.parse_cv",
                new=AsyncMock(return_value=_MOCK_CV_PARSE_RESULT),
            ),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            # Override the upload dir via the settings used by the router
            with patch("app.config.settings.upload_dir", tmpdir):
                resp = await async_client.post(
                    "/api/profiles/cv/upload",
                    files={"file": ("resume.pdf", _TINY_PDF, "application/pdf")},
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert body["file_name"] == "resume.pdf"
        assert body["file_size"] == len(_TINY_PDF)
        assert body["parsed_data"]["headline"] == "CV Parsed Headline"
        assert len(body["parsed_data"]["skills"]) == 1
        assert body["parsed_data"]["skills"][0]["name"] == "Python"

    async def test_upload_cv_non_pdf_rejected(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Upload a non-PDF file returns 422."""
        resp = await async_client.post(
            "/api/profiles/cv/upload",
            files={"file": ("resume.txt", b"not a pdf", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "PDF" in resp.json()["detail"]

    async def test_upload_cv_too_large(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Upload a PDF larger than 10MB returns 422."""
        large_content = b"x" * (10 * 1024 * 1024 + 1)
        resp = await async_client.post(
            "/api/profiles/cv/upload",
            files={"file": ("large.pdf", large_content, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "large" in resp.json()["detail"].lower()

    async def test_upload_cv_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """Upload CV without auth returns 401/422."""
        resp = await async_client.post(
            "/api/profiles/cv/upload",
            files={"file": ("test.pdf", _TINY_PDF, "application/pdf")},
        )
        assert resp.status_code in (401, 403, 422)


class TestCVDownload:
    """GET /api/profiles/cv/download/{cv_id}"""

    async def test_download_cv_success(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers: dict[str, str],
    ):
        """Download an existing CV returns the PDF file."""
        # Pre-populate CV record + file
        with tempfile.TemporaryDirectory() as tmpdir:
            cv_id = "00000000-0000-0000-0000-000000000001"
            file_path = Path(tmpdir) / f"{cv_id}.pdf"
            file_path.write_bytes(_TINY_PDF)

            cv = CurriculumVitae(
                id=cv_id,
                user_id=test_user.id,
                filename="test.pdf",
                file_path=str(file_path),
                file_size=len(_TINY_PDF),
            )
            db_session.add(cv)
            await db_session.flush()

            with patch("app.config.settings.upload_dir", tmpdir):
                resp = await async_client.get(
                    f"/api/profiles/cv/download/{cv_id}",
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content == _TINY_PDF

    async def test_download_cv_not_found_returns_404(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Download a non-existent CV returns 404."""
        resp = await async_client.get(
            "/api/profiles/cv/download/nonexistent-id",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestCVDelete:
    """DELETE /api/profiles/cv/{cv_id}"""

    async def test_delete_cv_success(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers: dict[str, str],
    ):
        """Delete an existing CV returns 204 and removes the record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cv_id = "00000000-0000-0000-0000-000000000002"
            file_path = Path(tmpdir) / f"{cv_id}.pdf"
            file_path.write_bytes(_TINY_PDF)

            cv = CurriculumVitae(
                id=cv_id,
                user_id=test_user.id,
                filename="delete-me.pdf",
                file_path=str(file_path),
                file_size=len(_TINY_PDF),
            )
            db_session.add(cv)
            await db_session.flush()

            with patch("app.config.settings.upload_dir", tmpdir):
                resp = await async_client.delete(
                    f"/api/profiles/cv/{cv_id}",
                    headers=auth_headers,
                )

        assert resp.status_code == 204

        # Verify DB record is gone
        from sqlalchemy import select
        result = await db_session.execute(
            select(CurriculumVitae).where(CurriculumVitae.id == cv_id),
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_cv_not_found_returns_404(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Delete a non-existent CV returns 404."""
        resp = await async_client.delete(
            "/api/profiles/cv/nonexistent-id",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestCVFullCycle:
    """Full upload → download → delete cycle."""

    async def test_upload_download_delete_cycle(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers: dict[str, str],
    ):
        """Full CV lifecycle: upload, download, then delete."""
        # Create a profile first
        profile = Profile(user_id=test_user.id, experience_level="senior")
        db_session.add(profile)
        await db_session.flush()

        with (
            patch(
                "app.profiles.cv_parser.CVParser.parse_cv",
                new=AsyncMock(return_value=_MOCK_CV_PARSE_RESULT),
            ),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            with patch("app.config.settings.upload_dir", tmpdir):
                # 1. Upload
                resp = await async_client.post(
                    "/api/profiles/cv/upload",
                    files={"file": ("resume.pdf", _TINY_PDF, "application/pdf")},
                    headers=auth_headers,
                )
                assert resp.status_code == 200
                body = resp.json()
                cv_id = body["id"]
                assert cv_id is not None

                # 2. Download
                resp = await async_client.get(
                    f"/api/profiles/cv/download/{cv_id}",
                    headers=auth_headers,
                )
                assert resp.status_code == 200
                assert resp.headers["content-type"] == "application/pdf"
                assert resp.content == _TINY_PDF

                # 3. Delete
                resp = await async_client.delete(
                    f"/api/profiles/cv/{cv_id}",
                    headers=auth_headers,
                )
                assert resp.status_code == 204

                # 4. Download after delete returns 404
                resp = await async_client.get(
                    f"/api/profiles/cv/download/{cv_id}",
                    headers=auth_headers,
                )
                assert resp.status_code == 404

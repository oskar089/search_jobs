"""Unit tests for MergeService.merge() strategy.

Validates the fill-empty merge behavior:
  - Scalar fields: fill when existing is None, never overwrite populated fields
  - List fields: append items not already present (dedup by key), preserve existing
  - Edge cases: empty lists, missing keys, partial import data
"""

from __future__ import annotations

import pytest

from app.profiles.merge_service import MergeService
from app.profiles.schemas import (
    EducationItem,
    ExperienceItem,
    ImportedProfile,
    SkillItem,
)


class TestMergeService:
    """Suite for MergeService.merge() strategy."""

    # ------------------------------------------------------------------
    # Scalar fields: fill-empty + no-overwrite
    # ------------------------------------------------------------------

    def test_fill_empty_scalar_fields(self):
        """Existing None fields are filled with imported values.

        When the existing profile has None for headline, summary, and
        linkedin_url, and the imported data has those fields populated,
        MergeService MUST return them in the merged result.
        """
        existing = {
            "headline": None,
            "summary": None,
            "linkedin_url": None,
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": [],
            "education": [],
            "work_experience": [],
        }
        imported = ImportedProfile(
            headline="Software Engineer",
            summary="Experienced full-stack developer",
            linkedin_url="https://linkedin.com/in/test",
        )

        result = MergeService.merge(existing, imported)

        assert result["headline"] == "Software Engineer"
        assert result["summary"] == "Experienced full-stack developer"
        assert result["linkedin_url"] == "https://linkedin.com/in/test"

    def test_no_overwrite_existing_scalar(self):
        """Existing non-None scalar fields are never overwritten.

        When the existing profile already has 'headline' populated and
        the imported data provides a different value, MergeService MUST
        preserve the existing value.
        """
        existing = {
            "headline": "Existing Engineer",
            "summary": "Existing summary",
            "linkedin_url": "https://linkedin.com/in/existing",
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": [],
            "education": [],
            "work_experience": [],
        }
        imported = ImportedProfile(
            headline="New Headline",
            summary="New summary",
            linkedin_url="https://linkedin.com/in/new",
            infojobs_url="https://infojobs.com/in/new",
        )

        result = MergeService.merge(existing, imported)

        # Existing non-None values are preserved
        assert result["headline"] == "Existing Engineer"
        assert result["summary"] == "Existing summary"
        assert result["linkedin_url"] == "https://linkedin.com/in/existing"
        # None field IS filled
        assert result["infojobs_url"] == "https://infojobs.com/in/new"

    def test_partial_import_does_not_clear_existing(self):
        """Importing only some fields leaves other existing fields intact.

        When the imported data only has a subset of fields, the existing
        values for the other fields MUST remain unchanged in the result.
        """
        existing = {
            "headline": "Engineer",
            "summary": None,
            "linkedin_url": None,
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": [],
            "education": [],
            "work_experience": [],
        }
        imported = ImportedProfile(
            summary="Just updating my summary",
        )

        result = MergeService.merge(existing, imported)

        # Existing populated field is preserved
        assert result["headline"] == "Engineer"
        # Empty field is filled
        assert result["summary"] == "Just updating my summary"
        # Other empty fields remain None (not set, no value to fill with)
        assert result.get("linkedin_url") is None

    # ------------------------------------------------------------------
    # List fields: append-new + dedup
    # ------------------------------------------------------------------

    def test_append_new_skills(self):
        """New skills from import are appended to existing skills list.

        When the existing profile has skills and the imported data
        contains additional skills, MergeService MUST include all
        existing plus the new ones, deduplicated by name.
        """
        existing = {
            "headline": None,
            "summary": None,
            "linkedin_url": None,
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": [{"name": "Python", "level": "advanced"}],
            "education": [],
            "work_experience": [],
        }
        imported = ImportedProfile(
            skills=[
                SkillItem(name="Python", level="advanced"),
                SkillItem(name="Docker", level="intermediate"),
                SkillItem(name="Kubernetes", level="beginner"),
            ],
        )

        result = MergeService.merge(existing, imported)

        # Python was already there (dedup)
        assert len(result["skills"]) == 3
        skill_names = {s["name"] for s in result["skills"]}
        assert "Python" in skill_names
        assert "Docker" in skill_names
        assert "Kubernetes" in skill_names

    def test_dedup_education_by_institution_and_degree(self):
        """Education entries are deduplicated by institution+degree combo.

        When the imported education list contains an entry that matches
        an existing entry by both institution and degree, it MUST NOT
        be added again.
        """
        existing = {
            "headline": None,
            "summary": None,
            "linkedin_url": None,
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": [],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "BS Computer Science",
                    "field": "Computer Science",
                    "start_date": "2015-09-01",
                    "end_date": "2019-06-01",
                    "description": None,
                },
            ],
            "work_experience": [],
        }
        imported = ImportedProfile(
            education=[
                EducationItem(
                    institution="MIT",
                    degree="BS Computer Science",
                    field="Computer Science",
                    start_date="2015-09-01",
                    end_date="2019-06-01",
                ),
                EducationItem(
                    institution="Stanford",
                    degree="MS AI",
                    field="Artificial Intelligence",
                    start_date="2020-09-01",
                    end_date="2022-06-01",
                ),
            ],
        )

        result = MergeService.merge(existing, imported)

        # MIT should appear once, Stanford should be appended
        assert len(result["education"]) == 2
        institutions = {e["institution"] for e in result["education"]}
        assert "MIT" in institutions
        assert "Stanford" in institutions

    def test_dedup_work_experience_by_company_and_role(self):
        """Work experiences are deduplicated by company+role combo.

        When the imported experience matches an existing entry by both
        company and role, it MUST NOT be duplicated.
        """
        existing = {
            "headline": None,
            "summary": None,
            "linkedin_url": None,
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": [],
            "education": [],
            "work_experience": [
                {
                    "company": "Google",
                    "role": "Software Engineer",
                    "start_date": "2020-01-01",
                    "end_date": None,
                    "description": "Worked on search",
                    "current": True,
                },
            ],
        }
        imported = ImportedProfile(
            work_experience=[
                ExperienceItem(
                    company="Google",
                    role="Software Engineer",
                    start_date="2020-01-01",
                    end_date=None,
                    description="Worked on search",
                    current=True,
                ),
                ExperienceItem(
                    company="AWS",
                    role="DevOps Engineer",
                    start_date="2018-01-01",
                    end_date="2019-12-01",
                    description="Cloud infra",
                    current=False,
                ),
            ],
        )

        result = MergeService.merge(existing, imported)

        # Google appears once, AWS is new
        assert len(result["work_experience"]) == 2
        companies = {e["company"] for e in result["work_experience"]}
        assert "Google" in companies
        assert "AWS" in companies

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_import_changes_nothing(self):
        """Importing an empty profile returns the existing values unchanged.

        When the imported data is completely empty, MergeService MUST
        return the existing values as-is (not overwrite anything).
        """
        existing = {
            "headline": "Engineer",
            "summary": "Summary",
            "linkedin_url": "https://linkedin.com/in/existing",
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": [{"name": "Python", "level": "advanced"}],
            "education": [],
            "work_experience": [],
        }
        imported = ImportedProfile()

        result = MergeService.merge(existing, imported)

        assert result["headline"] == "Engineer"
        assert result["summary"] == "Summary"
        assert result["linkedin_url"] == "https://linkedin.com/in/existing"
        assert result["skills"] == [{"name": "Python", "level": "advanced"}]

    def test_merge_with_existing_none_lists(self):
        """Existing lists that are None are treated as empty for merge.

        When the existing profile has None for skills/education/
        work_experience (e.g., from a freshly migrated profile),
        MergeService MUST treat them as empty and fill from import.
        """
        existing = {
            "headline": None,
            "summary": None,
            "linkedin_url": None,
            "infojobs_url": None,
            "cv_file_url": None,
            "skills": None,
            "education": None,
            "work_experience": None,
        }
        imported = ImportedProfile(
            skills=[SkillItem(name="Python", level="advanced")],
            education=[
                EducationItem(
                    institution="MIT",
                    degree="BS CS",
                    field="CS",
                    start_date="2015-01-01",
                ),
            ],
        )

        result = MergeService.merge(existing, imported)

        assert len(result["skills"]) == 1
        assert result["skills"][0]["name"] == "Python"
        assert len(result["education"]) == 1
        assert result["education"][0]["institution"] == "MIT"

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of scoring a job posting against a user profile."""

    score: float = 0.0  # 0–100
    factors: dict = field(default_factory=dict)  # per-factor breakdown


class MatcherEngine:
    """Scoring engine that matches job postings against user profiles.

    Scores are computed from four weighted factors:
      - Role match (35%): how well the job title matches target roles
      - Tech stack match (30%): keyword overlap in job description
      - Location match (20%): city proximity and remote preference
      - Experience match (15%): seniority level alignment
    """

    WEIGHTS: dict[str, float] = {
        "role_match": 0.35,
        "tech_match": 0.30,
        "location_match": 0.20,
        "experience_match": 0.15,
    }

    def score(self, profile: dict, job: dict) -> MatchResult:
        """Compute a 0–100 match score.

        Returns a score of 0 immediately when the profile has no target
        roles or tech stack defined (per spec — no auto-apply without criteria).
        Uses headline, summary, skills, and work experience descriptions
        to enrich matching when provided via CV import.
        """
        target_roles = profile.get("target_roles") or []
        tech_stack = profile.get("tech_stack") or []

        if not target_roles or not tech_stack:
            logger.info("Profile has no target roles or tech stack — score = 0")
            return MatchResult(
                score=0.0,
                factors={"reason": "No target roles or tech stack defined"},
            )

        job_title = job.get("title", "")
        job_description = job.get("description", "")

        role_match = self._score_role_match(
            target_roles,
            job_title,
            headline=profile.get("headline", ""),
            summary=profile.get("summary", ""),
        )
        tech_match = self._score_tech_match(
            tech_stack,
            job_description,
            skills=profile.get("skills") or [],
        )
        location_match = self._score_location(profile, job.get("location"))
        experience_match = self._score_experience(
            profile.get("experience_level", ""),
            job_description,
            work_experience=profile.get("work_experience") or [],
        )

        raw_score = (
            role_match * self.WEIGHTS["role_match"]
            + tech_match * self.WEIGHTS["tech_match"]
            + location_match * self.WEIGHTS["location_match"]
            + experience_match * self.WEIGHTS["experience_match"]
        )

        score = round(min(max(raw_score * 100, 0.0), 100.0), 1)

        return MatchResult(
            score=score,
            factors={
                "role_match": round(role_match, 3),
                "tech_match": round(tech_match, 3),
                "location_match": round(location_match, 3),
                "experience_match": round(experience_match, 3),
            },
        )

    def _score_role_match(
        self,
        target_roles: list[str],
        job_title: str,
        headline: str = "",
        summary: str = "",
    ) -> float:
        """Score 0–1 based on title overlap with target roles + headline/summary.

        If the job title doesn't directly match a target role, checks whether
        the profile's headline or summary (e.g. "Full Stack Developer") aligns
        with the job title as a fallback.
        """
        if not job_title:
            return 0.0
        title_lower = job_title.lower()

        # Direct role match
        for role in target_roles:
            role_lower = role.lower()
            if role_lower in title_lower or title_lower in role_lower:
                return 1.0
            role_tokens = set(role_lower.split())
            title_tokens = set(title_lower.split())
            if role_tokens & title_tokens:
                return 0.5

        # Fallback: check headline/summary against job title
        profile_text = f"{headline} {summary}".lower()
        if profile_text:
            profile_tokens = set(profile_text.split())
            title_tokens = set(title_lower.split())
            if profile_tokens & title_tokens:
                return 0.3

        return 0.0

    def _score_tech_match(
        self,
        tech_stack: list[str],
        description: str,
        skills: list | None = None,
    ) -> float:
        """Score 0–1 as ratio of tech keywords (+ CV skills) found in description."""
        all_tech = list(tech_stack)
        if skills:
            # Flatten skills: could be strings or {name, level} objects
            for s in skills:
                if isinstance(s, dict):
                    name = s.get("name", "")
                    if name:
                        all_tech.append(name)
                elif isinstance(s, str):
                    all_tech.append(s)

        if not all_tech or not description:
            return 0.0
        desc_lower = description.lower()
        matched = sum(1 for tech in all_tech if tech.lower() in desc_lower)
        return min(matched / len(all_tech), 1.0)

    def _score_location(self, profile: dict, job_location: str | None) -> float:
        """Score 0–1 based on location compatibility."""
        if not job_location:
            return 0.5
        if profile.get("remote_only", False):
            return 1.0
        preferred = profile.get("locations") or []
        if not preferred:
            return 0.5
        loc_lower = job_location.lower()
        for pref in preferred:
            if pref.lower() in loc_lower or loc_lower in pref.lower():
                return 1.0
        return 0.0

    def _score_experience(
        self,
        experience_level: str,
        description: str,
        work_experience: list | None = None,
    ) -> float:
        """Score 0–1 based on seniority alignment + work history.

        Uses the user's experience level and optionally checks work
        experience descriptions for seniority keywords.
        """
        if not experience_level:
            return 0.5

        levels = {"junior": 1, "mid": 2, "senior": 3, "lead": 4}
        user_lvl = levels.get(experience_level.lower(), 0)
        if user_lvl == 0:
            return 0.5

        # Build a combined text from the job description + work history
        combined = (description or "").lower()
        if work_experience:
            for exp in work_experience:
                if isinstance(exp, dict):
                    desc = exp.get("description", "") or ""
                    role = exp.get("role", "") or ""
                    combined += f" {desc} {role}".lower()

        for lvl_name, lvl_val in levels.items():
            if lvl_name in combined:
                diff = abs(user_lvl - lvl_val)
                if diff == 0:
                    return 1.0
                if diff == 1:
                    return 0.5
                return 0.0
        return 0.5

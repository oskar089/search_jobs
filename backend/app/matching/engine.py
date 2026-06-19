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
        """
        target_roles = profile.get("target_roles") or []
        tech_stack = profile.get("tech_stack") or []

        if not target_roles or not tech_stack:
            logger.info("Profile has no target roles or tech stack — score = 0")
            return MatchResult(
                score=0.0,
                factors={"reason": "No target roles or tech stack defined"},
            )

        role_match = self._score_role_match(target_roles, job.get("title", ""))
        tech_match = self._score_tech_match(tech_stack, job.get("description", ""))
        location_match = self._score_location(profile, job.get("location"))
        experience_match = self._score_experience(
            profile.get("experience_level", ""),
            job.get("description", ""),
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

    def _score_role_match(self, target_roles: list[str], job_title: str) -> float:
        """Score 0–1 based on title overlap with target roles."""
        if not job_title:
            return 0.0
        title_lower = job_title.lower()
        for role in target_roles:
            role_lower = role.lower()
            if role_lower in title_lower or title_lower in role_lower:
                return 1.0
            role_tokens = set(role_lower.split())
            title_tokens = set(title_lower.split())
            if role_tokens & title_tokens:
                return 0.5
        return 0.0

    def _score_tech_match(self, tech_stack: list[str], description: str) -> float:
        """Score 0–1 as ratio of tech keywords found in description."""
        if not tech_stack or not description:
            return 0.0
        desc_lower = description.lower()
        matched = sum(1 for tech in tech_stack if tech.lower() in desc_lower)
        return matched / len(tech_stack)

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

    def _score_experience(self, experience_level: str, description: str) -> float:
        """Score 0–1 based on seniority alignment."""
        if not experience_level or not description:
            return 0.5
        levels = {"junior": 1, "mid": 2, "senior": 3, "lead": 4}
        user_lvl = levels.get(experience_level.lower(), 0)
        if user_lvl == 0:
            return 0.5
        desc_lower = description.lower()
        for lvl_name, lvl_val in levels.items():
            if lvl_name in desc_lower:
                diff = abs(user_lvl - lvl_val)
                if diff == 0:
                    return 1.0
                if diff == 1:
                    return 0.5
                return 0.0
        return 0.5

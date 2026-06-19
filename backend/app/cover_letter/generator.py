import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CoverLetterInput:
    """Input data for generating a cover letter."""

    job_title: str
    company: str
    job_description: str
    profile: dict = field(default_factory=dict)
    language: str = "en"


class CoverLetterGenerator:
    """Generates formal cover letters via an LLM API with in-memory caching.

    - Detects job posting language and writes in the same language.
    - Retries ONCE on failure (5 s delay).
    - Caches per user+posting to avoid duplicate API costs.
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    async def generate(
        self,
        input_data: CoverLetterInput,
        user_id: str,
        job_id: str,
    ) -> str:
        """Return a cover letter, using cache if available."""
        cache_key = f"{user_id}:{job_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("Cover letter cache hit for %s", cache_key)
            return cached

        prompt = self._build_prompt(input_data)
        letter = await self._call_llm(prompt, input_data.language)
        self._cache[cache_key] = letter
        return letter

    def _build_prompt(self, data: CoverLetterInput) -> str:
        tech_stack = ", ".join(data.profile.get("tech_stack") or [])
        target_roles = ", ".join(data.profile.get("target_roles") or [])
        experience = data.profile.get("experience_level", "professional")

        return (
            f"You are a professional cover letter writer. Write a formal, "
            f"professional cover letter for a job application. "
            f"Do NOT use slang, casual phrases, or humor.\n\n"
            f"Job Title: {data.job_title}\n"
            f"Company: {data.company}\n"
            f"Job Description:\n{data.job_description}\n\n"
            f"Applicant Profile:\n"
            f"- Target Roles: {target_roles}\n"
            f"- Tech Stack: {tech_stack}\n"
            f"- Experience Level: {experience}\n\n"
            f"Write the entire cover letter in {data.language}. "
            f"Use formal business letter format. "
            f"Sign off with 'Sincerely' and leave the name blank."
        )

    async def _call_llm(self, prompt: str, language: str) -> str:
        """Call the OpenAI-compatible LLM endpoint; retry once on failure."""
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        settings.llm_api_url,
                        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                        json={
                            "model": settings.llm_model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": (
                                        "You are a professional cover letter writer. "
                                        "Always write in formal, professional tone. "
                                        f"The response MUST be in {language}."
                                    ),
                                },
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.7,
                            "max_tokens": 512,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()

            except Exception as exc:
                last_error = exc
                logger.warning("LLM API attempt %d/2 failed: %s", attempt + 1, exc)
                if attempt == 0:
                    await asyncio.sleep(5)

        raise RuntimeError(
            f"Cover letter generation failed after 2 attempts: {last_error}",
        )

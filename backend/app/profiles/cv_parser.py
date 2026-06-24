"""CV PDF parser — text extraction plus LLM-powered structured parsing.

Uses ``pdfplumber`` for text extraction and any OpenAI-compatible LLM
(Ollama, OpenAI, etc.) to extract structured profile fields from the
raw text.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from openai import AsyncOpenAI

from app.config import settings
from app.profiles.schemas import CVParseResult, ImportedProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# System prompt for structured extraction (works with any LLM).
_EXTRACTION_PROMPT = """You are a CV/resume parser. Extract structured data from the
following CV text and return a JSON object with these fields:
- headline (str or null): The professional headline / current title
- summary (str or null): Professional summary or objective
- skills (list of {{"name": str, "level": str}}): Technical and professional skills.
  Level must be one of: beginner, intermediate, advanced, expert.
- education (list of {{"institution": str, "degree": str, "field": str or null,
  "start_date": str or null, "end_date": str or null}}): Educational entries.
- work_experience (list of {{"company": str, "role": str, "start_date": str or null,
  "end_date": str or null, "description": str or null, "current": bool}}):
  Work experience entries.

Return ONLY valid JSON, no markdown formatting, no explanation, no code blocks."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CVParser:
    """Parse CV PDF files into structured profile data.

    Two-step process:
    1. ``extract_text()`` — extract raw text via ``pdfplumber``.
    2. ``parse_cv()`` — send text to the configured LLM for structured extraction.

    The LLM client is lazily initialised so that ``extract_text()``
    can be called without an API key configured.
    """

    def __init__(self, openai_client: AsyncOpenAI | None = None) -> None:
        self._client = openai_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text(self, file_path: str) -> str:
        """Extract all text from a PDF file using ``pdfplumber``.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the PDF file.

        Returns
        -------
        str
            The concatenated text of all pages.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If the PDF is empty or has no extractable text.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        import pdfplumber

        try:
            with pdfplumber.open(file_path) as pdf:
                pages_text = [page.extract_text() for page in pdf.pages]
        except Exception as exc:
            raise ValueError(f"Could not extract text from PDF: {exc}") from exc

        text = "\n".join(filter(None, pages_text)).strip()

        if not text:
            raise ValueError(
                "Could not extract text from PDF: no extractable content found.",
            )

        return text

    async def parse_cv(self, file_path: str) -> CVParseResult:
        """Extract text from a PDF and parse it via the configured LLM.

        Parameters
        ----------
        file_path:
            Path to the PDF file.

        Returns
        -------
        CVParseResult
            Metadata about the file plus the structured parsed data.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If the PDF is empty, has no extractable text, or LLM
            parsing fails.
        """
        text = self.extract_text(file_path)
        if not text:
            raise ValueError("No extractable text found in PDF.")

        path = Path(file_path)
        parsed = await self._parse_with_llm(text)

        return CVParseResult(
            id=str(uuid.uuid4()),
            file_name=path.name,
            file_size=path.stat().st_size,
            parsed_data=parsed,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _parse_with_llm(self, text: str) -> ImportedProfile:
        """Send extracted text to the configured LLM and parse the structured response.

        Falls back gracefully if ``response_format`` is not supported by the
        backend (e.g. some Ollama models).
        """
        client = self._get_client()

        kwargs: dict = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": _EXTRACTION_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
        }

        # Some Ollama models don't support response_format — try with it,
        # fall back without if it fails.
        use_response_format = True
        for attempt in range(2):
            try:
                if use_response_format:
                    kwargs["response_format"] = {"type": "json_object"}
                completion = await client.chat.completions.create(**kwargs)
                raw = completion.choices[0].message.content
                if not raw:
                    raise ValueError("Empty response from LLM")
                data = json.loads(raw)
                return ImportedProfile(**data)
            except (json.JSONDecodeError, Exception) as exc:
                if attempt == 0 and use_response_format:
                    logger.info(
                        "LLM CV parsing with response_format failed (%s), "
                        "retrying without it",
                        exc,
                    )
                    use_response_format = False
                    kwargs.pop("response_format", None)
                    # Strengthen the prompt to force JSON-only output
                    kwargs["messages"][0]["content"] = (
                        _EXTRACTION_PROMPT
                        + "\n\nCRITICAL: Respond with raw JSON only. "
                        "No markdown, no code fences, no explanation."
                    )
                    continue
                logger.exception("LLM CV parsing failed after retry")
                raise ValueError(
                    f"Failed to parse CV with LLM ({settings.llm_model}): {exc}",
                ) from exc

        raise ValueError("Unexpected: LLM parsing loop exited without return")

    def _get_client(self) -> AsyncOpenAI:
        """Return the LLM client, creating it lazily if needed."""
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=settings.llm_api_url,
                api_key=settings.llm_api_key,
            )
        return self._client

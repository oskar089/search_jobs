"""CV PDF parser — text extraction plus OpenAI-powered structured parsing.

Uses ``pdfplumber`` for text extraction and the OpenAI chat completions
API with function calling to extract structured profile fields from the
raw text.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from openai import AsyncOpenAI

from app.profiles.schemas import CVParseResult, ImportedProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# System prompt for the OpenAI structured extraction.
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

Return ONLY valid JSON, no markdown formatting, no explanation."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CVParser:
    """Parse CV PDF files into structured profile data.

    Two-step process:
    1. ``extract_text()`` — extract raw text via ``pdfplumber``.
    2. ``parse_cv()`` — send text to OpenAI for structured extraction.

    The OpenAI client is lazily initialised so that ``extract_text()``
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
        """Extract text from a PDF and parse it via OpenAI.

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
            If the PDF is empty, has no extractable text, or OpenAI
            parsing fails.
        """
        text = self.extract_text(file_path)
        if not text:
            raise ValueError("No extractable text found in PDF.")

        path = Path(file_path)
        parsed = await self._parse_with_openai(text)

        return CVParseResult(
            id=str(uuid.uuid4()),
            file_name=path.name,
            file_size=path.stat().st_size,
            parsed_data=parsed,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _parse_with_openai(self, text: str) -> ImportedProfile:
        """Send extracted text to OpenAI and parse the structured response."""
        client = self._get_client()
        try:
            completion = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": _EXTRACTION_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
        except Exception as exc:
            logger.exception("OpenAI CV parsing failed")
            raise ValueError(
                f"Failed to parse CV with OpenAI: {exc}",
            ) from exc

        raw = completion.choices[0].message.content
        if not raw:
            raise ValueError(
                "OpenAI returned empty response during CV parsing.",
            )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to decode OpenAI response: {exc}",
            ) from exc

        return ImportedProfile(**data)

    def _get_client(self) -> AsyncOpenAI:
        """Return the OpenAI client, creating it lazily if needed."""
        if self._client is None:
            self._client = AsyncOpenAI()
        return self._client

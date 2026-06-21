"""Unit tests for CVParser.

Tests text extraction via pdfplumber and structured parsing via
OpenAI function calling.  The OpenAI client is mocked so no API
calls are made during tests.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.profiles.cv_parser import CVParser
from app.profiles.schemas import CVParseResult

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestCVParserExtractText:
    """Tests for CVParser.extract_text()."""

    def test_extract_text_returns_string_from_valid_pdf(self):
        """extract_text() returns the text content of a valid PDF.

        Given a path to a valid PDF with known content, the method
        MUST return a non-empty string containing the extracted text.
        """
        pdf_path = str(FIXTURES_DIR / "sample_cv.pdf")
        parser = CVParser()

        text = parser.extract_text(pdf_path)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "Senior Software Engineer" in text
        assert "Python" in text

    def test_extract_text_raises_on_nonexistent_file(self):
        """extract_text() raises FileNotFoundError for a missing file."""
        parser = CVParser()

        with pytest.raises(FileNotFoundError):
            parser.extract_text("/path/to/nonexistent/file.pdf")

    def test_extract_text_raises_on_empty_pdf(self):
        """extract_text() raises ValueError for an empty/invalid PDF."""
        # Create an empty file that looks like a PDF
        empty_path = str(FIXTURES_DIR / "empty.pdf")
        try:
            Path(empty_path).write_text("%PDF-1.4\n%%EOF")
            parser = CVParser()

            with pytest.raises(ValueError, match="Could not extract text"):
                parser.extract_text(empty_path)
        finally:
            Path(empty_path).unlink(missing_ok=True)


class TestCVParserParseCV:
    """Tests for CVParser.parse_cv()."""

    @pytest.mark.asyncio
    async def test_parse_cv_returns_cv_parse_result(self):
        """parse_cv() returns a CVParseResult with parsed fields.

        Given a valid PDF path and a mocked OpenAI response with
        structured data, the method MUST return a CVParseResult
        containing the parsed fields.
        """
        pdf_path = str(FIXTURES_DIR / "sample_cv.pdf")
        parser = CVParser()

        # Mock the OpenAI client
        mock_openai = MagicMock()
        mock_message = MagicMock()
        mock_message.content = (
            '{"headline": "Senior Software Engineer", '
            '"summary": "Full-stack developer", '
            '"skills": [{"name": "Python", "level": "advanced"}], '
            '"education": [{"institution": "MIT", "degree": "BS CS", '
            '"start_date": "2015", "end_date": "2019"}], '
            '"work_experience": [{"company": "Google", "role": "SWE", '
            '"start_date": "2020", "description": "Built stuff"}]}'
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_completion)

        parser._client = mock_openai

        result = await parser.parse_cv(pdf_path)

        assert isinstance(result, CVParseResult)
        assert result.file_name == "sample_cv.pdf"
        assert result.file_size > 0
        assert result.parsed_data.headline == "Senior Software Engineer"
        assert result.parsed_data.summary == "Full-stack developer"
        assert len(result.parsed_data.skills) == 1
        assert result.parsed_data.skills[0].name == "Python"
        assert len(result.parsed_data.education) == 1
        assert result.parsed_data.education[0].institution == "MIT"
        assert result.id is not None and len(str(result.id)) > 0

    @pytest.mark.asyncio
    async def test_parse_cv_handles_openai_error(self):
        """parse_cv() raises ValueError when OpenAI returns an error."""
        pdf_path = str(FIXTURES_DIR / "sample_cv.pdf")
        parser = CVParser()

        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI API error"),
        )
        parser._client = mock_openai

        with pytest.raises(ValueError, match="Failed to parse CV"):
            await parser.parse_cv(pdf_path)

    @pytest.mark.asyncio
    async def test_parse_cv_handles_empty_pdf(self):
        """parse_cv() raises ValueError when the PDF has no extractable text."""
        # Create a minimal valid but empty PDF
        empty_path = str(FIXTURES_DIR / "empty_content.pdf")
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            # Just add whitespace
            pdf.cell(text=" ")
            pdf.output(empty_path)

            parser = CVParser()
            with pytest.raises(ValueError, match="no extractable content"):
                await parser.parse_cv(empty_path)
        finally:
            Path(empty_path).unlink(missing_ok=True)

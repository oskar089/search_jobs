"""Unit tests for FileStorageService.

Tests save, serve, and delete operations using a temporary directory.
The service is abstracted behind a protocol so we verify the contract.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile

from app.profiles.file_storage import FileStorageService


class TestFileStorageService:
    """Suite for FileStorageService save/serve/delete operations."""

    @pytest.mark.asyncio
    async def test_save_returns_cv_response_with_metadata(self):
        """save() returns a CVResponse with id, filename, file_size, user_id.

        When a file is saved, the response must contain non-empty metadata
        derived from the uploaded file and profile context.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "resume.pdf"
            mock_file.read = AsyncMock(return_value=b"%PDF-1.4 sample content")

            result = await service.save(mock_file, profile_id="user-abc")

            assert result.id is not None and len(result.id) > 0
            assert result.filename == "resume.pdf"
            assert result.file_size == len(b"%PDF-1.4 sample content")
            assert result.user_id == "user-abc"

    @pytest.mark.asyncio
    async def test_save_writes_file_to_disk(self):
        """save() writes the file content to the upload directory.

        After saving, the file must exist on disk at the expected path
        with the correct content.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            content = b"%PDF-1.4 some binary data here"
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "cv.pdf"
            mock_file.read = AsyncMock(return_value=content)

            result = await service.save(mock_file, profile_id="user-xyz")

            # File should exist on disk
            saved_path = Path(tmpdir) / f"{result.id}.pdf"
            assert saved_path.exists()
            assert saved_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_serve_returns_file_response_with_correct_media_type(self):
        """serve() returns a FileResponse with application/pdf media type.

        When a stored CV is requested by id, the response must stream the PDF
        with the correct content type.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            content = b"%PDF-1.4 serve test"
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "serve.pdf"
            mock_file.read = AsyncMock(return_value=content)

            saved = await service.save(mock_file, profile_id="user-serve")

            response = service.serve(saved.id)

            assert response.media_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_serve_raises_on_nonexistent_cv(self):
        """serve() raises FileNotFoundError when the CV id does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            with pytest.raises(FileNotFoundError, match="CV not found"):
                service.serve("nonexistent-id")

    @pytest.mark.asyncio
    async def test_delete_removes_file_and_returns_none(self):
        """delete() removes the file from disk and returns None.

        After deletion, the file must no longer exist on disk.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            content = b"%PDF-1.4 delete test"
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "delete.pdf"
            mock_file.read = AsyncMock(return_value=content)

            saved = await service.save(mock_file, profile_id="user-del")

            # File exists before deletion
            saved_path = Path(tmpdir) / f"{saved.id}.pdf"
            assert saved_path.exists()

            result = service.delete(saved.id)

            assert result is None
            assert not saved_path.exists()

    @pytest.mark.asyncio
    async def test_delete_raises_on_nonexistent_cv(self):
        """delete() raises FileNotFoundError when the CV id does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            with pytest.raises(FileNotFoundError, match="CV not found"):
                service.delete("nonexistent-id")

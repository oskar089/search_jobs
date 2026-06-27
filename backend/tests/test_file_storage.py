"""Unit tests for FileStorageService and validate_file helper.

Tests save, serve, and delete operations using a temporary directory.
The service is abstracted behind a protocol so we verify the contract.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from app.profiles.file_storage import FileStorageService, validate_file


class TestValidateFile:
    """validate_file() must validate PDFs by extension, content-type, and magic bytes."""

    @pytest.mark.asyncio
    async def test_valid_pdf_passes(self):
        """Valid PDF with .pdf ext, application/pdf content-type, and %PDF magic bytes passes."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "resume.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 sample content")

        # Should not raise
        await validate_file(mock_file)

        # Verify read was called
        mock_file.read.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_wrong_extension(self):
        """File with .exe extension is rejected even if content-type is PDF."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "resume.exe"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 sample")

        with pytest.raises(HTTPException) as exc:
            await validate_file(mock_file)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_wrong_content_type(self):
        """File with non-PDF content-type is rejected even if extension is .pdf."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "resume.pdf"
        mock_file.content_type = "text/html"
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 sample")

        with pytest.raises(HTTPException) as exc:
            await validate_file(mock_file)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_wrong_magic_bytes(self):
        """File with .pdf extension and PDF content-type but wrong magic bytes is rejected."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "fake.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"PK\x03\x04 not a pdf")

        with pytest.raises(HTTPException) as exc:
            await validate_file(mock_file)
        assert exc.value.status_code == 422


class TestPathTraversal:
    """serve() and delete() must validate UUID format to prevent path traversal.

    The guard must reject path traversal even when the resolved file EXISTS
    outside the upload directory. This proves the UUID check runs BEFORE
    path resolution.
    """

    @pytest.mark.asyncio
    async def test_serve_rejects_non_uuid(self):
        """serve() rejects non-UUID cv_id with FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            with pytest.raises(FileNotFoundError, match="CV not found"):
                service.serve("not-a-uuid-at-all")

    @pytest.mark.asyncio
    async def test_serve_rejects_path_traversal_even_when_file_exists(self):
        """serve() rejects path traversal even if the resolved file exists outside upload dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file OUTSIDE the upload directory
            outside_file = Path(tmpdir) / "outside.pdf"
            outside_file.write_bytes(b"%PDF-outside-content")

            # Upload dir is a subdirectory
            upload_dir = Path(tmpdir) / "uploads"
            upload_dir.mkdir()

            service = FileStorageService(upload_dir=str(upload_dir))

            # cv_id="../outside" would resolve to outside.pdf which EXISTS
            # BUT UUID validation must reject it before path resolution
            with pytest.raises(FileNotFoundError):
                service.serve("../outside")

    @pytest.mark.asyncio
    async def test_delete_rejects_non_uuid(self):
        """delete() rejects non-UUID cv_id with FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(upload_dir=tmpdir)
            with pytest.raises(FileNotFoundError, match="CV not found"):
                service.delete("not-a-uuid")


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

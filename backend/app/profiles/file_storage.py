"""File storage service for CV PDF uploads.

Provides local-filesystem storage with a protocol that can be swapped
for S3-compatible storage later.  The public methods are ``save()``,
``serve()``, and ``delete()``.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

from fastapi import UploadFile
from fastapi.responses import FileResponse

from app.profiles.schemas import CVResponse


# ---------------------------------------------------------------------------
# Abstract protocol (swap-friendly for S3)
# ---------------------------------------------------------------------------


@runtime_checkable
class FileStorage(Protocol):
    """Interface for file storage backends.

    Implementing this protocol allows swapping local filesystem storage
    for S3, GCS, or any other backend without changing the consumer.
    """

    async def save(self, file: UploadFile, profile_id: str) -> CVResponse:
        """Persist an uploaded file and return metadata."""
        ...

    def serve(self, cv_id: str) -> FileResponse:
        """Return a ``FileResponse`` streaming the stored file."""
        ...

    def delete(self, cv_id: str) -> None:
        """Remove the stored file from the backend.

        Raises ``FileNotFoundError`` if the CV id does not exist.
        """
        ...


# ---------------------------------------------------------------------------
# Local filesystem implementation
# ---------------------------------------------------------------------------


class FileStorageService:
    """Local filesystem implementation of ``FileStorage``.

    Files are stored as ``{upload_dir}/{cv_id}.pdf``.  Metadata is
    returned as a ``CVResponse`` but is **not persisted to a database**
    by this service — the caller is responsible for creating/updating
    ``CurriculumVitae`` rows.
    """

    def __init__(self, upload_dir: str = "uploads/cv") -> None:
        self._upload_dir = Path(upload_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save(self, file: UploadFile, profile_id: str) -> CVResponse:
        """Save the uploaded file to the local filesystem.

        Parameters
        ----------
        file:
            The uploaded PDF file (must support ``.read()`` and
            have a ``.filename`` attribute).
        profile_id:
            The owning user/profile ID (stored in the response).

        Returns
        -------
        CVResponse
            Metadata describing the stored file.
        """
        cv_id = str(uuid.uuid4())
        content = await file.read()
        dest = self._upload_dir / f"{cv_id}.pdf"
        dest.write_bytes(content)

        return CVResponse(
            id=cv_id,
            user_id=profile_id,
            filename=file.filename or "untitled.pdf",
            file_size=len(content),
        )

    def serve(self, cv_id: str) -> FileResponse:
        """Stream the stored file back to the client.

        Parameters
        ----------
        cv_id:
            The UUID of the stored CV file.

        Returns
        -------
        FileResponse
            A FastAPI streaming response with ``application/pdf``
            media type.

        Raises
        ------
        FileNotFoundError
            If no file exists for ``cv_id``.
        """
        path = self._resolve(cv_id)
        return FileResponse(
            path=str(path),
            media_type="application/pdf",
            filename=path.name,
        )

    def delete(self, cv_id: str) -> None:
        """Remove the stored file from disk.

        Parameters
        ----------
        cv_id:
            The UUID of the stored CV file.

        Raises
        ------
        FileNotFoundError
            If no file exists for ``cv_id``.
        """
        path = self._resolve(cv_id)
        path.unlink()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, cv_id: str) -> Path:
        """Resolve a CV id to a filesystem path, raising if missing."""
        path = self._upload_dir / f"{cv_id}.pdf"
        if not path.exists():
            raise FileNotFoundError(f"CV not found: {cv_id}")
        return path

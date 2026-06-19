import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Application(Base):
    __tablename__ = "application"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    stored_job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    pipeline_run_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cover_letter_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cover_letter_text: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")  # type: ignore[name-defined]  # noqa: F821
    stored_job: Mapped["StoredJob"] = relationship("StoredJob", back_populates="applications")  # type: ignore[name-defined]  # noqa: F821
    pipeline_run: Mapped["PipelineRun | None"] = relationship("PipelineRun", back_populates="applications")  # type: ignore[name-defined]  # noqa: F821
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="application")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Application {self.id} status={self.status}>"

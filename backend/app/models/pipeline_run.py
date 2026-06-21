import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_run"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("user.id"), nullable=False)
    portal_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("portal.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, scraping, matching, applying, notifying, completed, failed
    trigger: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    steps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="pipeline_runs")  # type: ignore[name-defined]  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        "Application", back_populates="pipeline_run"
    )  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<PipelineRun {self.id} status={self.status}>"

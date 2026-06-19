import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StoredJob(Base):
    """Stores scraped job postings."""

    __tablename__ = "stored_job"
    __table_args__ = (
        UniqueConstraint("portal_id", "external_id", name="uq_portal_external_job"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portal_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    salary_range: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Relationships
    portal: Mapped["Portal"] = relationship("Portal", back_populates="stored_jobs")  # type: ignore[name-defined]  # noqa: F821
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="stored_job")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<StoredJob {self.title} @ {self.company}>"

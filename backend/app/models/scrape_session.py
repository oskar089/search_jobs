import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScrapeSession(Base):
    __tablename__ = "scrape_session"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    portal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("portal.id"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("user.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(50), nullable=False)  # running, completed, failed
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    portal: Mapped["Portal"] = relationship("Portal", back_populates="scrape_sessions")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<ScrapeSession {self.id} status={self.status}>"

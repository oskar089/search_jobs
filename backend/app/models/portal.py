import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Portal(Base):
    __tablename__ = "portal"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("user.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    job_listing_url: Mapped[str] = mapped_column(String(500), nullable=False)
    selectors: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scrape_interval_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="portals")  # type: ignore[name-defined]  # noqa: F821
    stored_jobs: Mapped[list["StoredJob"]] = relationship("StoredJob", back_populates="portal")  # type: ignore[name-defined]  # noqa: F821
    scrape_sessions: Mapped[list["ScrapeSession"]] = relationship(  # noqa: F821
        "ScrapeSession", back_populates="portal"
    )  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Portal {self.name}>"

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("user.id"), nullable=False)
    application_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("application.id"), nullable=True
    )

    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # application_submitted, application_failed, portal_error, match_found
    channel: Mapped[str] = mapped_column(
        String(20), default="in_app", nullable=False
    )  # in_app, email, both
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")  # type: ignore[name-defined]  # noqa: F821
    application: Mapped["Application | None"] = relationship(  # noqa: F821
        "Application", back_populates="notifications"
    )  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Notification {self.title} is_read={self.is_read}>"

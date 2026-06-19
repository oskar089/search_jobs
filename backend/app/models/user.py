import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    profile: Mapped["Profile | None"] = relationship("Profile", back_populates="user", uselist=False)  # type: ignore[name-defined]  # noqa: F821
    portals: Mapped[list["Portal"]] = relationship("Portal", back_populates="user")  # type: ignore[name-defined]  # noqa: F821
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="user")  # type: ignore[name-defined]  # noqa: F821
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")  # type: ignore[name-defined]  # noqa: F821
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship("PipelineRun", back_populates="user")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<User {self.email}>"

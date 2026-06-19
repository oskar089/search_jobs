import asyncio
import logging
import uuid
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Dispatch notifications through in-app storage and email.

    Email uses SMTP via *aiosmtplib* with automatic retry (3 attempts,
    exponential backoff). In-app notifications create DB rows in the
    ``notification`` table.
    """

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    async def create_in_app(
        self,
        user_id: str,
        type: str,  # noqa: A002
        title: str,
        body: str,
        application_id: str | None = None,
    ) -> str:
        """Persist an in-app notification row and return its ID."""
        from app.models import Notification

        async with self.session_factory() as session:
            notif = Notification(
                id=str(uuid.uuid4()),
                user_id=user_id,
                application_id=application_id,
                type=type,
                channel="in_app",
                title=title,
                body=body,
            )
            session.add(notif)
            await session.commit()
            logger.info("In-app notification %s created for user %s", notif.id, user_id)
            return str(notif.id)

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email via SMTP with up to 3 retries.

        Returns ``True`` if sent successfully, ``False`` otherwise.
        """
        if not settings.smtp_host:
            logger.warning("SMTP not configured — skipping email to %s", to)
            return False

        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with aiosmtplib.SMTP(
                    hostname=settings.smtp_host,
                    port=settings.smtp_port,
                    timeout=30,
                ) as smtp:
                    if settings.smtp_user and settings.smtp_password:
                        await smtp.login(settings.smtp_user, settings.smtp_password)
                    await smtp.send_message(msg)
                    logger.info("Email sent to %s (attempt %d/3)", to, attempt + 1)
                    return True
            except Exception as exc:
                last_error = exc
                logger.warning("SMTP attempt %d/3 failed for %s: %s", attempt + 1, to, exc)
                if attempt < 2:
                    await asyncio.sleep((attempt + 1) * 2)  # 2 s, 4 s

        logger.error("All SMTP retries exhausted for %s: %s", to, last_error)
        return False

    async def notify_application_submitted(
        self,
        application_id: str,
        user_id: str,
        user_email: str,
        job_title: str,
        company: str,
    ) -> None:
        """Send in-app + email notification for a successful submission."""
        title = f"Application Submitted"
        body = f"Your application for {job_title} at {company} has been submitted."

        await self.create_in_app(
            user_id=user_id,
            type="application_submitted",
            title=title,
            body=body,
            application_id=application_id,
        )
        await self.send_email(
            to=user_email,
            subject=f"Application Submitted — {job_title} @ {company}",
            body=body,
        )

    async def notify_application_failed(
        self,
        application_id: str,
        user_id: str,
        user_email: str,
        job_title: str,
        company: str,
        error: str,
    ) -> None:
        """Send in-app + email notification for a failed submission."""
        title = f"Application Failed"
        body = f"Your application for {job_title} at {company} failed: {error}"

        await self.create_in_app(
            user_id=user_id,
            type="application_failed",
            title=title,
            body=body,
            application_id=application_id,
        )
        await self.send_email(
            to=user_email,
            subject=f"Application Failed — {job_title} @ {company}",
            body=body,
        )

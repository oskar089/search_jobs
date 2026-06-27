"""Tests for the notification service — SMTP STARTTLS enforcement and connectivity check."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.notifications.service import NotificationService


@pytest.fixture
def service() -> NotificationService:
    """Return a NotificationService with a mock session factory."""
    return NotificationService(session_factory=MagicMock())


# ---------------------------------------------------------------------------
# send_email — STARTTLS enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_email_calls_starttls(service: NotificationService) -> None:
    """GIVEN SMTP is configured WHEN send_email connects THEN it calls starttls()."""
    mock_smtp = AsyncMock()
    mock_smtp.__aenter__.return_value = mock_smtp

    with (
        patch("app.notifications.service.settings") as mock_settings,
        patch("aiosmtplib.SMTP", return_value=mock_smtp),
    ):
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        mock_settings.smtp_from = "noreply@test.app"

        result = await service.send_email(to="test@example.com", subject="Test", body="Hello")

    assert result is True
    mock_smtp.starttls.assert_awaited_once()
    mock_smtp.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_email_with_auth_calls_login(service: NotificationService) -> None:
    """GIVEN SMTP credentials are provided WHEN send_email runs THEN it calls login after STARTTLS."""
    mock_smtp = AsyncMock()
    mock_smtp.__aenter__.return_value = mock_smtp

    with (
        patch("app.notifications.service.settings") as mock_settings,
        patch("aiosmtplib.SMTP", return_value=mock_smtp),
    ):
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_password = "secret"
        mock_settings.smtp_from = "noreply@test.app"

        result = await service.send_email(to="other@example.com", subject="Hi", body="World")

    assert result is True
    mock_smtp.starttls.assert_awaited_once()
    # login must be called after starttls, before send_message
    mock_smtp.login.assert_awaited_once_with("user@example.com", "secret")
    mock_smtp.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_email_skipped_when_smtp_not_configured(service: NotificationService) -> None:
    """GIVEN SMTP host is empty WHEN send_email runs THEN it skips sends and returns False."""
    with patch("app.notifications.service.settings") as mock_settings:
        mock_settings.smtp_host = ""

        result = await service.send_email(to="test@example.com", subject="Test", body="Hello")

    assert result is False


@pytest.mark.asyncio
async def test_send_email_starttls_failure_returns_false(
    service: NotificationService,
) -> None:
    """GIVEN SMTP server rejects STARTTLS WHEN send_email runs THEN it returns False."""
    mock_smtp = AsyncMock()
    mock_smtp.__aenter__.return_value = mock_smtp
    mock_smtp.starttls.side_effect = Exception("STARTTLS not supported")

    with (
        patch("app.notifications.service.settings") as mock_settings,
        patch("aiosmtplib.SMTP", return_value=mock_smtp),
    ):
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        mock_settings.smtp_from = "noreply@test.app"

        result = await service.send_email(to="test@example.com", subject="Test", body="Hello")

    assert result is False
    # starttls is called on each of the 3 retry attempts
    assert mock_smtp.starttls.awaited
    assert mock_smtp.send_message.await_count == 0


@pytest.mark.asyncio
async def test_send_email_login_failure_returns_false(service: NotificationService) -> None:
    """GIVEN SMTP auth fails WHEN send_email runs THEN it returns False after retries."""
    mock_smtp = AsyncMock()
    mock_smtp.__aenter__.return_value = mock_smtp
    mock_smtp.login.side_effect = Exception("Authentication failed")

    with (
        patch("app.notifications.service.settings") as mock_settings,
        patch("aiosmtplib.SMTP", return_value=mock_smtp),
    ):
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_password = "wrong"
        mock_settings.smtp_from = "noreply@test.app"

        result = await service.send_email(to="test@example.com", subject="Test", body="Hello")

    assert result is False
    mock_smtp.starttls.assert_awaited()
    assert mock_smtp.send_message.await_count == 0


# ---------------------------------------------------------------------------
# check_smtp_connectivity — startup connectivity check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_smtp_connectivity_success(service: NotificationService) -> None:
    """GIVEN SMTP is reachable WHEN check_smtp_connectivity runs THEN it returns True."""
    mock_smtp = AsyncMock()
    mock_smtp.__aenter__.return_value = mock_smtp

    with (
        patch("app.notifications.service.settings") as mock_settings,
        patch("aiosmtplib.SMTP", return_value=mock_smtp),
    ):
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""

        result = await service.check_smtp_connectivity()

    assert result is True
    mock_smtp.starttls.assert_awaited_once()
    mock_smtp.quit.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_smtp_connectivity_with_different_port(service: NotificationService) -> None:
    """GIVEN SMTP uses a non-default port WHEN check_smtp_connectivity runs THEN it connects on that port."""
    mock_smtp = AsyncMock()
    mock_smtp.__aenter__.return_value = mock_smtp

    with (
        patch("app.notifications.service.settings") as mock_settings,
        patch("aiosmtplib.SMTP") as mock_smtp_class,
    ):
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 465
        mock_settings.smtp_user = ""

        mock_smtp_class.return_value = mock_smtp

        result = await service.check_smtp_connectivity()

    assert result is True
    mock_smtp_class.assert_called_once_with(hostname="smtp.example.com", port=465, timeout=10)


@pytest.mark.asyncio
async def test_check_smtp_connectivity_failure_logs_warning(
    service: NotificationService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GIVEN SMTP is unreachable WHEN check_smtp_connectivity runs THEN it logs warning and returns False."""
    with (
        patch("app.notifications.service.settings") as mock_settings,
        patch("aiosmtplib.SMTP", side_effect=Exception("Connection refused")),
    ):
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""

        with caplog.at_level(logging.WARNING):
            result = await service.check_smtp_connectivity()

    assert result is False
    assert any("SMTP server unreachable" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_check_smtp_connectivity_skipped_when_not_configured(
    service: NotificationService,
) -> None:
    """GIVEN SMTP host is empty WHEN check_smtp_connectivity runs THEN it skips and returns None."""
    with patch("app.notifications.service.settings") as mock_settings:
        mock_settings.smtp_host = ""

        result = await service.check_smtp_connectivity()

    assert result is None

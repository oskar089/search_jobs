"""Tests for main.py startup validation hook (Phase 1).

Verifies that settings.validate_startup() is called on startup
and that missing non-critical configs produce warning logs.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestStartupValidation:
    """Startup validation hook in main.py."""

    def test_run_startup_validation_exists(self):
        """run_startup_validation function is importable from app.main."""
        from app.main import run_startup_validation

        assert callable(run_startup_validation)

    def test_log_non_critical_warnings_exists(self):
        """log_non_critical_warnings function is importable from app.main."""
        from app.main import log_non_critical_warnings

        assert callable(log_non_critical_warnings)

    def test_startup_handler_calls_validate_startup(self):
        """run_startup_validation invokes settings.validate_startup()."""
        from app.main import run_startup_validation

        # Patch at the class level to avoid pydantic's strict __setattr__
        with patch("app.config.Settings.validate_startup") as mock_validate:
            run_startup_validation()
            mock_validate.assert_called_once()

    def test_startup_logs_warning_for_missing_llm_key(self):
        """Missing LLM_API_KEY logs a warning."""
        from app.config import settings
        from app.main import log_non_critical_warnings

        original_llm_key = settings.llm_api_key
        try:
            settings.llm_api_key = ""
            with patch("app.main.logger") as mock_logger:
                log_non_critical_warnings()
                mock_logger.warning.assert_any_call(
                    "LLM_API_KEY is not set \u2014 LLM features will be unavailable"
                )
        finally:
            settings.llm_api_key = original_llm_key

    def test_startup_logs_warning_for_missing_smtp_host(self):
        """Missing SMTP_HOST logs a warning."""
        from app.config import settings
        from app.main import log_non_critical_warnings

        original_smtp_host = settings.smtp_host
        try:
            settings.smtp_host = ""
            with patch("app.main.logger") as mock_logger:
                log_non_critical_warnings()
                mock_logger.warning.assert_any_call(
                    "SMTP_HOST is not set \u2014 email notifications will be unavailable"
                )
        finally:
            settings.smtp_host = original_smtp_host

    def test_startup_does_not_warn_when_keys_are_set(self):
        """No warnings when LLM_API_KEY and SMTP_HOST are set."""
        from app.config import settings
        from app.main import log_non_critical_warnings

        original_llm_key = settings.llm_api_key
        original_smtp_host = settings.smtp_host
        try:
            settings.llm_api_key = "some-key"
            settings.smtp_host = "smtp.example.com"
            with patch("app.main.logger") as mock_logger:
                log_non_critical_warnings()
            warning_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if "LLM_API_KEY" in str(c) or "SMTP_HOST" in str(c)
            ]
            assert len(warning_calls) == 0
        finally:
            settings.llm_api_key = original_llm_key
            settings.smtp_host = original_smtp_host

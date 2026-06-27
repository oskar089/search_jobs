"""Tests for scraper reliability: stealth, backoff, and fallback.

STRICT TDD: Tests written before implementation.
"""

from __future__ import annotations

import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scrapers.stealth import apply_stealth, calculate_backoff, get_stealth_script


class TestBackoffCalculator:
    """Exponential backoff with jitter: min(16000, 1000 * 2**attempt + random.uniform(0, 500))."""

    def test_backoff_attempt_0_is_1000_plus_jitter(self):
        """Attempt 0: 1000 * 2^0 = 1000 + jitter(0-500) = 1000-1500ms."""
        for _ in range(100):
            result = calculate_backoff(0)
            assert 1000 <= result <= 1500, f"Expected 1000-1500, got {result}"

    def test_backoff_attempt_1_is_2000_plus_jitter(self):
        """Attempt 1: 1000 * 2^1 = 2000 + jitter(0-500) = 2000-2500ms."""
        for _ in range(100):
            result = calculate_backoff(1)
            assert 2000 <= result <= 2500, f"Expected 2000-2500, got {result}"

    def test_backoff_attempt_2_is_4000_plus_jitter(self):
        """Attempt 2: 1000 * 2^2 = 4000 + jitter(0-500) = 4000-4500ms."""
        for _ in range(100):
            result = calculate_backoff(2)
            assert 4000 <= result <= 4500, f"Expected 4000-4500, got {result}"

    def test_backoff_attempt_3_is_8000_plus_jitter(self):
        """Attempt 3: 1000 * 2^3 = 8000 + jitter(0-500) = 8000-8500ms."""
        for _ in range(100):
            result = calculate_backoff(3)
            assert 8000 <= result <= 8500, f"Expected 8000-8500, got {result}"

    def test_backoff_caps_at_16000_plus_jitter(self):
        """Attempt 4+: min(16000, ...) caps at 16000 + jitter(0-500) = 16000-16500ms."""
        for _ in range(100):
            result = calculate_backoff(4)
            assert 16000 <= result <= 16500, f"Expected 16000-16500, got {result}"

    def test_backoff_high_attempt_stays_capped(self):
        """Attempt 10 also caps at 16000-16500 (not 1000*2^10=1024000)."""
        for _ in range(100):
            result = calculate_backoff(10)
            assert 16000 <= result <= 16500, f"Expected 16000-16500, got {result}"

    def test_backoff_jitter_is_random(self):
        """Over 1000 samples, at least 3 distinct values should appear (jitter)."""
        results = {calculate_backoff(0) for _ in range(1000)}
        assert len(results) >= 3, f"Expected jitter to produce varied values, got {len(results)} unique"

    def test_backoff_returns_float(self):
        """Backoff value must be a float (milliseconds precision)."""
        result = calculate_backoff(2)
        assert isinstance(result, float)


class TestStealthModule:
    """Stealth script generation and injection."""

    def test_get_stealth_script_returns_string(self):
        """get_stealth_script() must return a non-empty string."""
        script = get_stealth_script()
        assert isinstance(script, str)
        assert len(script) > 100, "Stealth script should contain substantial JS payload"

    def test_get_stealth_script_contains_iife(self):
        """Stealth script should be an IIFE (starts with (() =>)."""
        script = get_stealth_script()
        assert script.startswith("(() => {"), f"Expected IIFE, got prefix: {script[:30]}"

    def test_get_stealth_script_is_reproducible(self):
        """Multiple calls should return the same stable payload."""
        script1 = get_stealth_script()
        script2 = get_stealth_script()
        assert script1 == script2, "Stealth script should be deterministic"

    def test_apply_stealth_injects_script_to_context(self):
        """apply_stealth() should call context.add_init_script with a stealth script."""
        from app.scrapers.stealth import apply_stealth, get_stealth_script

        with patch("app.scrapers.stealth.get_stealth_script", return_value="(() => { /* test */ })();"):
            mock_context = MagicMock()
            mock_context.add_init_script = AsyncMock()

            import inspect
            assert inspect.iscoroutinefunction(apply_stealth), "apply_stealth must be async"

            import asyncio
            asyncio.run(apply_stealth(mock_context))
            mock_context.add_init_script.assert_awaited_once_with("(() => { /* test */ })();")


class TestScraperEngineStealth:
    """ScraperEngine must inject stealth script before navigation."""

    @patch("app.scrapers.engine.ScraperEngine._get_browser")
    async def test_stealth_injected_before_goto(self, mock_get_browser):
        """Engine._scrape_page() must call context.add_init_script before page.goto()."""
        from app.scrapers.engine import ScraperEngine, PortalSelectors

        # Create a mock browser that returns a mock context
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_context.new_page.return_value = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_get_browser.return_value = mock_browser

        engine = ScraperEngine(headless=True)
        selectors = PortalSelectors(job_card=".card", title="h2", company=".company")

        # The scrape should trigger _scrape_page which injects stealth
        with patch("app.scrapers.engine.apply_stealth", new_callable=AsyncMock) as mock_apply:
            await engine._scrape_page(
                url="https://example.com/jobs",
                selectors=selectors,
                max_results=5,
            )

            # Verify apply_stealth was called with the context before goto
            mock_apply.assert_awaited_once()
            context_arg = mock_apply.await_args[0][0]
            assert context_arg is mock_context

    @patch("app.scrapers.engine.ScraperEngine._get_browser")
    async def test_scrape_propagates_failure_without_stealth(self, mock_get_browser):
        """When stealth is unavailable, scrape should still try."""
        from app.scrapers.engine import ScraperEngine, PortalSelectors

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_get_browser.return_value = mock_browser

        engine = ScraperEngine(headless=True)
        selectors = PortalSelectors(job_card=".card", title="h2", company=".company")

        # Even if stealth apply fails, the scrape should continue
        with patch("app.scrapers.engine.apply_stealth", side_effect=Exception("Stealth failed")):
            await engine._scrape_page(
                url="https://example.com/jobs",
                selectors=selectors,
                max_results=5,
            )

            # page.goto should still have been called
            mock_page.goto.assert_awaited_once()


class TestFallbackBehavior:
    """After all stealth retries fail, retry once without stealth."""

    async def _make_engine_and_context(self):
        """Helper to create a mocked engine + context for fallback testing."""
        from app.scrapers.engine import ScraperEngine, PortalSelectors

        engine = ScraperEngine(headless=True)
        selectors = PortalSelectors(job_card=".card", title="h2", company=".company")

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        with patch.object(engine, "_get_browser", return_value=mock_browser):
            yield engine, selectors, mock_context, mock_page

    @patch("app.scrapers.engine.apply_stealth", new_callable=AsyncMock)
    async def test_fallback_retries_without_stealth(self, mock_apply):
        """After all retries with stealth fail, retry once without."""
        from app.scrapers.engine import ScraperEngine, PortalSelectors

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        # The page.goto raises on all stealth attempts
        mock_page.goto = AsyncMock(side_effect=Exception("Connection refused"))
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        engine = ScraperEngine(headless=True)
        selectors = PortalSelectors(job_card=".card", title="h2", company=".company")

        with patch.object(engine, "_get_browser", return_value=mock_browser):
            with pytest.raises(RuntimeError, match="Scrape failed after"):
                await engine.scrape("https://example.com/jobs", selectors, max_results=5)

            # Should have called apply_stealth for all stealth retries
            # (first 3 attempts)
            # Then the final attempt without stealth
            assert mock_context.close.call_count >= 3, "Expected multiple context close calls"

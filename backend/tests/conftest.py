"""Pytest fixtures for E2E tests with Playwright.

Provides browser, page, and auth setup for frontend E2E tests.
"""

from __future__ import annotations

import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from playwright.async_api import Browser, Page, Playwright, async_playwright

# Default URLs — override via env vars or pytest options
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
API_URL = os.getenv("API_URL", "http://localhost:8000/api")
TEST_EMAIL = os.getenv("TEST_EMAIL", "e2e@test.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "testpass123")


# ---------------------------------------------------------------------------
# Playwright browser fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def playwright_instance() -> AsyncIterator[Playwright]:
    """Create a Playwright instance (session-scoped)."""
    async with async_playwright() as pw:
        yield pw


@pytest_asyncio.fixture(scope="session")
async def browser(playwright_instance: Playwright) -> AsyncIterator[Browser]:
    """Launch a Chromium browser (session-scoped).

    Set PLAYWRIGHT_HEADLESS=false to see the browser window.
    """
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
    browser = await playwright_instance.chromium.launch(headless=headless)
    yield browser
    await browser.close()


@pytest_asyncio.fixture
async def page(browser: Browser) -> AsyncIterator[Page]:
    """Create a new browser page for each test."""
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
    p = await ctx.new_page()
    yield p
    await ctx.close()


# ---------------------------------------------------------------------------
# URL fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_url() -> str:
    """Frontend base URL."""
    return FRONTEND_URL


@pytest.fixture
def api_base_url() -> str:
    """Backend API base URL."""
    return API_URL


# ---------------------------------------------------------------------------
# Auth token fixture — logs in via the backend API
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def auth_token(api_base_url: str) -> str:
    """Return a valid JWT token by logging in via the API.

    The test user must exist in the database (seeded or registered).
    Falls back to registering if login fails.
    """
    from httpx import AsyncClient

    async with AsyncClient(base_url=api_base_url, timeout=15) as client:
        # Try to login
        resp = await client.post(
            "/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]

        # User doesn't exist — register
        resp = await client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": "E2E Test User",
            },
        )
        if resp.status_code == 201:
            return resp.json()["access_token"]

        pytest.fail(
            f"Could not obtain auth token. Login: {resp.status_code}, "
            f"Register: check backend is running.",
        )


# ---------------------------------------------------------------------------
# Authenticated page fixture — page with token set in localStorage
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def authed_page(page: Page, base_url: str, auth_token: str) -> Page:
    """Return a page that has a valid auth token in localStorage
    and is already on the profile page."""
    await page.goto(base_url)
    await page.evaluate(
        f"localStorage.setItem('token', '{auth_token}');",
    )
    # Reload to pick up the token
    await page.goto(f"{base_url}/profile")
    await page.wait_for_load_state("networkidle")
    return page

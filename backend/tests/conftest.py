"""Pytest fixtures for unit, integration, and E2E tests.

Provides:
- Integration: async_client, db_session, test_user, auth_headers
- E2E: browser, page, auth_token, authed_page
"""

from __future__ import annotations

import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from playwright.async_api import Browser, Page, Playwright, async_playwright
from sqlalchemy import JSON, NullPool
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# ---------------------------------------------------------------------------
# SQLite PostgreSQL compatibility: convert PG-specific types for SQLite
# ---------------------------------------------------------------------------
from sqlalchemy.ext.compiler import compiles  # noqa: E402

from app.auth.utils import create_access_token
from app.database import Base, get_session
from app.main import app


@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_, compiler, **kw):
    """Use JSON for ARRAY columns on SQLite."""
    return compiler.process(JSON())


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    """Use VARCHAR(36) for UUID columns on SQLite."""
    return "VARCHAR(36)"

# Replace ARRAY column types with JSON in metadata so that bind/result
# processing serializes lists correctly (aiosqlite doesn't accept Python
# lists as bind parameters — it expects scalar values or JSON strings).
for _table in Base.metadata.tables.values():
    for _col in _table.columns:
        if isinstance(_col.type, ARRAY):
            _col.type = JSON()

# Default URLs — override via env vars or pytest options
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
API_URL = os.getenv("API_URL", "http://localhost:8000/api")
TEST_EMAIL = os.getenv("TEST_EMAIL", "e2e@test.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "testpass123")

# ---------------------------------------------------------------------------
# Integration test fixtures (SQLite in-memory)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a SQLite engine for testing (file-based, shared across connections)."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite+aiosqlite:///{tmp.name}"
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()
        import os
        os.unlink(tmp.name)


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    """Create a fresh SQLAlchemy async session for each test.

    Rolls back after each test to keep the DB clean.
    """

    connection = await test_engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user and return it.

    Uses raw SQL to avoid circular imports. Returns an object with .id.
    """
    import uuid

    from app.auth.utils import hash_password

    user_id = str(uuid.uuid4())
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"

    from sqlalchemy import text

    pwd_hash = hash_password("testpass123")
    await db_session.execute(
        text(
            "INSERT INTO \"user\" (id, email, name, password_hash) "
            "VALUES (:id, :email, :name, :password_hash)"
        ),
        {
            "id": user_id,
            "email": email,
            "name": "Test User",
            "password_hash": pwd_hash,
        },
    )
    await db_session.commit()

    class FakeUser:
        def __init__(self, uid: str, uemail: str):
            self.id = uid
            self.email = uemail

    return FakeUser(user_id, email)


@pytest_asyncio.fixture
async def auth_headers(test_user) -> dict[str, str]:
    """Return valid Authorization headers for the test user."""
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Return an httpx AsyncClient wired to the FastAPI test app.

    The get_session dependency is overridden to use the test DB session.
    """

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# E2E test fixtures (Playwright)
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


@pytest.fixture
def base_url() -> str:
    """Frontend base URL."""
    return FRONTEND_URL


@pytest.fixture
def api_base_url() -> str:
    """Backend API base URL."""
    return API_URL


@pytest_asyncio.fixture
async def auth_token(api_base_url: str) -> str:
    """Return a valid JWT token by logging in via the API.

    The test user must exist in the database (seeded or registered).
    Falls back to registering if login fails.
    """
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

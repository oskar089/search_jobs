"""Test fixtures for the Search Jobs app.

Handles PostgreSQL-to-SQLite type adaptation so tests can use an
in-memory SQLite database without requiring a real PostgreSQL instance.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# SQLite compatibility for PostgreSQL-specific types
# ---------------------------------------------------------------------------
# The production models use PostgreSQL-only types (UUID, ARRAY). These
# @compiles directives tell SQLAlchemy how to render them for the SQLite
# dialect so we can use SQLite during tests.
#
# We also monkey-patch the bind/result processors so that Python lists
# are transparently serialised to JSON strings when writing to SQLite
# and deserialised back when reading.


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "VARCHAR(36)"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "TEXT"


# ---- Monkey-patch ARRAY processors for SQLite ----
# Store Python lists as JSON strings so they survive the TEXT column.


def _array_bind_processor_sqlite(
    self: ARRAY,
    dialect: Any,
) -> Any:
    """Serialize lists to JSON for SQLite; defer to original for PostgreSQL."""
    if dialect.name == "sqlite":

        def process(value: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return json.dumps(value)
            return value

        return process
    return _original_array_bp(self, dialect)


def _array_result_processor_sqlite(
    self: ARRAY,
    dialect: Any,
    coltype: Any,
) -> Any:
    """Deserialise JSON strings from SQLite; defer to original for PostgreSQL."""
    if dialect.name == "sqlite":

        def process(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value

        return process
    return _original_array_rp(self, dialect, coltype)


_original_array_bp = ARRAY.bind_processor
_original_array_rp = ARRAY.result_processor
ARRAY.bind_processor = _array_bind_processor_sqlite
ARRAY.result_processor = _array_result_processor_sqlite


# ---------------------------------------------------------------------------
# Imports that depend on the monkey-patches above
# ---------------------------------------------------------------------------
from app.auth.utils import create_access_token, hash_password  # noqa: E402
from app.database import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """Create a file-based SQLite engine, create all tables, yield, then clean up.

    We use a temporary file (not ``:memory:``) because SQLAlchemy's
    ``NullPool`` creates one connection per acquisition, and in-memory is
    per-connection — tables created on one connection would be invisible to
    another.  A file-based database sidesteps this entirely.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name
    database_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh SQLAlchemy async session for each test."""
    factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_app(db_session: AsyncSession) -> AsyncGenerator[Any, None]:
    """Override the ``get_session`` dependency with the test database session."""

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(
    test_app: Any,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an ``httpx.AsyncClient`` wired to the test FastAPI app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create and return a minimal user for authenticated test scenarios."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("secret123"),
        name="Test User",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_token(test_user: User) -> str:
    """Generate a valid JWT access token for ``test_user``."""
    return create_access_token(test_user.id)


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict[str, str]:
    """Return ``Authorization: Bearer <token>`` headers for the test user."""
    return {"Authorization": f"Bearer {auth_token}"}

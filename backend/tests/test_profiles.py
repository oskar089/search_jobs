"""Unit tests for profile CRUD logic at the database/ORM level.

Validates create, read, and update operations on ``Profile`` model instances.
Uses the test database session from ``conftest.py``.
"""

from sqlalchemy import select

from app.models import Profile

# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------


async def test_create_profile_minimal(db_session, test_user):
    """A profile can be created with just user_id and experience_level."""
    profile = Profile(user_id=test_user.id, experience_level="senior")
    db_session.add(profile)
    await db_session.flush()

    assert profile.id is not None
    assert profile.user_id == test_user.id
    assert profile.experience_level == "senior"
    # Defaults
    assert profile.is_active is True
    assert profile.remote_only is False
    assert profile.target_roles == []
    assert profile.tech_stack == []


async def test_create_profile_full(db_session, test_user):
    """A profile with all fields populated stores them correctly."""
    profile = Profile(
        user_id=test_user.id,
        target_roles=["backend", "devops"],
        tech_stack=["python", "docker"],
        experience_level="mid",
        min_salary=60000,
        max_salary=100000,
        locations=["Buenos Aires", "Remote"],
        remote_only=True,
        languages=["es", "en"],
        is_active=True,
    )
    db_session.add(profile)
    await db_session.flush()

    assert profile.min_salary == 60000
    assert profile.max_salary == 100000
    assert profile.locations == ["Buenos Aires", "Remote"]
    assert profile.remote_only is True
    assert profile.languages == ["es", "en"]
    assert profile.tech_stack == ["python", "docker"]


async def test_create_profile_unique_user_id_constraint(db_session, test_user):
    """The same user cannot have more than one profile (unique user_id)."""
    Profile(user_id=test_user.id, experience_level="junior")
    db_session.add(Profile(user_id=test_user.id, experience_level="junior"))
    await db_session.flush()

    # A second profile with the same user_id should fail
    dup = Profile(user_id=test_user.id, experience_level="senior")
    db_session.add(dup)
    import pytest

    with pytest.raises(Exception):  # IntegrityError
        await db_session.flush()


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------


async def test_get_profile_by_user_id(db_session, test_user):
    """A profile can be retrieved by ``user_id``."""
    profile = Profile(user_id=test_user.id, experience_level="mid")
    db_session.add(profile)
    await db_session.flush()

    result = await db_session.execute(
        select(Profile).where(Profile.user_id == test_user.id),
    )
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.id == profile.id
    assert found.experience_level == "mid"


async def test_get_profile_not_found(db_session):
    """Querying a non-existent user_id returns ``None``."""
    result = await db_session.execute(
        select(Profile).where(Profile.user_id == "nonexistent"),
    )
    assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


async def test_update_profile_fields(db_session, test_user):
    """Individual profile fields persist after update."""
    profile = Profile(user_id=test_user.id, experience_level="junior")
    db_session.add(profile)
    await db_session.flush()

    profile.experience_level = "senior"
    profile.target_roles = ["tech-lead"]
    await db_session.flush()
    await db_session.refresh(profile)

    assert profile.experience_level == "senior"
    assert profile.target_roles == ["tech-lead"]


async def test_partial_update_preserves_other_fields(db_session, test_user):
    """Updating one field does not reset other fields to defaults."""
    profile = Profile(
        user_id=test_user.id,
        experience_level="senior",
        min_salary=80000,
        max_salary=120000,
        target_roles=["engineer"],
    )
    db_session.add(profile)
    await db_session.flush()

    # Update only max_salary
    profile.max_salary = 150000
    await db_session.flush()
    await db_session.refresh(profile)

    assert profile.min_salary == 80000  # unchanged
    assert profile.max_salary == 150000  # updated
    assert profile.experience_level == "senior"  # unchanged
    assert profile.target_roles == ["engineer"]  # unchanged

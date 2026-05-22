import pytest
from sqlalchemy import select, delete

from app.models.user import User


@pytest.mark.asyncio
async def test_first_user_becomes_superuser(db):
    """When users table is empty, first user should be superuser."""
    # Clear any existing users to simulate fresh migration state
    await db.execute(delete(User))
    await db.commit()

    # No users exist
    result = await db.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 0

    # Create first user (simulating migration from env vars)
    user = User(
        email='admin@example.com',
        password_hash='hashed_password',
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.commit()

    result = await db.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1
    assert users[0].is_superuser is True
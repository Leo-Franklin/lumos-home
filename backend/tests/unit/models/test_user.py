import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite engine with all tables created."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    from app.models import (  # noqa: F401
        camera,
        device,
        device_online_log,
        dlna_device,
        member,
        recording,
        schedule,
        user,
        user_settings,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_create(db):
    user = User(
        email='test@example.com',
        password_hash='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.S0JUHSAbH',
        is_active=False,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    assert user.id is not None
    assert user.email == 'test@example.com'
    assert user.is_active is False
    assert user.is_superuser is False


@pytest.mark.asyncio
async def test_user_unique_email(db):
    user1 = User(email='dup@example.com', password_hash='hash1')
    db.add(user1)
    await db.commit()

    user2 = User(email='dup@example.com', password_hash='hash2')
    db.add(user2)
    with pytest.raises(IntegrityError):
        await db.commit()

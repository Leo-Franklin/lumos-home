import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.email_token import EmailVerificationToken, PasswordResetToken


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite engine with all tables created."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    from app.models import (  # noqa: F401
        camera, device, device_online_log, dlna_device, email_token, member, recording, schedule, user, user_settings,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_email_verification_token_create(db):
    import uuid
    token = EmailVerificationToken(
        user_id=1,
        token=str(uuid.uuid4()),
        expires_at=datetime.now() + timedelta(hours=24),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    assert token.id is not None


@pytest.mark.asyncio
async def test_password_reset_token_create(db):
    import uuid
    token = PasswordResetToken(
        user_id=1,
        token=str(uuid.uuid4()),
        expires_at=datetime.now() + timedelta(minutes=15),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    assert token.id is not None
import asyncio
import os
import time
from pathlib import Path

import pytest_asyncio
from sqlalchemy import create_engine

os.environ['JWT_SECRET_KEY'] = 'test_secret_key_that_is_at_least_32_characters_long'
os.environ['ADMIN_PASSWORD'] = 'testpassword_for_ci_only'
os.environ['CORS_ALLOW_ORIGINS'] = 'http://localhost:5173'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/test.db'
os.environ['GITHUB_CLIENT_ID'] = 'test_github_client_id'
os.environ['GITHUB_CLIENT_SECRET'] = 'test_github_client_secret'
os.environ['GO2RTC_ENABLED'] = 'false'


def pytest_configure(config):
    """Re-assert env vars in case something reset them after module load."""
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key_that_is_at_least_32_characters_long'
    os.environ['ADMIN_PASSWORD'] = 'testpassword_for_ci_only'
    os.environ['CORS_ALLOW_ORIGINS'] = 'http://localhost:5173'
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/test.db'


@pytest_asyncio.fixture
async def db():
    """Provide a test database session."""
    from app.database import _get_session_maker

    async with _get_session_maker()() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def cleanup_recordings():
    """Delete all Recording rows after each test to prevent cross-test pollution."""
    yield
    from sqlalchemy import delete

    from app.database import AsyncSessionLocal
    from app.models.recording import Recording

    async with AsyncSessionLocal() as session:
        await session.execute(delete(Recording))
        await session.commit()


def _sqlite_db_paths(db_path: Path) -> list[Path]:
    return [db_path, Path(f'{db_path}-wal'), Path(f'{db_path}-shm')]


def _dispose_cached_db_engines() -> None:
    """Close app.database singleton engines so Windows can delete test.db."""
    import app.database as db_module

    engine = db_module._engine
    if engine is None:
        return
    db_module._engine = None
    db_module._AsyncSessionLocal = None
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()


def _try_remove_test_db(test_db_path: Path) -> bool:
    """Remove test.db and SQLite sidecars. Returns False if the file stays locked."""
    _dispose_cached_db_engines()
    for attempt in range(5):
        try:
            for path in _sqlite_db_paths(test_db_path):
                if path.exists():
                    path.unlink()
            return True
        except PermissionError:
            _dispose_cached_db_engines()
            if attempt == 4:
                return False
            time.sleep(0.2 * (attempt + 1))
    return False


def _create_fresh_test_schema(sync_url: str) -> None:
    from app.database import Base

    engine = create_engine(sync_url, connect_args={'check_same_thread': False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


def pytest_sessionstart(session):
    """Create test database tables once per session, before any test runs.

    ASGITransport does not trigger FastAPI's lifespan, so init_db() never
    runs automatically. We create tables here so API-level integration tests
    have a working database.

    Uses a dedicated test database (data/test.db) separate from the
    production database (data/smart_home.db) to prevent test pollution.
    """
    from app.config import get_settings
    from app.database import Base

    # Import all model modules so they register with Base.metadata before create_all
    from app.domain.models import (  # noqa: F401
        camera,
        device,
        device_online_log,
        dlna_device,
        member,
        recording,
        schedule,
        user_settings,
    )
    from app.models import (
        email_token,  # noqa: F401
        user,  # noqa: F401
    )

    settings = get_settings()
    Path('data').mkdir(exist_ok=True)

    test_db_path = Path('data/test.db')
    sync_url = settings.database_url.replace('sqlite+aiosqlite:///', 'sqlite:///', 1)

    if not _try_remove_test_db(test_db_path):
        # Windows: another process (or a stale handle) may keep test.db open.
        # Fall back to resetting schema in place instead of failing session start.
        _create_fresh_test_schema(sync_url)
        return

    engine = create_engine(sync_url, connect_args={'check_same_thread': False})
    Base.metadata.create_all(bind=engine)
    engine.dispose()

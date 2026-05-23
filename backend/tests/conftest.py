import os
from pathlib import Path

from sqlalchemy import create_engine

os.environ['JWT_SECRET_KEY'] = 'test_secret_key_that_is_at_least_32_characters_long'
os.environ['ADMIN_PASSWORD'] = 'testpassword_for_ci_only'
os.environ['CORS_ALLOW_ORIGINS'] = 'http://localhost:5173'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/test.db'


def pytest_configure(config):
    """Re-assert env vars in case something reset them after module load."""
    os.environ['JWT_SECRET_KEY'] = 'test_secret_key_that_is_at_least_32_characters_long'
    os.environ['ADMIN_PASSWORD'] = 'testpassword_for_ci_only'
    os.environ['CORS_ALLOW_ORIGINS'] = 'http://localhost:5173'
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/test.db'


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

    settings = get_settings()
    Path('data').mkdir(exist_ok=True)

    # Always start with a clean test database
    test_db_path = Path('data/test.db')
    if test_db_path.exists():
        test_db_path.unlink()

    # Convert aiosqlite URL to sync sqlite URL for table creation
    sync_url = settings.database_url.replace('sqlite+aiosqlite:///', 'sqlite:///', 1)
    engine = create_engine(sync_url, connect_args={'check_same_thread': False})
    Base.metadata.create_all(bind=engine)
    engine.dispose()

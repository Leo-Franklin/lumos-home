from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Lazy import to avoid triggering settings validation at import time
# (settings validation requires real .env values which aren't available during test collection)
_engine = None
_AsyncSessionLocal = None


class _LazySessionMaker:
    """Lazy proxy for AsyncSessionLocal — defers settings access until first use."""

    def __call__(self):
        return _get_session_maker()()

    def begin(self, **kwargs):
        return _get_session_maker().begin(**kwargs)

    @property
    def engine(self):
        return _get_engine()


# Backwards-compatible API entry point (matches original AsyncSessionLocal interface)
AsyncSessionLocal = _LazySessionMaker()


def _get_engine():
    global _engine
    if _engine is None:
        from app.config import get_settings

        settings = get_settings()
        from sqlalchemy.ext.asyncio import create_async_engine

        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            connect_args={'check_same_thread': False},
        )
    return _engine


def _get_session_maker():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        from app.config import get_settings

        settings = get_settings()
        from sqlalchemy.ext.asyncio import async_sessionmaker

        _AsyncSessionLocal = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _AsyncSessionLocal


async def init_db() -> None:
    # Import all models so create_all picks them up

    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent column migrations — wrapped individually so one failure doesn't block others
        for stmt in (
            'ALTER TABLE cameras ADD COLUMN rtsp_url TEXT',
            'ALTER TABLE devices ADD COLUMN hostname TEXT',
            'ALTER TABLE devices ADD COLUMN open_ports TEXT',
            'ALTER TABLE devices ADD COLUMN response_time_ms REAL',
            "ALTER TABLE members ADD COLUMN auto_record_cameras JSON DEFAULT '[]'",
            'ALTER TABLE cameras ADD COLUMN is_online BOOLEAN NOT NULL DEFAULT 1',
            'ALTER TABLE cameras ADD COLUMN last_probe_at DATETIME',
            'ALTER TABLE cameras ADD COLUMN auto_cast_dlna VARCHAR(256)',
            "ALTER TABLE cameras ADD COLUMN recording_presets JSON DEFAULT '[]'",
            'ALTER TABLE cameras ADD COLUMN default_preset_id VARCHAR(36)',
            'ALTER TABLE schedules ADD COLUMN preset_id VARCHAR(36)',
            'ALTER TABLE schedules ADD COLUMN overrides TEXT',
        ):
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_maker()() as session:
        yield session

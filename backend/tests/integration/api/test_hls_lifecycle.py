"""Integration tests for deprecated HLS live endpoints.

HLS live streaming was removed in favor of a future go2rtc-based player.
These endpoints remain as stubs returning HTTP 410 Gone.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture
async def mem_db():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    from app.database import Base
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
    from app.models import user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    yield Session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(mem_db):
    from app.database import get_db
    from app.deps import get_current_user
    from app.main import app as fastapi_app

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as c:
        yield c

    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_live_start_returns_410_gone(client):
    response = await client.post('/api/v1/cameras/AA:BB:CC:DD:EE:01/live/start')
    assert response.status_code == 410
    assert 'go2rtc' in response.json()['error']['message']


@pytest.mark.asyncio
async def test_live_stop_returns_410_gone(client):
    response = await client.delete('/api/v1/cameras/AA:BB:CC:DD:EE:01/live/stop')
    assert response.status_code == 410
    assert 'go2rtc' in response.json()['error']['message']

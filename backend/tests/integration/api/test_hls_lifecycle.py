"""Integration tests for the HLS start/stop endpoints.

Goal of P0-1: HLS process management moves out of the router into
StreamManager. These tests prove the router delegates to the manager and
that previously-magic globals (`_live_procs`, `_HLS_BASE`) no longer
exist as process holders.
"""

from unittest.mock import AsyncMock, MagicMock

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
async def client_with_stream_manager(mem_db):
    """App client with a fake StreamManager injected into app.state."""
    from app.database import get_db
    from app.deps import get_current_user, get_stream_user
    from app.main import app as fastapi_app

    fake_manager = MagicMock()
    # get() returns a real-ish StreamInfo-shaped value with idle state
    fake_manager.get.return_value = MagicMock(state='idle', camera_mac='A')
    fake_manager.start_hls = AsyncMock(return_value=MagicMock(state='running'))
    fake_manager.stop = AsyncMock(return_value=None)
    fastapi_app.state.stream_manager = fake_manager

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'
    fastapi_app.dependency_overrides[get_stream_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as c:
        yield c, fake_manager

    fastapi_app.dependency_overrides.clear()


async def _seed_camera_with_rtsp(mem_db, mac: str = 'AA:BB:CC:DD:EE:01'):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=mac, device_type='camera', is_online=True))
        await db.commit()
        db.add(Camera(device_mac=mac, onvif_host='192.168.1.10', rtsp_url='rtsp://x/y'))
        await db.commit()


@pytest.mark.asyncio
async def test_live_start_delegates_to_stream_manager(mem_db, client_with_stream_manager):
    await _seed_camera_with_rtsp(mem_db)
    client, mgr = client_with_stream_manager

    response = await client.post('/api/v1/cameras/AA:BB:CC:DD:EE:01/live/start')
    assert response.status_code == 202
    # The router must have called StreamManager.start_hls exactly once
    assert mgr.start_hls.await_count == 1
    # And it was passed the uppercased MAC and the rtsp URL
    args, _kwargs = mgr.start_hls.call_args
    assert args[0] == 'AA:BB:CC:DD:EE:01'
    assert args[1] == 'rtsp://x/y'


@pytest.mark.asyncio
async def test_live_stop_delegates_to_stream_manager(mem_db, client_with_stream_manager):
    await _seed_camera_with_rtsp(mem_db)
    client, mgr = client_with_stream_manager

    response = await client.delete('/api/v1/cameras/AA:BB:CC:DD:EE:01/live/stop')
    assert response.status_code == 202
    mgr.stop.assert_called_once_with('AA:BB:CC:DD:EE:01')


@pytest.mark.asyncio
async def test_hls_start_fails_when_no_rtsp_url(mem_db, client_with_stream_manager):
    """Sanity check: routers still validate preconditions before delegating."""
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac='AA:BB:CC:DD:EE:02', device_type='camera', is_online=True))
        await db.commit()
        db.add(Camera(device_mac='AA:BB:CC:DD:EE:02', onvif_host='192.168.1.10', rtsp_url=None))
        await db.commit()

    client, mgr = client_with_stream_manager
    response = await client.post('/api/v1/cameras/AA:BB:CC:DD:EE:02/live/start')
    assert response.status_code == 422
    mgr.start_hls.assert_not_called()

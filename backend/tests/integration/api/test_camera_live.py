"""Integration tests for GET /cameras/{mac}/live (go2rtc live info)."""

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
async def client_with_go2rtc(mem_db):
    from app.database import get_db
    from app.deps import get_current_user
    from app.domain.services.go2rtc_adapter import Go2RtcAdapter, Go2RtcConfig, LiveStreamInfo
    from app.main import app as fastapi_app

    fake_adapter = MagicMock(spec=Go2RtcAdapter)
    fake_adapter.config = Go2RtcConfig(enabled=True)
    fake_adapter.build_live_info.return_value = LiveStreamInfo(
        mode='mse',
        stream_name='AA-BB-CC-DD-EE-01',
        status='ready',
        mse_ws_url='/api/v1/cameras/AA:BB:CC:DD:EE:01/live/ws',
        webrtc_url='/api/v1/cameras/AA:BB:CC:DD:EE:01/live/webrtc',
        mjpeg_url='/api/v1/cameras/AA:BB:CC:DD:EE:01/stream/mjpeg',
    )
    fake_adapter.ensure_stream = AsyncMock()
    fake_adapter.ping = AsyncMock(return_value=True)
    # Save the real adapter so the teardown can restore it. Tests outside
    # this file (e.g. test_recording_presets) import the same `app` object
    # and rely on the adapter being set.
    _original_adapter = getattr(fastapi_app.state, 'go2rtc_adapter', None)
    fastapi_app.state.go2rtc_adapter = fake_adapter

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as c:
        yield c, fake_adapter

    fastapi_app.dependency_overrides.clear()
    fastapi_app.state.go2rtc_adapter = _original_adapter


async def _seed_camera(mem_db, mac: str = 'AA:BB:CC:DD:EE:01', rtsp_url: str = 'rtsp://x/y'):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=mac, device_type='camera', is_online=True))
        await db.commit()
        db.add(Camera(device_mac=mac, onvif_host='192.168.1.10', rtsp_url=rtsp_url))
        await db.commit()


@pytest.mark.asyncio
async def test_get_live_info_syncs_stream_and_returns_mse_urls(mem_db, client_with_go2rtc):
    await _seed_camera(mem_db)
    client, adapter = client_with_go2rtc

    response = await client.get('/api/v1/cameras/AA:BB:CC:DD:EE:01/live')
    assert response.status_code == 200
    body = response.json()
    assert body['mode'] == 'mse'
    assert body['stream_name'] == 'AA-BB-CC-DD-EE-01'
    assert body['mse_ws_url'].endswith('/live/ws')
    adapter.ensure_stream.assert_awaited_once_with('AA-BB-CC-DD-EE-01', 'rtsp://x/y')


@pytest.mark.asyncio
async def test_get_live_info_returns_404_for_unknown_camera(mem_db, client_with_go2rtc):
    client, adapter = client_with_go2rtc
    response = await client.get('/api/v1/cameras/AA:BB:CC:DD:EE:99/live')
    assert response.status_code == 404
    adapter.ensure_stream.assert_not_called()


@pytest.mark.asyncio
async def test_get_live_info_returns_422_without_rtsp(mem_db, client_with_go2rtc):
    await _seed_camera(mem_db, rtsp_url=None)
    client, adapter = client_with_go2rtc
    response = await client.get('/api/v1/cameras/AA:BB:CC:DD:EE:01/live')
    assert response.status_code == 422
    adapter.ensure_stream.assert_not_called()


@pytest.mark.asyncio
async def test_get_live_info_falls_back_when_go2rtc_unreachable(mem_db, client_with_go2rtc):
    """Reproduces the live-button 500: go2rtc is enabled in settings, but the
    go2rtc process is not running (port refused). The route must NOT 500; it
    should return the mjpeg_fallback payload and the caller (LivePlayer) will
    degrade to the <img> stream.

    The adapter is a MagicMock, so the "go2rtc unreachable" condition is
    modeled by the post-fix contract: ensure_stream returns normally (the
    real adapter catches httpx errors and returns None), ping() returns
    False, and build_live_info returns the unavailable payload.
    """
    from app.domain.services.go2rtc_adapter import LiveStreamInfo

    await _seed_camera(mem_db)
    client, adapter = client_with_go2rtc
    adapter.ensure_stream.return_value = None  # post-fix: no exception
    adapter.ping.return_value = False
    adapter.build_live_info.return_value = LiveStreamInfo(
        mode='mjpeg_fallback',
        stream_name='AA-BB-CC-DD-EE-01',
        status='unavailable',
        mjpeg_url='/api/v1/cameras/AA:BB:CC:DD:EE:01/stream/mjpeg',
    )

    response = await client.get('/api/v1/cameras/AA:BB:CC:DD:EE:01/live')
    assert response.status_code == 200
    body = response.json()
    assert body['mode'] == 'mjpeg_fallback'
    assert body['status'] == 'unavailable'
    assert body['mjpeg_url'].endswith('/stream/mjpeg')

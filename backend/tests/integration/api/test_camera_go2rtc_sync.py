"""Integration tests — camera CRUD syncs go2rtc streams when enabled."""

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
    from app.domain.services.go2rtc_adapter import Go2RtcAdapter, Go2RtcConfig
    from app.main import app as fastapi_app

    fake_adapter = MagicMock(spec=Go2RtcAdapter)
    fake_adapter.config = Go2RtcConfig(enabled=True)
    fake_adapter.ensure_stream = AsyncMock()
    fake_adapter.remove_stream = AsyncMock()
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


async def _seed_device(mem_db, mac: str = 'AA:BB:CC:DD:EE:01'):
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=mac, device_type='camera', is_online=True))
        await db.commit()


async def _seed_camera(
    mem_db,
    mac: str = 'AA:BB:CC:DD:EE:01',
    rtsp_url: str | None = 'rtsp://192.168.1.10/stream',
):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=mac, device_type='camera', is_online=True))
        await db.commit()
        db.add(
            Camera(
                device_mac=mac,
                onvif_host='192.168.1.10',
                rtsp_url=rtsp_url,
                onvif_user='admin',
                onvif_password='secret',
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_create_camera_with_rtsp_syncs_go2rtc_stream(mem_db, client_with_go2rtc):
    await _seed_device(mem_db)
    client, adapter = client_with_go2rtc

    response = await client.post(
        '/api/v1/cameras',
        json={
            'device_mac': 'AA:BB:CC:DD:EE:01',
            'onvif_host': '192.168.1.10',
            'rtsp_url': 'rtsp://192.168.1.10/stream',
            'onvif_user': 'admin',
            'onvif_password': 'secret',
        },
    )
    assert response.status_code == 201
    adapter.ensure_stream.assert_awaited_once_with(
        'AA-BB-CC-DD-EE-01',
        'rtsp://admin:secret@192.168.1.10/stream',
    )


@pytest.mark.asyncio
async def test_create_camera_without_rtsp_skips_sync(mem_db, client_with_go2rtc):
    await _seed_device(mem_db)
    client, adapter = client_with_go2rtc

    response = await client.post(
        '/api/v1/cameras',
        json={'device_mac': 'AA:BB:CC:DD:EE:01', 'onvif_host': '192.168.1.10'},
    )
    assert response.status_code == 201
    adapter.ensure_stream.assert_not_called()


@pytest.mark.asyncio
async def test_update_camera_rtsp_syncs_go2rtc_stream(mem_db, client_with_go2rtc):
    await _seed_camera(mem_db)
    client, adapter = client_with_go2rtc

    response = await client.put(
        '/api/v1/cameras/AA:BB:CC:DD:EE:01',
        json={'rtsp_url': 'rtsp://192.168.1.10/newstream'},
    )
    assert response.status_code == 200
    adapter.ensure_stream.assert_awaited_once_with(
        'AA-BB-CC-DD-EE-01',
        'rtsp://admin:secret@192.168.1.10/newstream',
    )


@pytest.mark.asyncio
async def test_update_camera_credentials_syncs_go2rtc_stream(mem_db, client_with_go2rtc):
    await _seed_camera(mem_db)
    client, adapter = client_with_go2rtc

    response = await client.put(
        '/api/v1/cameras/AA:BB:CC:DD:EE:01',
        json={'onvif_password': 'newpass'},
    )
    assert response.status_code == 200
    adapter.ensure_stream.assert_awaited_once_with(
        'AA-BB-CC-DD-EE-01',
        'rtsp://admin:newpass@192.168.1.10/stream',
    )


@pytest.mark.asyncio
async def test_delete_camera_removes_go2rtc_stream(mem_db, client_with_go2rtc):
    await _seed_camera(mem_db)
    client, adapter = client_with_go2rtc

    response = await client.delete('/api/v1/cameras/AA:BB:CC:DD:EE:01')
    assert response.status_code == 204
    adapter.remove_stream.assert_awaited_once_with('AA-BB-CC-DD-EE-01')


@pytest.mark.asyncio
async def test_crud_skips_sync_when_go2rtc_disabled(mem_db):
    from app.database import get_db
    from app.deps import get_current_user
    from app.domain.services.go2rtc_adapter import Go2RtcAdapter, Go2RtcConfig
    from app.main import app as fastapi_app

    fake_adapter = MagicMock(spec=Go2RtcAdapter)
    fake_adapter.config = Go2RtcConfig(enabled=False)
    fake_adapter.ensure_stream = AsyncMock()
    fake_adapter.remove_stream = AsyncMock()
    fastapi_app.state.go2rtc_adapter = fake_adapter

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    await _seed_device(mem_db)
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as client:
        await client.post(
            '/api/v1/cameras',
            json={
                'device_mac': 'AA:BB:CC:DD:EE:01',
                'onvif_host': '192.168.1.10',
                'rtsp_url': 'rtsp://192.168.1.10/stream',
            },
        )
        fake_adapter.ensure_stream.assert_not_called()

        await _seed_camera(mem_db, mac='BB:CC:DD:EE:FF:00')
        await client.put(
            '/api/v1/cameras/BB:CC:DD:EE:FF:00',
            json={'rtsp_url': 'rtsp://192.168.1.20/stream'},
        )
        fake_adapter.ensure_stream.assert_not_called()

        await client.delete('/api/v1/cameras/BB:CC:DD:EE:FF:00')
        fake_adapter.remove_stream.assert_not_called()

    fastapi_app.dependency_overrides.clear()

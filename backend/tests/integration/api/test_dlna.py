"""Integration tests for app/api/dlna.py endpoints.

Coverage target: 60%+
Endpoints under test:
    POST /api/v1/dlna/discover           -> 202
    GET  /api/v1/dlna                    -> list_dlna_devices
    POST /api/v1/dlna/cast               -> cast_url
    POST /api/v1/dlna/{id}/play          -> play (204)
    POST /api/v1/dlna/{id}/pause         -> pause (204)
    POST /api/v1/dlna/{id}/stop          -> stop (204)
    GET  /api/v1/dlna/{id}/status        -> get_status
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base

# ---------------------------------------------------------------------------
# In-memory DB fixture (shared across the whole module)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mem_db():
    """Isolated in-memory SQLite with all tables created."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    # Ensure all model tables are registered with Base.metadata
    from app.models import (  # noqa: F401
        camera,
        device,
        device_online_log,
        dlna_device,
        member,
        recording,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    yield Session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Authenticated client fixture
# ---------------------------------------------------------------------------

_JWT_KEY = 'test_secret_key_that_is_at_least_32_characters_long'
_ADMIN_PW = 'testpassword12345'


@pytest_asyncio.fixture
async def client(mem_db, monkeypatch):
    """AsyncClient backed by in-memory DB with auth dependency bypassed."""
    monkeypatch.setenv('JWT_SECRET_KEY', _JWT_KEY)
    monkeypatch.setenv('ADMIN_PASSWORD', _ADMIN_PW)

    from app.config import get_settings

    get_settings.cache_clear()

    from app.database import get_db
    from app.deps import get_current_user
    from app.main import app as fastapi_app

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://test') as c:
        yield c

    fastapi_app.dependency_overrides.clear()
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Helper to insert a DLNADevice row
# ---------------------------------------------------------------------------


async def _create_device(
    mem_db, *, av_transport_url: str | None = 'http://192.168.1.10:49152/AVTransport'
) -> int:
    """Insert a DLNADevice and return its id."""
    from app.domain.models.dlna_device import DLNADevice

    async with mem_db() as db:
        device = DLNADevice(
            udn=f'uuid:{uuid.uuid4()}',
            friendly_name='Test Renderer',
            device_type='urn:schemas-upnp-org:device:MediaRenderer:1',
            manufacturer='Acme',
            model_name='Renderer 1000',
            ip='192.168.1.10',
            location_url='http://192.168.1.10:49152/description.xml',
            av_transport_url=av_transport_url,
            rendering_control_url='http://192.168.1.10:49152/RenderingControl',
            is_online=True,
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device.id


# ===========================================================================
# POST /api/v1/dlna/discover
# ===========================================================================


@pytest.mark.asyncio
async def test_discover_returns_202(client):
    with patch('app.api.dlna.ws_manager.broadcast', new_callable=AsyncMock):
        resp = await client.post('/api/v1/dlna/discover')
    assert resp.status_code == 202
    assert 'message' in resp.json()


# ===========================================================================
# GET /api/v1/dlna  (list_dlna_devices)
# ===========================================================================


@pytest.mark.asyncio
async def test_list_dlna_devices_empty(client):
    resp = await client.get('/api/v1/dlna')
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_dlna_devices_returns_inserted(client, mem_db):
    await _create_device(mem_db)
    resp = await client.get('/api/v1/dlna')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['friendly_name'] == 'Test Renderer'
    assert data[0]['is_online'] is True


@pytest.mark.asyncio
async def test_list_dlna_devices_multiple(client, mem_db):
    await _create_device(mem_db)
    await _create_device(mem_db)
    resp = await client.get('/api/v1/dlna')
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ===========================================================================
# POST /api/v1/dlna/cast
# ===========================================================================


@pytest.mark.asyncio
async def test_cast_url_success(client, mem_db):
    device_id = await _create_device(
        mem_db, av_transport_url='http://192.168.1.10:49152/AVTransport'
    )

    with (
        patch('app.api.dlna.DLNAController') as mock_ctrl_cls,
        patch('app.api.dlna.ws_manager.broadcast', new_callable=AsyncMock),
    ):
        mock_ctrl = AsyncMock()
        mock_ctrl_cls.return_value = mock_ctrl
        mock_ctrl.set_uri = AsyncMock()
        mock_ctrl.play = AsyncMock()

        resp = await client.post(
            '/api/v1/dlna/cast',
            json={'device_id': device_id, 'media_url': 'http://example.com/video.mp4'},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data['message'] == '投屏成功'
    assert data['device'] == 'Test Renderer'
    mock_ctrl.set_uri.assert_called_once_with('http://example.com/video.mp4')
    mock_ctrl.play.assert_called_once()


@pytest.mark.asyncio
async def test_cast_url_device_not_found(client):
    resp = await client.post(
        '/api/v1/dlna/cast',
        json={'device_id': 9999, 'media_url': 'http://example.com/video.mp4'},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cast_url_no_av_transport(client, mem_db):
    device_id = await _create_device(mem_db, av_transport_url=None)

    resp = await client.post(
        '/api/v1/dlna/cast',
        json={'device_id': device_id, 'media_url': 'http://example.com/video.mp4'},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cast_url_controller_failure_returns_502(client, mem_db):
    device_id = await _create_device(
        mem_db, av_transport_url='http://192.168.1.10:49152/AVTransport'
    )

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = AsyncMock()
        mock_ctrl_cls.return_value = mock_ctrl
        mock_ctrl.set_uri = AsyncMock(side_effect=RuntimeError('Connection refused'))
        mock_ctrl.play = AsyncMock()

        resp = await client.post(
            '/api/v1/dlna/cast',
            json={'device_id': device_id, 'media_url': 'http://example.com/video.mp4'},
        )

    assert resp.status_code == 502


# ===========================================================================
# POST /api/v1/dlna/{id}/play
# ===========================================================================


@pytest.mark.asyncio
async def test_play_success(client, mem_db):
    device_id = await _create_device(mem_db)

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.play = AsyncMock()
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.post(f'/api/v1/dlna/{device_id}/play')

    assert resp.status_code == 204
    mock_ctrl.play.assert_called_once()


@pytest.mark.asyncio
async def test_play_device_not_found(client):
    resp = await client.post('/api/v1/dlna/9999/play')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_play_no_av_transport(client, mem_db):
    device_id = await _create_device(mem_db, av_transport_url=None)
    resp = await client.post(f'/api/v1/dlna/{device_id}/play')
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_play_controller_failure_returns_502(client, mem_db):
    device_id = await _create_device(mem_db)

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.play = AsyncMock(side_effect=RuntimeError('device unreachable'))
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.post(f'/api/v1/dlna/{device_id}/play')

    assert resp.status_code == 502


# ===========================================================================
# POST /api/v1/dlna/{id}/pause
# ===========================================================================


@pytest.mark.asyncio
async def test_pause_success(client, mem_db):
    device_id = await _create_device(mem_db)

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.pause = AsyncMock()
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.post(f'/api/v1/dlna/{device_id}/pause')

    assert resp.status_code == 204
    mock_ctrl.pause.assert_called_once()


@pytest.mark.asyncio
async def test_pause_device_not_found(client):
    resp = await client.post('/api/v1/dlna/9999/pause')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pause_controller_failure_returns_502(client, mem_db):
    device_id = await _create_device(mem_db)

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.pause = AsyncMock(side_effect=RuntimeError('timeout'))
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.post(f'/api/v1/dlna/{device_id}/pause')

    assert resp.status_code == 502


# ===========================================================================
# POST /api/v1/dlna/{id}/stop
# ===========================================================================


@pytest.mark.asyncio
async def test_stop_success(client, mem_db):
    device_id = await _create_device(mem_db)

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.stop = AsyncMock()
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.post(f'/api/v1/dlna/{device_id}/stop')

    assert resp.status_code == 204
    mock_ctrl.stop.assert_called_once()


@pytest.mark.asyncio
async def test_stop_device_not_found(client):
    resp = await client.post('/api/v1/dlna/9999/stop')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stop_controller_failure_returns_502(client, mem_db):
    device_id = await _create_device(mem_db)

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.stop = AsyncMock(side_effect=RuntimeError('network error'))
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.post(f'/api/v1/dlna/{device_id}/stop')

    assert resp.status_code == 502


# ===========================================================================
# GET /api/v1/dlna/{id}/status
# ===========================================================================


@pytest.mark.asyncio
async def test_get_status_success(client, mem_db):
    device_id = await _create_device(mem_db)

    transport_info = {
        'current_transport_state': 'PLAYING',
        'current_transport_status': 'OK',
        'current_speed': '1',
    }

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.get_transport_info = AsyncMock(return_value=transport_info)
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.get(f'/api/v1/dlna/{device_id}/status')

    assert resp.status_code == 200
    data = resp.json()
    assert data['current_transport_state'] == 'PLAYING'
    assert data['current_transport_status'] == 'OK'
    assert data['current_speed'] == '1'


@pytest.mark.asyncio
async def test_get_status_device_not_found(client):
    resp = await client.get('/api/v1/dlna/9999/status')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_status_no_av_transport(client, mem_db):
    device_id = await _create_device(mem_db, av_transport_url=None)
    resp = await client.get(f'/api/v1/dlna/{device_id}/status')
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_status_controller_failure_returns_502(client, mem_db):
    device_id = await _create_device(mem_db)

    with patch('app.api.dlna.DLNAController') as mock_ctrl_cls:
        mock_ctrl = MagicMock()
        mock_ctrl.get_transport_info = AsyncMock(side_effect=RuntimeError('SOAP error'))
        mock_ctrl_cls.return_value = mock_ctrl

        resp = await client.get(f'/api/v1/dlna/{device_id}/status')

    assert resp.status_code == 502


# ===========================================================================
# Schema field validation
# ===========================================================================


@pytest.mark.asyncio
async def test_list_dlna_devices_response_schema(client, mem_db):
    """Verify all DLNADeviceOut fields are present in list response."""
    await _create_device(mem_db)
    resp = await client.get('/api/v1/dlna')
    assert resp.status_code == 200
    item = resp.json()[0]
    for field in ['id', 'udn', 'friendly_name', 'is_online', 'av_transport_url', 'created_at']:
        assert field in item, f'Missing field: {field}'

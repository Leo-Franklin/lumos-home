"""Integration tests for GET/PUT /system/go2rtc settings."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_current_user
from app.domain.services.go2rtc_adapter import Go2RtcAdapter, Go2RtcConfig
from app.domain.services.go2rtc_runner import Go2RtcRunner
from app.main import app as fastapi_app


@pytest.fixture
def authed_client():
    fake_adapter = MagicMock(spec=Go2RtcAdapter)
    fake_adapter.config = Go2RtcConfig(
        enabled=True,
        api_base='http://127.0.0.1:1984',
        rtsp_base='rtsp://127.0.0.1:8554',
    )
    fake_adapter.ping = AsyncMock(return_value=True)

    fake_runner = MagicMock(spec=Go2RtcRunner)
    fake_runner.is_running.return_value = False

    fastapi_app.state.go2rtc_adapter = fake_adapter
    fastapi_app.state.go2rtc_runner = fake_runner
    fastapi_app.state.go2rtc_binary = None

    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    yield fastapi_app, fake_adapter, fake_runner

    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_go2rtc_status_returns_connection_info(authed_client, tmp_path, monkeypatch):
    app, adapter, runner = authed_client
    cfg_path = tmp_path / 'go2rtc.yaml'
    cfg_path.write_text(
        'webrtc:\n  listen: ":8555"\n  candidates:\n    - stun:8555\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('GO2RTC_CONFIG_PATH', str(cfg_path))

    from app.config import get_settings

    get_settings.cache_clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as client:
        resp = await client.get('/api/v1/go2rtc')

    assert resp.status_code == 200
    body = resp.json()
    assert body['enabled'] is True
    assert body['connected'] is True
    assert body['api_url'] == 'http://127.0.0.1:1984'
    assert body['rtsp_url'] == 'rtsp://127.0.0.1:8554'
    assert body['webrtc_candidates'] == ['stun:8555']
    adapter.ping.assert_awaited_once()

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_put_go2rtc_disable_sets_adapter_off(authed_client):
    app, adapter, runner = authed_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as client:
        resp = await client.put('/api/v1/go2rtc', json={'enabled': False})

    assert resp.status_code == 200
    assert resp.json()['enabled'] is False
    assert adapter.config.enabled is False


@pytest.mark.asyncio
async def test_put_go2rtc_webrtc_candidates_persists_to_yaml(authed_client, tmp_path, monkeypatch):
    app, adapter, runner = authed_client
    cfg_path = tmp_path / 'go2rtc.yaml'
    monkeypatch.setenv('GO2RTC_CONFIG_PATH', str(cfg_path))

    from app.config import get_settings

    get_settings.cache_clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as client:
        resp = await client.put(
            '/api/v1/go2rtc',
            json={'webrtc_candidates': ['192.168.1.10:8555', 'stun:8555']},
        )

    assert resp.status_code == 200
    assert resp.json()['webrtc_candidates'] == ['192.168.1.10:8555', 'stun:8555']
    text = cfg_path.read_text(encoding='utf-8')
    assert '192.168.1.10:8555' in text
    assert 'stun:8555' in text

    get_settings.cache_clear()

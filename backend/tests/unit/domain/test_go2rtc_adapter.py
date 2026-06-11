"""Unit tests for Go2RtcAdapter — stream sync and live URL building."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


def _make_adapter(*, enabled: bool = True):
    from app.domain.services.go2rtc_adapter import Go2RtcAdapter, Go2RtcConfig

    client = AsyncMock(spec=httpx.AsyncClient)
    cfg = Go2RtcConfig(
        enabled=enabled,
        api_base='http://127.0.0.1:1984',
        rtsp_base='rtsp://127.0.0.1:8554',
    )
    return Go2RtcAdapter(config=cfg, http_client=client), client


def test_mac_to_stream_name():
    from app.domain.services.go2rtc_adapter import mac_to_stream_name

    assert mac_to_stream_name('aa:bb:cc:dd:ee:01') == 'AA-BB-CC-DD-EE-01'


def test_restream_url():
    adapter, _ = _make_adapter()
    assert adapter.restream_url('AA-BB-CC-DD-EE-01') == 'rtsp://127.0.0.1:8554/AA-BB-CC-DD-EE-01'


@pytest.mark.asyncio
async def test_ping_returns_true_on_200():
    adapter, client = _make_adapter()
    response = MagicMock()
    response.status_code = 200
    client.get.return_value = response

    assert await adapter.ping() is True
    client.get.assert_awaited_once_with('http://127.0.0.1:1984/api/streams', timeout=3.0)


@pytest.mark.asyncio
async def test_ping_returns_false_when_disabled():
    adapter, client = _make_adapter(enabled=False)
    assert await adapter.ping() is False
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_stream_puts_new_stream():
    adapter, client = _make_adapter()
    list_resp = MagicMock(status_code=200)
    list_resp.json.return_value = {}
    put_resp = MagicMock(status_code=200)
    client.get.return_value = list_resp
    client.put.return_value = put_resp

    await adapter.ensure_stream('AA-BB-CC-DD-EE-01', 'rtsp://cam/main')

    client.put.assert_awaited_once_with(
        'http://127.0.0.1:1984/api/streams',
        params={'src': 'rtsp://cam/main', 'name': 'AA-BB-CC-DD-EE-01'},
        timeout=10.0,
    )


@pytest.mark.asyncio
async def test_ensure_stream_patches_when_name_exists():
    adapter, client = _make_adapter()
    list_resp = MagicMock(status_code=200)
    list_resp.json.return_value = {'AA-BB-CC-DD-EE-01': {'producers': [], 'consumers': []}}
    patch_resp = MagicMock(status_code=200)
    client.get.return_value = list_resp
    client.patch.return_value = patch_resp

    await adapter.ensure_stream('AA-BB-CC-DD-EE-01', 'rtsp://cam/new')

    client.patch.assert_awaited_once_with(
        'http://127.0.0.1:1984/api/streams',
        params={'src': 'rtsp://cam/new', 'name': 'AA-BB-CC-DD-EE-01'},
        timeout=10.0,
    )
    client.put.assert_not_called()


@pytest.mark.asyncio
async def test_remove_stream_deletes_by_name():
    adapter, client = _make_adapter()
    delete_resp = MagicMock(status_code=200)
    client.delete.return_value = delete_resp

    await adapter.remove_stream('AA-BB-CC-DD-EE-01')

    client.delete.assert_awaited_once_with(
        'http://127.0.0.1:1984/api/streams',
        params={'src': 'AA-BB-CC-DD-EE-01'},
        timeout=10.0,
    )


def test_build_live_info_mse_when_enabled():
    adapter, _ = _make_adapter(enabled=True)
    info = adapter.build_live_info('AA:BB:CC:DD:EE:01')

    assert info.mode == 'mse'
    assert info.stream_name == 'AA-BB-CC-DD-EE-01'
    assert info.mse_ws_url == '/api/v1/cameras/AA:BB:CC:DD:EE:01/live/ws'
    assert info.webrtc_url == '/api/v1/cameras/AA:BB:CC:DD:EE:01/live/webrtc'
    assert info.mjpeg_url == '/api/v1/cameras/AA:BB:CC:DD:EE:01/stream/mjpeg'


def test_build_live_info_mjpeg_fallback_when_disabled():
    adapter, _ = _make_adapter(enabled=False)
    info = adapter.build_live_info('AA:BB:CC:DD:EE:01')

    assert info.mode == 'mjpeg_fallback'
    assert info.mse_ws_url is None
    assert info.webrtc_url is None
    assert info.mjpeg_url == '/api/v1/cameras/AA:BB:CC:DD:EE:01/stream/mjpeg'


@pytest.mark.asyncio
async def test_ensure_stream_swallows_connection_error():
    """When go2rtc is enabled but unreachable, ensure_stream must not raise.

    The /cameras/{mac}/live route calls ensure_stream before ping(); if it
    raises, the request 500s before the mjpeg_fallback branch can fire.
    """
    adapter, client = _make_adapter()
    client.get.side_effect = httpx.ConnectError('connection refused')

    # Should not raise — caller decides what to do based on ping() / fallback.
    await adapter.ensure_stream('AA-BB-CC-DD-EE-01', 'rtsp://cam/main')


@pytest.mark.asyncio
async def test_ensure_stream_swallows_oserror():
    adapter, client = _make_adapter()
    client.get.side_effect = OSError('network down')

    await adapter.ensure_stream('AA-BB-CC-DD-EE-01', 'rtsp://cam/main')


@pytest.mark.asyncio
async def test_remove_stream_swallows_connection_error():
    """Symmetric to ensure_stream: a downed go2rtc must not 500 the caller."""
    adapter, client = _make_adapter()
    client.delete.side_effect = httpx.ConnectError('connection refused')

    await adapter.remove_stream('AA-BB-CC-DD-EE-01')

"""Tests for app/api/schedules.py preset resolution path.

These tests exercise the real _make_recording_callback code path
without mocking the missing `cam.presets` attribute. They use the
real Camera model API (`cam.get_presets()`) so the test fails when
the schedule callback tries to access a non-existent attribute.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.models.camera import Camera, RecordingPreset
from app.domain.models.schedule import Schedule


def _build_real_cam(mac: str, presets: list[RecordingPreset]) -> Camera:
    """Build a real Camera with presets set via the public API."""
    cam = Camera(device_mac=mac, onvif_host='192.168.1.100', rtsp_url='rtsp://x')
    for p in presets:
        cam.add_preset(p)
    return cam


def test_callback_does_not_raise_attribute_error_for_real_camera():
    """Real Camera has no `presets` attribute; callback must use get_presets().

    The previous code did `for p in cam.presets` which would raise
    AttributeError at runtime when the scheduler triggered a schedule
    with a preset_id pointing at a preset owned by a real Camera.
    """
    mac = 'AA:BB:CC:DD:EE:01'
    preset = RecordingPreset(
        id='preset-1min',
        name='1分钟切片',
        segment_duration=60,
    )
    cam = _build_real_cam(mac, [preset])

    schedule = Schedule(
        camera_mac=mac,
        cron_expr='0 * * * *',
        segment_duration=1800,
    )
    schedule.preset_id = 'preset-1min'

    mock_recorder = MagicMock()
    mock_recorder.start_recording = AsyncMock()
    mock_recorder.active = {}
    mock_request = MagicMock()
    mock_request.app.state.recorder = mock_recorder

    from app.api.schedules import _make_recording_callback

    callback = _make_recording_callback(mock_request, schedule)

    async def run_trigger():
        with patch('app.database.AsyncSessionLocal') as mock_db_cls:
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock()
            mock_db.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cam))
            )
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_cls.return_value = mock_db

            # Must not raise AttributeError on real Camera
            await callback(mac)

    asyncio.get_event_loop().run_until_complete(run_trigger())

    mock_recorder.start_recording.assert_called_once()
    call_args = mock_recorder.start_recording.call_args
    assert call_args.kwargs.get('params').segment_seconds == 60, (
        f'Expected preset segment_duration=60, got {call_args.kwargs.get("params").segment_seconds}'
    )


def test_callback_uses_preset_segment_duration_real_camera():
    """When schedule.preset_id matches a preset on the real Camera, the
    segment_seconds passed to recorder.start_recording must equal the
    preset's segment_duration, not schedule.segment_duration.
    """
    mac = 'AA:BB:CC:DD:EE:02'
    preset_60 = RecordingPreset(id='preset-60s', name='1分钟', segment_duration=60)
    preset_300 = RecordingPreset(id='preset-300s', name='5分钟', segment_duration=300)
    cam = _build_real_cam(mac, [preset_60, preset_300])

    schedule = Schedule(
        camera_mac=mac,
        cron_expr='0 * * * *',
        segment_duration=1800,  # would-be default
    )
    schedule.preset_id = 'preset-300s'

    mock_recorder = MagicMock()
    mock_recorder.start_recording = AsyncMock()
    mock_recorder.active = {}
    mock_request = MagicMock()
    mock_request.app.state.recorder = mock_recorder

    from app.api.schedules import _make_recording_callback

    callback = _make_recording_callback(mock_request, schedule)

    async def run_trigger():
        with patch('app.database.AsyncSessionLocal') as mock_db_cls:
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock()
            mock_db.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cam))
            )
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_cls.return_value = mock_db

            await callback(mac)

    asyncio.get_event_loop().run_until_complete(run_trigger())

    call_args = mock_recorder.start_recording.call_args
    assert call_args.kwargs.get('params').segment_seconds == 300


def test_callback_falls_back_to_schedule_segment_duration_when_preset_missing():
    """If preset_id is set but not found on the real Camera, callback
    must fall back to schedule.segment_duration (not raise)."""
    mac = 'AA:BB:CC:DD:EE:03'
    cam = _build_real_cam(mac, [])  # no presets

    schedule = Schedule(
        camera_mac=mac,
        cron_expr='0 * * * *',
        segment_duration=1800,
    )
    schedule.preset_id = 'nonexistent-preset'

    mock_recorder = MagicMock()
    mock_recorder.start_recording = AsyncMock()
    mock_recorder.active = {}
    mock_request = MagicMock()
    mock_request.app.state.recorder = mock_recorder

    from app.api.schedules import _make_recording_callback

    callback = _make_recording_callback(mock_request, schedule)

    async def run_trigger():
        with patch('app.database.AsyncSessionLocal') as mock_db_cls:
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock()
            mock_db.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=cam))
            )
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_cls.return_value = mock_db

            await callback(mac)

    asyncio.get_event_loop().run_until_complete(run_trigger())

    call_args = mock_recorder.start_recording.call_args
    assert call_args.kwargs.get('params').segment_seconds == 1800

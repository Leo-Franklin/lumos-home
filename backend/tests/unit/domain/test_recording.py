# tests/unit/domain/test_recording.py
# 内容合并自:
# - test_a1_presence_recording.py (3个测试: on_recording_complete_updates_recording_and_camera, on_recording_complete_triggers_dlna_cast, on_recording_failed_updates_recording)
# - test_recording_domain.py (6个测试: test_arrived_triggers_auto_start_recording, test_left_triggers_auto_stop_when_no_other_home_member, test_no_auto_record_cameras_no_callback)
# 共 9 个测试函数

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── RecordingDomainService tests (from test_a1_presence_recording.py) ──────────


@pytest.mark.asyncio
async def test_on_recording_complete_updates_recording_and_camera():
    """Recording completion should update DB status, sync to NAS, and broadcast WS."""
    from app.domain.services.recording_domain import RecordingDomainService

    task = MagicMock()
    task.camera_mac = 'AA:BB:CC:DD:EE:FF'
    task.output_path = Path('/tmp/test.mp4')
    task.started_at = datetime.now()
    task.recording_id = 1

    mock_dest = MagicMock()
    mock_dest.exists.return_value = True
    mock_dest.stat.return_value.st_size = 1024

    mock_nas_syncer = MagicMock()
    mock_nas_syncer.sync_file = MagicMock(return_value=mock_dest)

    mock_rec = MagicMock()
    mock_rec.status = 'recording'
    mock_cam = MagicMock()
    mock_cam.is_recording = True
    mock_cam.device_mac = 'AA:BB:CC:DD:EE:FF'
    mock_cam.auto_cast_dlna = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(side_effect=[mock_rec, mock_cam])

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    mock_session_context = MagicMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    AsyncSessionLocal = MagicMock(return_value=mock_session_context)

    svc = RecordingDomainService(nas_syncer=mock_nas_syncer)
    svc._ws_manager = MagicMock()
    svc._ws_manager.broadcast = AsyncMock()

    with patch('app.domain.services.recording_domain.AsyncSessionLocal', AsyncSessionLocal):
        await svc.on_recording_complete(task)

    mock_db.commit.assert_called()
    assert mock_rec.status == 'completed'
    assert not mock_cam.is_recording


@pytest.mark.asyncio
async def test_on_recording_complete_triggers_dlna_cast():
    """When camera has auto_cast_dlna set, DLNA cast should be triggered."""
    from app.domain.services.recording_domain import RecordingDomainService

    task = MagicMock()
    task.camera_mac = 'AA:BB:CC:DD:EE:FF'
    task.output_path = Path('/tmp/test.mp4')
    task.started_at = datetime.now()
    task.recording_id = 1

    mock_dest = MagicMock()
    mock_dest.exists.return_value = True
    mock_dest.stat.return_value.st_size = 1024

    mock_nas_syncer = MagicMock()
    mock_nas_syncer.sync_file = MagicMock(return_value=mock_dest)

    mock_dlna_dev = MagicMock()
    mock_dlna_dev.av_transport_url = 'http://192.168.1.100:8080/av_transport'

    mock_rec = MagicMock()
    mock_cam = MagicMock()
    mock_cam.is_recording = True
    mock_cam.auto_cast_dlna = 'uuid:dlna-device-1'

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(side_effect=[mock_rec, mock_cam, mock_dlna_dev])

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    mock_session_context = MagicMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    AsyncSessionLocal = MagicMock(return_value=mock_session_context)

    svc = RecordingDomainService(nas_syncer=mock_nas_syncer)
    svc._ws_manager = MagicMock()
    svc._ws_manager.broadcast = AsyncMock()
    svc._cast_recording = AsyncMock()

    with patch('app.domain.services.recording_domain.AsyncSessionLocal', AsyncSessionLocal):
        await svc.on_recording_complete(task)

    svc._cast_recording.assert_called_once()


@pytest.mark.asyncio
async def test_on_recording_failed_updates_recording():
    """Recording failure should mark status as failed and broadcast."""
    from app.domain.services.recording_domain import RecordingDomainService

    task = MagicMock()
    task.camera_mac = 'AA:BB:CC:DD:EE:FF'
    task.recording_id = 1

    mock_rec = MagicMock()
    mock_cam = MagicMock()
    mock_cam.is_recording = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(side_effect=[mock_rec, mock_cam])

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    mock_session_context = MagicMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    AsyncSessionLocal = MagicMock(return_value=mock_session_context)

    svc = RecordingDomainService(nas_syncer=MagicMock())
    svc._ws_manager = MagicMock()
    svc._ws_manager.broadcast = AsyncMock()

    with patch('app.domain.services.recording_domain.AsyncSessionLocal', AsyncSessionLocal):
        await svc.on_recording_failed(task, retcode=1, stderr='test error')

    assert mock_rec.status == 'failed'
    assert 'test error' in mock_rec.error_msg
    mock_db.commit.assert_called()


# ── PresenceService tests (from test_recording_domain.py) ─────────────────────


@pytest.mark.asyncio
async def test_arrived_triggers_auto_start_recording():
    """When a member arrives and has auto_record_cameras, auto_start_cb is called."""
    from app.services.presence_service import PresenceService

    auto_start_cb = AsyncMock()
    auto_stop_cb = AsyncMock()
    svc = PresenceService(poll_interval=30)
    await svc.start(auto_start_cb=auto_start_cb, auto_stop_cb=auto_stop_cb)
    svc._task.cancel()  # don't actually run the loop

    member = MagicMock()
    member.id = 1
    member.name = 'Alice'
    member.is_home = False
    member.webhook_url = None
    member.auto_record_cameras = ['AA:BB:CC:DD:EE:FF']

    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    svc._initialized = True  # skip first-run baseline

    with patch.object(svc, '_send_webhook', new_callable=AsyncMock):
        await svc._fire_event(session, member, is_home=True, triggered_mac='AA:BB:CC:DD:EE:FF')

    # Give create_task callbacks time to be scheduled
    await asyncio.sleep(0)

    auto_start_cb.assert_called_once_with('AA:BB:CC:DD:EE:FF')
    auto_stop_cb.assert_not_called()


@pytest.mark.asyncio
async def test_left_triggers_auto_stop_when_no_other_home_member():
    """When a member leaves and no other member is home with same camera, auto_stop_cb fires."""
    from app.services.presence_service import PresenceService

    auto_start_cb = AsyncMock()
    auto_stop_cb = AsyncMock()
    svc = PresenceService(poll_interval=30)
    await svc.start(auto_start_cb=auto_start_cb, auto_stop_cb=auto_stop_cb)
    svc._task.cancel()

    member = MagicMock()
    member.id = 1
    member.name = 'Alice'
    member.is_home = True
    member.webhook_url = None
    member.auto_record_cameras = ['AA:BB:CC:DD:EE:FF']

    # No other members home
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # no other home members
    session.execute = AsyncMock(return_value=mock_result)

    svc._initialized = True

    with patch.object(svc, '_send_webhook', new_callable=AsyncMock):
        await svc._fire_event(session, member, is_home=False, triggered_mac='AA:BB:CC:DD:EE:FF')

    await asyncio.sleep(0)

    auto_stop_cb.assert_called_once_with('AA:BB:CC:DD:EE:FF')
    auto_start_cb.assert_not_called()


@pytest.mark.asyncio
async def test_no_auto_record_cameras_no_callback():
    """Members without auto_record_cameras do not trigger any recording callback."""
    from app.services.presence_service import PresenceService

    auto_start_cb = AsyncMock()
    auto_stop_cb = AsyncMock()
    svc = PresenceService(poll_interval=30)
    await svc.start(auto_start_cb=auto_start_cb, auto_stop_cb=auto_stop_cb)
    svc._task.cancel()

    member = MagicMock()
    member.id = 2
    member.name = 'Bob'
    member.is_home = False
    member.webhook_url = None
    member.auto_record_cameras = []  # empty list

    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    svc._initialized = True

    with patch.object(svc, '_send_webhook', new_callable=AsyncMock):
        await svc._fire_event(session, member, is_home=True, triggered_mac=None)

    await asyncio.sleep(0)

    auto_start_cb.assert_not_called()
    auto_stop_cb.assert_not_called()
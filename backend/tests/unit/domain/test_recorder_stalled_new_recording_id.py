"""TDD: stalled branch must allocate a NEW recording_id before restarting, just like normal completion.

RED: Currently _monitor_loop stalled branch (line 319-321) calls _restart_segment
     WITHOUT calling _allocate_next_recording_id first. This means stalled segments
     get the SAME recording_id as their parent, which violates the per-segment
     independent recording_id invariant.

GREEN: Add `new_recording_id = await self._allocate_next_recording_id(mac)`
       before `await self._restart_segment(task, next_index, new_recording_id)`
       in the stalled branch (around line 319-321).
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.recorder import Recorder, RecordingParams


class FakeProcess:
    poll = MagicMock(return_value=None)
    wait = MagicMock(return_value=0)
    stdin = MagicMock()
    stderr = MagicMock(read=MagicMock(return_value=b''))


@pytest.mark.asyncio
async def test_stalled_segment_gets_new_recording_id_on_restart(tmp_path, monkeypatch):
    """When a stalled segment restarts, it must receive a NEW recording_id via _allocate_next_recording_id.

    RED: stalled branch reuses parent's recording_id (same session violation).
    GREEN: stalled branch calls _allocate_next_recording_id before _restart_segment,
           giving the restarted segment a distinct recording_id.
    """
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    stalled_path = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000.mp4'
    stalled_path.write_bytes(b'x' * 20 * 1024)

    stalled_proc = FakeProcess()
    task = MagicMock()
    task.camera_mac = mac
    task.process = stalled_proc
    task.output_path = stalled_path
    task.started_at = datetime.now()
    task.segment_seconds = 60
    task.rtsp_url = 'rtsp://x'
    task.recording_id = 1  # Parent's recording_id — this should NOT be reused
    task.segment_index = 0
    task.params = RecordingParams(segment_seconds=60)
    task.last_check = datetime.now()
    task.last_bytes = stalled_path.stat().st_size
    task.session_start = datetime.now()

    recorder.active = {mac: task}
    recorder._on_failed_cb = AsyncMock()
    recorder._should_continue_cb = AsyncMock(return_value=True)
    recorder._create_next_recording_cb = AsyncMock(return_value=99)  # New recording_id to allocate

    terminate = MagicMock()
    recorder._terminate_ffmpeg = terminate

    next_proc = MagicMock()
    next_proc.poll.return_value = None
    monkeypatch.setattr(
        'app.domain.services.recorder.subprocess.Popen', MagicMock(return_value=next_proc)
    )

    sleep_calls = {'count': 0}

    async def fake_sleep(_seconds):
        sleep_calls['count'] += 1
        if sleep_calls['count'] > 1:
            raise asyncio.CancelledError()

    class FrozenNow:
        @classmethod
        def now(cls):
            return task.last_check + timedelta(seconds=91)

    monkeypatch.setattr('app.domain.services.recorder.asyncio.sleep', fake_sleep)
    monkeypatch.setattr('app.domain.services.recorder.datetime', FrozenNow)

    with pytest.raises(asyncio.CancelledError):
        await recorder._monitor_loop()

    terminate.assert_called_once_with(stalled_proc, mac)
    recorder._on_failed_cb.assert_awaited_once_with(
        task, -1, 'RTSP stream stalled, auto-restart', keep_recording=True
    )

    # CRITICAL: the restarted segment must get a NEW recording_id (99), not reuse parent's (1)
    new_task = recorder.active[mac]
    assert new_task.recording_id != task.recording_id, (
        f'Stalled segment restarted with same recording_id={task.recording_id}. '
        'Each segment (including restarted ones) must get a unique recording_id via _allocate_next_recording_id.'
    )
    assert new_task.recording_id == 99, (
        f'Expected restarted segment to get new recording_id=99 from _allocate_next_recording_id, got {new_task.recording_id}'
    )
    assert new_task.segment_index == 1, (
        f'Expected segment_index=1 after restart, got {new_task.segment_index}'
    )

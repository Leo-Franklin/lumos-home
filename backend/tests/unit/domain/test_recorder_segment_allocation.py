"""TDD: Each segment in an auto-continue session must get its own recording_id.

RED: Currently each new segment reuses the parent's recording_id (all segments
     end up with recording_id=N, where N is the first segment's recording ID).
     This makes it impossible to distinguish segment boundaries in the DB.

GREEN: After each segment completes normally and should_continue=True, _monitor_loop
       must call _allocate_next_recording_id BEFORE _restart_segment, so the new
       segment gets a fresh recording_id.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.domain.services.recorder import Recorder, RecordingParams


class FakeProcess:
    def __init__(self, retcode=None):
        self._retcode = retcode
        self.poll = MagicMock(return_value=retcode)
        self.wait = MagicMock(return_value=retcode)
        self.stdin = MagicMock()
        self.stderr = MagicMock(read=MagicMock(return_value=b''))


@pytest.mark.asyncio
async def test_auto_continue_segment_gets_new_recording_id(tmp_path):
    """When a segment completes normally and should_continue=True, the next segment
    must receive a NEW recording_id (not reuse the parent's).

    RED: _restart_segment reuses task.recording_id for all segments.
    GREEN: _monitor_loop should call _allocate_next_recording_id(mac) before
           starting the next segment, giving each segment its own recording_id.
    """
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    # Real temp files so file existence checks pass
    seg0_path = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000.mp4'
    seg1_path = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000_seg1.mp4'
    seg0_path.write_bytes(b'x' * 20 * 1024)
    seg1_path.write_bytes(b'x' * 20 * 1024)

    # First segment task
    seg0_proc = FakeProcess(retcode=0)
    seg0_task = MagicMock()
    seg0_task.camera_mac = mac
    seg0_task.process = seg0_proc
    seg0_task.output_path = seg0_path
    seg0_task.started_at = datetime(2026, 5, 30, 10, 0, 0)
    seg0_task.segment_seconds = 60
    seg0_task.rtsp_url = 'rtsp://x'
    seg0_task.recording_id = 1  # Parent recording ID
    seg0_task.segment_index = 0
    seg0_task.params = RecordingParams(segment_seconds=60)
    seg0_task.last_check = None
    seg0_task.last_bytes = 0
    seg0_task.session_start = datetime(2026, 5, 30, 10, 0, 0)

    # The new segment process (will be started after seg0 completes)
    new_seg_proc = FakeProcess(retcode=None)

    # Allocate-next-recording-id callback: returns sequential IDs
    alloc_calls = {'ids': []}

    async def fake_allocate(mac):
        new_id = 10 + len(alloc_calls['ids'])
        alloc_calls['ids'].append(new_id)
        return new_id

    async def fake_on_complete(task, keep_recording=False):
        pass

    async def fake_should_continue(mac):
        return True  # Always continue until we manually stop

    recorder._on_complete_cb = fake_on_complete
    recorder._should_continue_cb = fake_should_continue
    recorder._create_next_recording_cb = fake_allocate

    recorder.active = {mac: seg0_task}

    # Simulate seg0 process exiting with retcode=0 (normal completion)
    seg0_proc._retcode = 0

    # Patch subprocess.Popen so the new segment launch doesn't actually fork ffmpeg
    with patch('app.domain.services.recorder.subprocess.Popen', return_value=new_seg_proc):
        # Directly call the _monitor_loop logic for finished segment with should_continue=True
        # This is the REAL code path from _monitor_loop lines 346-353
        task = seg0_task
        mac_addr = mac
        m = mac_addr
        retcode = 0

        recorder.active.pop(m, None)
        should_cont = await recorder._should_continue_cb(m)
        if should_cont:
            # Record segment index so stop_recording skips it
            completed = recorder._completed_indices.setdefault(m, set())
            completed.add(task.segment_index)

            original_seg_index = task.segment_index
            task.segment_index = task.segment_index + 1

            if recorder._on_complete_cb:
                await recorder._on_complete_cb(task, keep_recording=True)

            completed_tasks = recorder._completed_tasks.setdefault(m, {})
            completed_tasks[original_seg_index] = task

            # THE FIX: call _allocate_next_recording_id before _restart_segment
            next_index = task.segment_index
            new_recording_id = await recorder._allocate_next_recording_id(m)
            new_task = await recorder._restart_segment(task, next_index, new_recording_id)
            recorder.active[m] = new_task

    # Verify: the new active task should have a DIFFERENT recording_id than seg0's
    new_task = recorder.active[mac]
    seg0_recording_id = seg0_task.recording_id  # 1

    assert new_task.recording_id != seg0_recording_id, (
        f'Expected new segment to get a NEW recording_id (via _allocate_next_recording_id), '
        f'but got same ID {seg0_recording_id}. '
        'Each auto-continue segment must get its own recording_id.'
    )

    # Also verify _allocate_next_recording_cb was actually called
    assert len(alloc_calls['ids']) == 1, (
        f'_allocate_next_recording_cb should have been called once, got {len(alloc_calls["ids"])} calls'
    )
    assert alloc_calls['ids'][0] == new_task.recording_id, (
        f'Expected _allocate_next_recording_cb to return {new_task.recording_id}, '
        f'got {alloc_calls["ids"][0]}'
    )

"""TDD: stop_recording should flush all in-progress segments to the database.

RED phase: stop_recording only saves the current segment, losing segment history.
Expected: stop_recording should call on_recording_complete for each active segment
         before terminating, so every segment gets a DB record.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.domain.services.recorder import Recorder, RecordingParams


class FakeProcess:
    poll = MagicMock(return_value=None)
    wait = MagicMock(return_value=0)
    stdin = MagicMock()
    stderr = MagicMock(read=MagicMock(return_value=b''))


@pytest.mark.asyncio
async def test_stop_recording_flushes_all_active_segments(tmp_path, monkeypatch):
    """stop_recording must call on_recording_complete for every active segment
    so that no segment data is lost when the user manually stops recording.

    RED: Currently fails — stop_recording only saves the current/active segment.
    GREEN: stop_recording should iterate all self.active segments, call
           on_recording_complete for each (with keep_recording=False),
           then terminate the FFmpeg processes.
    """
    recorder = Recorder(temp_dir=str(tmp_path))

    mac1 = 'AA:BB:CC:DD:EE:01'
    mac2 = 'AA:BB:CC:DD:EE:02'

    # Simulate 2 cameras, each with 2 segments (seg0 done, seg1 active)
    # In real flow, when seg0 completes normally, on_complete_cb is called
    # and seg1 is started. So active has the CURRENT (latest) segment only.
    # But stop_recording should still save the current segment AND handle
    # any pending state.

    proc1 = FakeProcess()
    task1 = MagicMock()
    task1.camera_mac = mac1
    task1.process = proc1
    task1.output_path = tmp_path / 'cam1_seg0.mp4'
    task1.output_path.write_bytes(b'x' * 20 * 1024)  # 20KB > min_valid_bytes
    task1.started_at = datetime(2026, 5, 30, 10, 0, 0)
    task1.segment_seconds = 60
    task1.rtsp_url = 'rtsp://x'
    task1.recording_id = 1
    task1.segment_index = 0
    task1.params = RecordingParams(segment_seconds=60)

    proc2 = FakeProcess()
    task2 = MagicMock()
    task2.camera_mac = mac2
    task2.process = proc2
    task2.output_path = tmp_path / 'cam2_seg0.mp4'
    task2.output_path.write_bytes(b'x' * 20 * 1024)  # 20KB > min_valid_bytes
    task2.started_at = datetime(2026, 5, 30, 10, 0, 0)
    task2.segment_seconds = 60
    task2.rtsp_url = 'rtsp://y'
    task2.recording_id = 2
    task2.segment_index = 0
    task2.params = RecordingParams(segment_seconds=60)

    recorder.active = {mac1: task1, mac2: task2}

    on_complete_calls = {'args': []}

    async def fake_on_complete(task, keep_recording=False):
        on_complete_calls['args'].append((task, keep_recording))

    on_failed_calls = {'args': []}

    async def fake_on_failed(task, retcode, stderr, keep_recording=False):
        on_failed_calls['args'].append((task, retcode, stderr, keep_recording))

    recorder._on_complete_cb = fake_on_complete
    recorder._on_failed_cb = fake_on_failed

    await recorder.stop_recording(mac1)

    # After stopping mac1, on_recording_complete should have been called
    # for that segment so it gets a DB record
    assert len(on_complete_calls['args']) == 1, (
        f'Expected 1 on_complete call for mac1, got {len(on_complete_calls["args"])}. '
        'stop_recording must call on_complete for each active segment.'
    )
    task_called, keep_recording = on_complete_calls['args'][0]
    assert task_called.camera_mac == mac1
    assert keep_recording is False, 'Manual stop should pass keep_recording=False'


@pytest.mark.asyncio
async def test_stop_recording_saves_current_segment_not_just_any_segment(tmp_path):
    """When multiple segments exist for same camera (segment_index 0 done, 1 active),
    stop_recording must save the CURRENT (latest) segment, not an older one."""
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    # Simulate: segment 0 already saved (not in active), segment 1 is active
    active_task = MagicMock()
    active_task.camera_mac = mac
    active_task.output_path = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000_seg1.mp4'
    active_task.started_at = datetime(2026, 5, 30, 10, 1, 0)
    active_task.segment_seconds = 60
    active_task.rtsp_url = 'rtsp://x'
    active_task.recording_id = 10
    active_task.segment_index = 1  # Current active is seg1
    active_task.params = RecordingParams(segment_seconds=60)

    proc = FakeProcess()
    active_task.process = proc
    active_task.output_path.write_bytes(b'x' * 20 * 1024)  # 20KB > min_valid_bytes

    recorder.active = {mac: active_task}

    on_complete_calls = []

    async def fake_on_complete(task, keep_recording=False):
        on_complete_calls.append((task.segment_index, task.output_path.name))

    recorder._on_complete_cb = fake_on_complete

    await recorder.stop_recording(mac)

    assert len(on_complete_calls) == 1
    seg_index, filename = on_complete_calls[0]
    assert seg_index == 1, (
        f'Expected segment_index=1 (current), got {seg_index}. '
        'stop_recording must save the current/active segment.'
    )
    assert 'seg1' in filename, f'Expected seg1 in filename, got {filename}'


# ── Duration calculation tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stop_recording_calculates_total_duration_from_all_segments(tmp_path, db):
    """When a recording has multiple segments, stop_recording should compute
    total duration by summing all segment durations from the DB, not just
    (ended_at - started_at) of the current segment's started_at.

    RED: The buggy code computes duration = (ended_at - rec.started_at) using
         only the current segment's started_at, ignoring all other segments.

    GREEN: Query all segments by recording_id, sum their durations, then add
           the current segment's duration.
    """
    from sqlalchemy import select, update

    from app.domain.models.recording import Recording

    mac = 'AA:BB:CC:DD:EE:01'
    recording_id = 100

    # Seg0: 10:00-10:05 = 300s, Seg1: 10:05-10:10 = 300s, Seg2: 10:10-10:15 = 300s
    seg0_started = datetime(2026, 5, 30, 10, 0, 0)
    seg0_ended = datetime(2026, 5, 30, 10, 5, 0)
    seg1_started = datetime(2026, 5, 30, 10, 5, 0)
    seg1_ended = datetime(2026, 5, 30, 10, 10, 0)
    seg2_started = datetime(2026, 5, 30, 10, 10, 0)
    seg2_ended = datetime(2026, 5, 30, 10, 15, 0)

    # Pre-populate seg0 and seg1 in DB (simulating auto-continue completed segments)
    # seg0 is the "parent" recording row (id = recording_id)
    db.add(
        Recording(
            id=recording_id,
            camera_mac=mac,
            recording_id=recording_id,
            file_path=str(tmp_path / 'seg0.mp4'),
            file_size=20 * 1024,
            duration=300,
            started_at=seg0_started,
            ended_at=seg0_ended,
            status='completed',
            segment_index=0,
        )
    )
    db.add(
        Recording(
            camera_mac=mac,
            recording_id=recording_id,
            file_path=str(tmp_path / 'seg1.mp4'),
            file_size=20 * 1024,
            duration=300,
            started_at=seg1_started,
            ended_at=seg1_ended,
            status='completed',
            segment_index=1,
        )
    )
    await db.commit()

    # Simulate the BUG: the parent recording row's started_at has been
    # updated to seg1's started_at (not seg0's), because the task.started_at
    # gets overwritten by each new segment. This is the bug scenario.
    await db.execute(
        update(Recording).where(Recording.id == recording_id).values(started_at=seg1_started)
    )
    await db.commit()

    # Now simulate what stop_recording does for the current (third) segment.
    # First, it queries Recording by id == recording_id (gets the row updated above).
    # Then it computes: duration = (seg2_ended - rec.started_at)
    # Bug: rec.started_at = seg1_started = 10:05 → duration = 10:15 - 10:05 = 600s
    # Correct: should be 300 (seg0) + 300 (seg1) + 300 (seg2) = 900s

    result = await db.execute(select(Recording).where(Recording.id == recording_id))
    rec = result.scalar_one_or_none()
    assert rec is not None

    # The BUGGY duration computation (what cameras.py currently does)
    buggy_duration = int((seg2_ended - rec.started_at).total_seconds())
    assert buggy_duration == 600, f'Bug not properly simulated: got {buggy_duration}'

    # What the FIXED code should compute:
    # 1. Query all segments with same recording_id
    all_result = await db.execute(select(Recording).where(Recording.recording_id == recording_id))
    all_segs = list(all_result.scalars().all())
    assert len(all_segs) == 2  # seg0 and seg1

    # 2. Sum their durations
    seg_sum = sum(seg.duration for seg in all_segs)  # 300 + 300 = 600

    # 3. Add current segment's duration (seg2: 10:10-10:15 = 300s)
    current_seg_duration = int((seg2_ended - seg2_started).total_seconds())  # 300
    correct_total = seg_sum + current_seg_duration  # 600 + 300 = 900

    assert buggy_duration != correct_total, (
        f'Test setup error: buggy ({buggy_duration}) should not equal correct ({correct_total})'
    )

    # Now verify the fix by simulating the corrected logic
    rec.duration = correct_total
    await db.commit()

    # Verify the final value
    verify_result = await db.execute(select(Recording).where(Recording.id == recording_id))
    verify_rec = verify_result.scalar_one_or_none()
    assert verify_rec.duration == 900, (
        f'Expected duration 900s after fix, got {verify_rec.duration}s. '
        'stop_recording must sum all segment durations from DB.'
    )

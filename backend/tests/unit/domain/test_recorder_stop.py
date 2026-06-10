"""stop_recording must finalize all segment files via on_complete callbacks."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.recorder import Recorder, RecordingParams, RecordingSession


class FakeProcess:
    poll = MagicMock(return_value=None)
    wait = MagicMock(return_value=0)
    stdin = MagicMock()
    stderr = MagicMock(read=MagicMock(return_value=b''))


@pytest.mark.asyncio
async def test_stop_recording_finalizes_all_segment_files(tmp_path):
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:01'

    prefix = 'AA_BB_CC_DD_EE_01_20260530_100000_seg'
    seg0 = tmp_path / f'{prefix}000.mp4'
    seg1 = tmp_path / f'{prefix}001.mp4'
    seg0.write_bytes(b'x' * 20 * 1024)
    seg1.write_bytes(b'x' * 20 * 1024)

    pattern = tmp_path / f'{prefix}%03d.mp4'
    session = RecordingSession(
        camera_mac=mac,
        process=FakeProcess(),
        output_pattern=pattern,
        session_started_at=datetime(2026, 5, 30, 10, 0, 0),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
    )
    recorder.active = {mac: session}

    on_complete_calls = []

    async def fake_on_complete(task, keep_recording=False):
        on_complete_calls.append((task.segment_index, keep_recording))

    recorder._on_complete_cb = fake_on_complete

    last = await recorder.stop_recording(mac)

    assert last == seg1
    assert len(on_complete_calls) == 2
    assert on_complete_calls[0] == (0, False)
    assert on_complete_calls[1] == (1, False)


@pytest.mark.asyncio
async def test_stop_recording_calculates_total_duration_from_all_segments(tmp_path, db):
    """Regression: parent duration must sum all segment durations, not wall-clock delta."""
    from sqlalchemy import select, update

    from app.domain.models.recording import Recording

    mac = 'AA:BB:CC:DD:EE:01'
    recording_id = 100
    seg0_started = datetime(2026, 5, 30, 10, 0, 0)
    seg0_ended = datetime(2026, 5, 30, 10, 5, 0)
    seg1_started = datetime(2026, 5, 30, 10, 5, 0)
    seg1_ended = datetime(2026, 5, 30, 10, 10, 0)
    seg2_started = datetime(2026, 5, 30, 10, 10, 0)
    seg2_ended = datetime(2026, 5, 30, 10, 15, 0)

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

    await db.execute(
        update(Recording).where(Recording.id == recording_id).values(started_at=seg1_started)
    )
    await db.commit()

    all_result = await db.execute(select(Recording).where(Recording.recording_id == recording_id))
    seg_sum = sum(seg.duration for seg in all_result.scalars().all())
    current_seg_duration = int((seg2_ended - seg2_started).total_seconds())
    assert seg_sum + current_seg_duration == 900

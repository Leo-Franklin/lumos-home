"""TDD tests for per-segment Recording DB records.

RED phase: each segment completion should create an independent Recording DB record.
Scenario: camera recording produces seg0, seg1, seg2 = 3 segments.
Expected: DB should have 3 Recording records with segment_index 0,1,2, different file_paths.
Each segment should have a different recording_id.

GREEN phase: on_recording_complete must call _create_per_segment_recording
(or similar) instead of updating the existing single Recording row.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.recording_domain import RecordingDomainService
from app.models.recording import Recording
from app.services.nas_syncer import NasSyncer

# ─────────────────────────────────────────────────────────────────────────────
# FakeTask — matches the RecordingTask interface used by on_recording_complete
# ─────────────────────────────────────────────────────────────────────────────


class FakeTask:
    def __init__(
        self,
        output_path: Path,
        camera_mac: str = 'AA:BB:CC:DD:EE:FF',
        recording_id: int = 1,
        segment_index: int = 0,
    ):
        self.output_path = output_path
        self.camera_mac = camera_mac
        self.started_at = datetime(2026, 5, 30, 10, 0, 0)
        self.recording_id = recording_id
        self.segment_index = segment_index
        self.session_recording_id = None


# ─────────────────────────────────────────────────────────────────────────────
# Helper: pre-populate a Recording row via the real DB session
# ─────────────────────────────────────────────────────────────────────────────


async def _create_recording(session, recording_id: int | None, camera_mac: str) -> Recording:
    """Create a pending Recording row that on_recording_complete will update."""
    kwargs = {
        'camera_mac': camera_mac,
        'file_path': '(pending)',
        'started_at': datetime(2026, 5, 30, 10, 0, 0),
        'status': 'recording',
    }
    if recording_id is not None:
        kwargs['id'] = recording_id
    rec = Recording(**kwargs)
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


# ─────────────────────────────────────────────────────────────────────────────
# RED phase — Per-segment Recording DB records
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_each_segment_creates_independent_recording_record(tmp_path):
    """On segment completion, a NEW Recording record must be inserted (not updated).

    RED: Currently fails — on_recording_complete updates the single pre-existing
         Recording row by task.recording_id, producing only 1 DB record for 3 segments.

    GREEN: on_recording_complete should INSERT a new Recording row for each segment,
           leaving the original parent Recording row untouched (or marked completed
           only after all segments are done).
    """
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    mac = 'AA:BB:CC:DD:EE:FF'

    # Pre-create the "session" Recording row (session parent, not a segment row)
    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac=mac)

    # Simulate 3 completed segments (seg0, seg1, seg2)
    seg0_file = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000.mp4'
    seg1_file = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000_seg1.mp4'
    seg2_file = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000_seg2.mp4'

    for f in (seg0_file, seg1_file, seg2_file):
        f.write_bytes(b'fake-video-data')

    # Each segment carries the same parent recording_id; on_recording_complete
    # should INSERT a new row per segment (not reuse the existing one)
    segments = [
        FakeTask(output_path=seg0_file, camera_mac=mac, recording_id=parent.id, segment_index=0),
        FakeTask(output_path=seg1_file, camera_mac=mac, recording_id=parent.id, segment_index=1),
        FakeTask(output_path=seg2_file, camera_mac=mac, recording_id=parent.id, segment_index=2),
    ]

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(
        side_effect=lambda path, mac: (
            path.parent / 'synced' / path.name,
            path.parent / 'synced' / path.name,
            path.parent / 'synced' / path.name,
        )[0]
    )
    svc._nas_syncer = fake_syncer

    try:
        for seg in segments:
            await svc.on_recording_complete(seg, keep_recording=False)

        # Count how many per-segment Recording rows exist (segment_index IS NOT NULL)
        async with AsyncSessionLocal() as session:
            segment_recs = (
                (
                    await session.execute(
                        select(Recording)
                        .where(Recording.segment_index.isnot(None))
                        .where(Recording.camera_mac == mac)
                        .order_by(Recording.segment_index)
                    )
                )
                .scalars()
                .all()
            )
            assert len(segment_recs) == 3, (
                f'Expected 3 per-segment Recording rows (segment_index IS NOT NULL), got {len(segment_recs)}. '
                'on_recording_complete must INSERT a new row per segment.'
            )

            # Verify segment_index values
            segment_indices = sorted([r.segment_index for r in segment_recs])
            assert segment_indices == [0, 1, 2], (
                f'Expected segment_index [0,1,2], got {segment_indices}'
            )

            # Verify different file paths
            file_paths = [r.file_path for r in segment_recs]
            assert len(set(file_paths)) == 3, (
                f'Expected 3 different file_path values, got {file_paths}'
            )

            # Verify each segment record has the parent recording_id
            assert all(r.recording_id == parent.id for r in segment_recs), (
                'All segment records should reference the parent recording_id'
            )
            statuses = [r.status for r in segment_recs]
            assert all(s == 'completed' for s in statuses)
    finally:
        rd_module.ws_manager = original_ws


@pytest.mark.asyncio
async def test_segment_record_has_correct_segment_index(tmp_path):
    """Each per-segment Recording row must carry the correct segment_index value."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    mac = 'CC:DD:EE:FF:AA:BB'

    # Pre-create the session row
    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac=mac)

    seg_file = tmp_path / 'segment_7.mp4'
    seg_file.write_bytes(b'video-data')

    # Task carries parent.id so the INSERT lands under the same session
    task = FakeTask(output_path=seg_file, camera_mac=mac, recording_id=parent.id, segment_index=7)

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(return_value=seg_file)
    svc._nas_syncer = fake_syncer

    try:
        await svc.on_recording_complete(task, keep_recording=False)

        async with AsyncSessionLocal() as session:
            recs = (await session.execute(select(Recording).order_by(Recording.id))).scalars().all()

        # The new per-segment row must have segment_index matching the task
        segment_rec = next((r for r in recs if r.segment_index == 7), None)
        assert segment_rec is not None, (
            f'Expected a Recording row with segment_index=7, got '
            f'[{", ".join(f"segment_index={r.segment_index}" for r in recs)}]. '
            'on_recording_complete must store task.segment_index in the new Recording row.'
        )
        assert segment_rec.status == 'completed'
    finally:
        rd_module.ws_manager = original_ws


@pytest.mark.asyncio
async def test_segments_get_different_file_paths(tmp_path):
    """Each per-segment Recording row must have a distinct file_path."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    mac = '11:22:33:44:55:66'

    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac=mac)

    seg0 = tmp_path / 'seg0.mp4'
    seg1 = tmp_path / 'seg1.mp4'
    seg2 = tmp_path / 'seg2.mp4'
    for f in (seg0, seg1, seg2):
        f.write_bytes(b'data')

    tasks = [
        FakeTask(output_path=seg0, camera_mac=mac, recording_id=parent.id, segment_index=0),
        FakeTask(output_path=seg1, camera_mac=mac, recording_id=parent.id, segment_index=1),
        FakeTask(output_path=seg2, camera_mac=mac, recording_id=parent.id, segment_index=2),
    ]

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(side_effect=lambda p, m: p.parent / 'synced' / p.name)
    svc._nas_syncer = fake_syncer

    try:
        for t in tasks:
            await svc.on_recording_complete(t, keep_recording=False)

        async with AsyncSessionLocal() as session:
            segment_recs = (
                (
                    await session.execute(
                        select(Recording)
                        .where(Recording.segment_index.isnot(None))
                        .where(Recording.camera_mac == mac)
                        .order_by(Recording.segment_index)
                    )
                )
                .scalars()
                .all()
            )

        file_paths = [r.file_path for r in segment_recs]
        assert len(set(file_paths)) == 3, f'Expected 3 distinct file_path values, got {file_paths}'
    finally:
        rd_module.ws_manager = original_ws


# ─────────────────────────────────────────────────────────────────────────────
# RED phase — tests that SHOULD FAIL until ffprobe logic is added to on_recording_complete
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_recording_complete_uses_ffprobe_duration_not_wall_clock(tmp_path, monkeypatch):
    """on_recording_complete must store actual media duration from ffprobe, not wall-clock elapsed time.

    RED: Currently fails because the implementation uses wall-clock elapsed time directly.
    GREEN: Implementation should call self._probe_duration(path) and use that value.
    """
    # Arrange — pre-create the Recording row
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac='AA:BB:CC:DD:EE:FF')

    output_file = tmp_path / 'segment.mp4'
    output_file.write_bytes(b'fake-video-data')
    task = FakeTask(output_path=output_file, camera_mac='AA:BB:CC:DD:EE:FF', recording_id=parent.id)
    task.started_at = datetime(2026, 5, 30, 10, 0, 0)  # 3+ hours ago → wall clock ≈ 10800s

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))
    # Probe returns 59s of actual media (much less than wall clock)
    svc._probe_duration = AsyncMock(return_value=59)

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_dest = tmp_path / 'synced' / 'segment.mp4'
    fake_dest.parent.mkdir(parents=True, exist_ok=True)
    fake_dest.write_bytes(b'fake-video-data')
    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(return_value=fake_dest)
    svc._nas_syncer = fake_syncer

    try:
        await svc.on_recording_complete(task, keep_recording=False)

        async with AsyncSessionLocal() as session:
            rec = (
                await session.execute(
                    select(Recording).where(
                        Recording.segment_index.isnot(None),
                        Recording.camera_mac == 'AA:BB:CC:DD:EE:FF',
                    )
                )
            ).scalar_one_or_none()
            assert rec is not None, 'Recording should exist (inserted per segment)'
            assert rec.duration == 59, (
                f'Expected duration=59 (ffprobe actual media), got {rec.duration}. '
                'on_recording_complete must call _probe_duration, not use wall-clock elapsed time.'
            )
            assert rec.status == 'completed'
    finally:
        rd_module.ws_manager = original_ws


@pytest.mark.asyncio
async def test_on_recording_complete_falls_back_to_wall_clock_when_ffprobe_returns_none(tmp_path):
    """If _probe_duration returns None, on_recording_complete should fall back to wall-clock duration."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac='AA:BB:CC:DD:EE:FF')

    output_file = tmp_path / 'segment.mp4'
    output_file.write_bytes(b'fake-video-data')
    task = FakeTask(output_path=output_file, camera_mac='AA:BB:CC:DD:EE:FF', recording_id=parent.id)
    task.started_at = datetime(2026, 5, 30, 10, 0, 0)

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))
    svc._probe_duration = AsyncMock(return_value=None)  # ffprobe unreachable

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_dest = tmp_path / 'synced' / 'segment.mp4'
    fake_dest.parent.mkdir(parents=True, exist_ok=True)
    fake_dest.write_bytes(b'fake-video-data')
    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(return_value=fake_dest)
    svc._nas_syncer = fake_syncer

    try:
        await svc.on_recording_complete(task, keep_recording=False)

        async with AsyncSessionLocal() as session:
            rec = (
                await session.execute(
                    select(Recording).where(
                        Recording.segment_index.isnot(None),
                        Recording.camera_mac == 'AA:BB:CC:DD:EE:FF',
                    )
                )
            ).scalar_one_or_none()
            assert rec is not None
            assert rec.status == 'completed'
            assert rec.duration is not None  # fallback to wall clock
    finally:
        rd_module.ws_manager = original_ws


# ─────────────────────────────────────────────────────────────────────────────
# on_recording_failed — existing ffprobe logic must remain intact
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_recording_failed_uses_ffprobe_treats_as_completed_at_30s(tmp_path):
    """on_recording_failed: actual media >= 30s → status=completed, duration=ffprobe value."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac='BB:CC:DD:EE:EE:EE')

    output_file = tmp_path / 'failed_segment.mp4'
    output_file.write_bytes(b'fake-video-data')
    task = FakeTask(output_path=output_file, camera_mac='BB:CC:DD:EE:EE:EE', recording_id=parent.id)
    task.started_at = datetime(2026, 5, 30, 9, 0, 0)

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))
    svc._probe_duration = AsyncMock(return_value=45)  # 45s actual media ≥ 30s threshold

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_dest = tmp_path / 'synced' / 'failed_segment.mp4'
    fake_dest.parent.mkdir(parents=True, exist_ok=True)
    fake_dest.write_bytes(b'fake-video-data')
    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(return_value=fake_dest)
    svc._nas_syncer = fake_syncer

    try:
        await svc.on_recording_failed(task, retcode=2, stderr='SIGKILL', keep_recording=False)

        async with AsyncSessionLocal() as session:
            rec = (
                await session.execute(
                    select(Recording).where(
                        Recording.segment_index.isnot(None),
                        Recording.camera_mac == 'BB:CC:DD:EE:EE:EE',
                    )
                )
            ).scalar_one_or_none()
            assert rec is not None
            assert rec.status == 'completed', f'Expected completed (45s >= 30s), got {rec.status}'
            assert rec.duration == 45
    finally:
        rd_module.ws_manager = original_ws


@pytest.mark.asyncio
async def test_on_recording_failed_marks_failed_when_media_under_30s(tmp_path):
    """on_recording_failed: actual media < 30s → status=failed."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac='CC:DD:EE:FF:AA:BB')

    output_file = tmp_path / 'short_segment.mp4'
    output_file.write_bytes(b'fake-video-data')
    task = FakeTask(output_path=output_file, camera_mac='CC:DD:EE:FF:AA:BB', recording_id=parent.id)
    task.started_at = datetime(2026, 5, 30, 9, 0, 0)

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))
    svc._probe_duration = AsyncMock(return_value=15)  # 15s < 30s threshold

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(return_value=output_file)
    svc._nas_syncer = fake_syncer

    try:
        await svc.on_recording_failed(task, retcode=2, stderr='SIGKILL', keep_recording=False)

        async with AsyncSessionLocal() as session:
            rec = (
                await session.execute(
                    select(Recording).where(
                        Recording.segment_index.isnot(None),
                        Recording.camera_mac == 'CC:DD:EE:FF:AA:BB',
                    )
                )
            ).scalar_one_or_none()
            assert rec is not None
            assert rec.status == 'failed', f'Expected failed (15s < 30s), got {rec.status}'
            assert rec.duration == 15
    finally:
        rd_module.ws_manager = original_ws


@pytest.mark.asyncio
async def test_on_recording_failed_marks_failed_when_ffprobe_unavailable(tmp_path):
    """on_recording_failed: ffprobe unavailable → status=failed (no wall-clock fallback)."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        parent = await _create_recording(session, recording_id=None, camera_mac='DD:EE:FF:AA:BB:CC')

    output_file = tmp_path / 'segment_no_probe.mp4'
    output_file.write_bytes(b'fake-video-data')
    task = FakeTask(output_path=output_file, camera_mac='DD:EE:FF:AA:BB:CC', recording_id=parent.id)
    task.started_at = datetime(2026, 5, 30, 9, 0, 0)

    svc = RecordingDomainService(MagicMock(spec=NasSyncer))
    svc._probe_duration = AsyncMock(return_value=None)  # ffprobe unavailable

    import app.domain.services.recording_domain as rd_module

    original_ws = rd_module.ws_manager
    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()
    rd_module.ws_manager = mock_ws

    fake_syncer = MagicMock(spec=NasSyncer)
    fake_syncer.sync_file = MagicMock(return_value=output_file)
    svc._nas_syncer = fake_syncer

    try:
        await svc.on_recording_failed(task, retcode=1, stderr='crashed', keep_recording=False)

        async with AsyncSessionLocal() as session:
            rec = (
                await session.execute(
                    select(Recording).where(
                        Recording.segment_index.isnot(None),
                        Recording.camera_mac == 'DD:EE:FF:AA:BB:CC',
                    )
                )
            ).scalar_one_or_none()
            assert rec is not None
            assert rec.status == 'failed'
    finally:
        rd_module.ws_manager = original_ws

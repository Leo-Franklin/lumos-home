"""Tests for Frigate-style single-process segment muxer recording."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.recorder import (
    Recorder,
    RecordingParams,
    RecordingSession,
    completed_segment_paths,
    segment_index_from_path,
)


class _FakeProcess:
    def __init__(self, retcode=None):
        self._retcode = retcode
        self.stdin = MagicMock()
        self.poll = MagicMock(side_effect=lambda: self._retcode)
        self.wait = MagicMock(return_value=self._retcode or 0)
        self.stderr = MagicMock(read=MagicMock(return_value=b''))

    def set_alive(self):
        self._retcode = None


def _write_segment(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x' * 20 * 1024)


def test_segment_index_from_path():
    assert segment_index_from_path(Path('MAC_20260610_120000_seg003.mp4')) == 3


def test_completed_segment_paths_single_active_file_not_finalized(tmp_path):
    """Must not treat the only open segment as complete while FFmpeg is running."""
    pattern = tmp_path / 'MAC_ts_seg%03d.mp4'
    _write_segment(tmp_path / 'MAC_ts_seg000.mp4')

    proc = _FakeProcess()
    proc.set_alive()
    session = RecordingSession(
        camera_mac='AA:BB:CC:DD:EE:FF',
        process=proc,
        output_pattern=pattern,
        session_started_at=datetime.now(),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
    )
    assert completed_segment_paths(session) == []


def test_completed_segment_paths_while_running(tmp_path):
    pattern = tmp_path / 'MAC_ts_seg%03d.mp4'
    seg0 = tmp_path / 'MAC_ts_seg000.mp4'
    seg1 = tmp_path / 'MAC_ts_seg001.mp4'
    _write_segment(seg0)
    _write_segment(seg1)

    proc = _FakeProcess()
    proc.set_alive()
    session = RecordingSession(
        camera_mac='AA:BB:CC:DD:EE:FF',
        process=proc,
        output_pattern=pattern,
        session_started_at=datetime.now(),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
    )
    paths = completed_segment_paths(session)
    assert len(paths) == 1
    assert paths[0].name == 'MAC_ts_seg000.mp4'


def test_completed_segment_paths_when_stopped(tmp_path):
    pattern = tmp_path / 'MAC_ts_seg%03d.mp4'
    for i in range(4):
        _write_segment(tmp_path / f'MAC_ts_seg{i:03d}.mp4')

    proc = _FakeProcess(retcode=0)
    session = RecordingSession(
        camera_mac='AA:BB:CC:DD:EE:FF',
        process=proc,
        output_pattern=pattern,
        session_started_at=datetime.now(),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
    )
    paths = completed_segment_paths(session)
    assert len(paths) == 4


class TestBuildFFmpegCmd:
    def test_default_uses_audio_aac_for_g711_cameras(self, tmp_path):
        """Default preset-record-generic-audio-aac: pcm_alaw → AAC in MP4."""
        recorder = Recorder(temp_dir=str(tmp_path))
        pattern = tmp_path / 'MAC_ts_seg%03d.mp4'
        params = RecordingParams(segment_seconds=60)
        cmd = recorder._build_ffmpeg_cmd('rtsp://cam/stream', pattern, params)
        assert cmd[0] == 'ffmpeg'
        assert '-rtsp_transport' in cmd and 'tcp' in cmd
        assert '-timeout' in cmd or '-stimeout' in cmd
        assert '-f' in cmd and 'segment' in cmd
        assert '-segment_time' in cmd and '60' in cmd
        assert '-map' in cmd and '0:v:0' in cmd and '0:a:0?' in cmd
        assert '-c:v' in cmd and 'copy' in cmd
        assert '-c:a' in cmd and 'aac' in cmd
        assert '-c' not in cmd
        assert 'movflags' not in cmd
        assert str(pattern) in cmd

    def test_audio_copy_mode_for_native_aac_cameras(self, tmp_path):
        """preset-record-generic-audio-copy — only when camera already outputs MP4 codecs."""
        recorder = Recorder(temp_dir=str(tmp_path))
        pattern = tmp_path / 'MAC_ts_seg%03d.mp4'
        params = RecordingParams(segment_seconds=60, audio_mode='copy')
        cmd = recorder._build_ffmpeg_cmd('rtsp://cam/stream', pattern, params)
        assert '-c' in cmd and cmd[cmd.index('-c') + 1] == 'copy'
        assert '-c:v' not in cmd
        assert '-c:a' not in cmd
        assert '-map' not in cmd


@pytest.mark.asyncio
async def test_four_segments_produce_four_db_rows(tmp_path, db):
    """3:22 at 60s preset → 4 segment files → 4 independent Recording rows."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.domain.models.recording import Recording
    from app.domain.services.recording_domain import RecordingDomainService
    from app.models.camera import Camera
    from app.models.device import Device
    from app.services.nas_syncer import NasSyncer

    mac = 'AA:BB:CC:DD:EE:FF'
    db.add(Device(mac=mac, device_type='camera', is_online=True))
    db.add(
        Camera(
            device_mac=mac,
            onvif_host='192.168.1.10',
            rtsp_url='rtsp://x',
            is_recording=True,
        )
    )
    parent = Recording(
        camera_mac=mac,
        file_path='(pending)',
        started_at=datetime.now(),
        status='recording',
    )
    db.add(parent)
    await db.commit()
    await db.refresh(parent)

    mock_nas = MagicMock(spec=NasSyncer)
    mock_nas.sync_file = MagicMock(side_effect=lambda p, _m: p)
    domain = RecordingDomainService(nas_syncer=mock_nas)
    domain._ws_manager = MagicMock()
    domain._ws_manager.broadcast = AsyncMock()
    domain._probe_duration = AsyncMock(return_value=60)

    recorder = Recorder(temp_dir=str(tmp_path))
    recorder.set_callbacks(
        on_complete=domain.on_recording_complete,
        on_failed=domain.on_recording_failed,
        should_continue=domain.should_continue_recording,
    )

    fake_proc = _FakeProcess()
    fake_proc.set_alive()

    def popen_factory(*_args, **_kwargs):
        return fake_proc

    import app.domain.services.recorder as rec_mod

    original_popen = rec_mod.subprocess.Popen
    rec_mod.subprocess.Popen = popen_factory
    try:
        await recorder.start_recording(mac, 'rtsp://x', RecordingParams(segment_seconds=60))
    finally:
        rec_mod.subprocess.Popen = original_popen

    session = recorder.active[mac]
    session.recording_id = parent.id
    session.session_recording_id = parent.id

    pattern = session.output_pattern
    prefix = pattern.name.replace('%03d', '')
    for i in range(3):
        _write_segment(tmp_path / f'{prefix}{i:03d}.mp4')
        await recorder._finalize_session_segments(session, keep_recording=True)

    _write_segment(tmp_path / f'{prefix}003.mp4')
    await recorder.stop_recording(mac)

    async with AsyncSessionLocal() as verify:
        rows = (
            (
                await verify.execute(
                    select(Recording)
                    .where(Recording.camera_mac == mac, Recording.segment_index.isnot(None))
                    .order_by(Recording.segment_index)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 4, f'Expected 4 segments, got {len(rows)}'
        assert [r.segment_index for r in rows] == [0, 1, 2, 3]
        assert len({r.file_path for r in rows}) == 4


@pytest.mark.asyncio
async def test_stop_recording_finalizes_last_partial_segment(tmp_path):
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    on_complete = AsyncMock()
    recorder._on_complete_cb = on_complete

    fake_proc = _FakeProcess()
    fake_proc.set_alive()

    def popen_factory(*_args, **_kwargs):
        return fake_proc

    import app.domain.services.recorder as rec_mod

    original_popen = rec_mod.subprocess.Popen
    rec_mod.subprocess.Popen = popen_factory
    try:
        await recorder.start_recording(mac, 'rtsp://x', RecordingParams(segment_seconds=60))
    finally:
        rec_mod.subprocess.Popen = original_popen

    session = recorder.active[mac]
    prefix = session.output_pattern.name.replace('%03d', '')
    _write_segment(tmp_path / f'{prefix}000.mp4')
    _write_segment(tmp_path / f'{prefix}001.mp4')

    last = await recorder.stop_recording(mac)
    assert last is not None
    assert on_complete.await_count == 2
    assert on_complete.await_args_list[-1].kwargs.get('keep_recording') is False

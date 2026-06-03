import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.recorder import Recorder, RecordingParams


class TestRecordingParams:
    def test_defaults(self):
        params = RecordingParams()
        assert params.resolution == '1920x1080'
        assert params.segment_seconds == 1800
        assert params.bitrate is None
        assert params.fps is None

    def test_bitrate_or_default_explicit(self):
        params = RecordingParams(bitrate=4096)
        assert params.bitrate_or_default() == 4096

    def test_bitrate_or_default_auto_1080p(self):
        params = RecordingParams(resolution='1920x1080')
        assert params.bitrate_or_default() == 2048

    def test_bitrate_or_default_auto_720p(self):
        params = RecordingParams(resolution='1280x720')
        assert params.bitrate_or_default() == 1024

    def test_bitrate_or_default_auto_480p(self):
        params = RecordingParams(resolution='640x480')
        assert params.bitrate_or_default() == 512

    def test_fps_or_default_explicit(self):
        params = RecordingParams(fps=30)
        assert params.fps_or_default() == 30

    def test_fps_or_default_null(self):
        params = RecordingParams()
        assert params.fps_or_default() == 25


class TestBuildFFmpegCmd:
    def test_default_params(self, tmp_path):
        params = RecordingParams()
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert cmd[0] == 'ffmpeg'
        assert '-c:v' in cmd
        assert 'copy' in cmd
        assert '-c:a' in cmd
        assert 'aac' in cmd
        assert '-t' in cmd
        assert '1800' in cmd
        assert '-movflags' in cmd
        assert '+frag_keyframe+empty_moov' in cmd
        assert str(output_path) in cmd
        # Stream copy — re-encode params are not applied
        for not_expected in ('libx264', '-b:v', '2048k', '-r', '25', '-s', '1920x1080'):
            assert not_expected not in cmd

    def test_custom_bitrate_ignored_in_copy_mode(self, tmp_path):
        params = RecordingParams(bitrate=4096)
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '4096k' not in cmd
        assert '-b:v' not in cmd

    def test_custom_fps_ignored_in_copy_mode(self, tmp_path):
        params = RecordingParams(fps=30)
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '-r' not in cmd

    def test_custom_resolution_ignored_in_copy_mode(self, tmp_path):
        params = RecordingParams(resolution='1280x720')
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '-s' not in cmd
        assert '1280x720' not in cmd

    def test_custom_segment_seconds(self, tmp_path):
        params = RecordingParams(segment_seconds=600)
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '-t' in cmd
        assert '600' in cmd

    def test_preset_like_params_only_segment_applied(self, tmp_path):
        """Preset video params are ignored in copy mode; only segment_seconds applies."""
        params = RecordingParams(
            resolution='1280x720',
            segment_seconds=600,
            bitrate=1024,
            fps=20,
        )
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '600' in cmd
        for not_expected in ('1280x720', '1024k', '20'):
            assert not_expected not in cmd


@pytest.mark.asyncio
async def test_monitor_auto_continue_completes_current_segment_and_allocates_new_recording(
    tmp_path, monkeypatch
):
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'
    finished_proc = MagicMock()
    finished_proc.poll.return_value = 0
    finished_proc.stderr.read.return_value = b''

    task = MagicMock()
    task.camera_mac = mac
    task.process = finished_proc
    task.output_path = Path(tmp_path / 'segment0.mp4')
    task.started_at = datetime.now()
    task.segment_seconds = 60
    task.rtsp_url = 'rtsp://192.168.1.100:554/stream'
    task.recording_id = 11
    task.segment_index = 0
    task.params = RecordingParams(segment_seconds=60)
    task.last_check = None

    recorder.active = {mac: task}
    recorder._on_complete_cb = AsyncMock()
    recorder._should_continue_cb = AsyncMock(return_value=True)
    recorder._create_next_recording_cb = AsyncMock(return_value=12)

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

    monkeypatch.setattr('app.domain.services.recorder.asyncio.sleep', fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await recorder._monitor_loop()

    recorder._on_complete_cb.assert_awaited_once_with(task, keep_recording=True)
    # Each auto-continue segment gets its own recording_id via _allocate_next_recording_id
    assert recorder.active[mac].recording_id == 12, (
        '新segment的recording_id应由_allocate_next_recording_id分配'
    )
    assert recorder.active[mac].segment_index == 1


@pytest.mark.asyncio
async def test_monitor_stalled_segment_allocates_new_recording_before_restart(
    tmp_path, monkeypatch
):
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'
    stalled_proc = MagicMock()
    stalled_proc.poll.return_value = None

    output_path = tmp_path / 'segment0.mp4'
    output_path.write_bytes(b'video-data')

    task = MagicMock()
    task.camera_mac = mac
    task.process = stalled_proc
    task.output_path = output_path
    task.started_at = datetime.now()
    task.segment_seconds = 60
    task.rtsp_url = 'rtsp://192.168.1.100:554/stream'
    task.recording_id = 21
    task.segment_index = 0
    task.params = RecordingParams(segment_seconds=60)
    task.last_check = datetime.now()
    task.last_bytes = output_path.stat().st_size

    recorder.active = {mac: task}
    recorder._on_failed_cb = AsyncMock()
    recorder._create_next_recording_cb = AsyncMock(return_value=22)

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
    # Each auto-restarted segment gets a NEW recording_id via _allocate_next_recording_id,
    # giving every segment its own recording_id in the DB (per-segment independent rows).
    assert recorder.active[mac].recording_id == 22, (
        f'Expected stalled segment to get new recording_id=22 from _allocate_next_recording_id, got {recorder.active[mac].recording_id}'
    )
    assert recorder.active[mac].segment_index == 1


@pytest.mark.asyncio
async def test_stalled_segment_skips_restart_when_should_continue_cb_returns_false(
    tmp_path, monkeypatch
):
    """验证：stalled分支中，如果should_continue_cb返回False，则不重启新segment"""
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'
    stalled_proc = MagicMock()
    stalled_proc.poll.return_value = None

    output_path = tmp_path / 'segment0.mp4'
    output_path.write_bytes(b'video-data')

    task = MagicMock()
    task.camera_mac = mac
    task.process = stalled_proc
    task.output_path = output_path
    task.started_at = datetime.now()
    task.segment_seconds = 60
    task.rtsp_url = 'rtsp://192.168.1.100:554/stream'
    task.recording_id = 21
    task.segment_index = 0
    task.params = RecordingParams(segment_seconds=60)
    task.last_check = datetime.now()
    task.last_bytes = output_path.stat().st_size

    recorder.active = {mac: task}
    recorder._on_failed_cb = AsyncMock()
    recorder._should_continue_cb = AsyncMock(return_value=False)
    recorder._create_next_recording_cb = AsyncMock(return_value=22)

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
    # should_continue_cb was called to decide whether to restart
    recorder._should_continue_cb.assert_awaited_once_with(mac)
    # mac should NOT be in active anymore (no restart happened)
    assert mac not in recorder.active, 'stalled但should_continue=False时，不应重启新segment'


# ─────────────────────────────────────────────────────────────────────────────
# Bug 1: segment正常完成后，new_task未存回self.active[mac]，
# 导致监控循环继续检查旧task(segment_index=0)，segment_index无法递增
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_segment_completion_stores_new_task_in_active(tmp_path, monkeypatch):
    """验证：segment正常完成后，新task必须存回self.active[mac]，否则segment_index不递增"""
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    # 模拟正常完成的进程 (poll() 返回 0 表示正常退出)
    finished_proc = MagicMock()
    finished_proc.poll.return_value = 0
    finished_proc.stderr.read.return_value = b''

    task = MagicMock()
    task.camera_mac = mac
    task.process = finished_proc
    task.output_path = tmp_path / 'segment0.mp4'
    task.started_at = datetime.now()
    task.segment_seconds = 60
    task.rtsp_url = 'rtsp://192.168.1.100:554/stream'
    task.recording_id = 11
    task.segment_index = 0
    task.params = RecordingParams(segment_seconds=60)
    task.last_check = None

    recorder.active = {mac: task}
    recorder._on_complete_cb = AsyncMock()
    recorder._should_continue_cb = AsyncMock(return_value=True)
    recorder._create_next_recording_cb = AsyncMock(return_value=12)

    # 新segment的进程
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

    monkeypatch.setattr('app.domain.services.recorder.asyncio.sleep', fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await recorder._monitor_loop()

    # 核心验证：new_task必须存回self.active[mac]，且segment_index=1
    assert mac in recorder.active, 'segment完成后，mac应保留在active中（用于监控新进程）'
    assert recorder.active[mac].segment_index == 1, (
        'segment_index应递增到1。'
        '如果失败原因：_monitor_loop的finished分支中，new_task未被存回self.active[mac]，'
        '导致下次循环仍监控旧task（segment_index=0）'
    )
    assert recorder.active[mac].recording_id == 12, (
        '新segment的recording_id应由_allocate_next_recording_id分配'
    )
    assert recorder.active[mac].process is next_proc, 'active中应保存新segment的进程对象'

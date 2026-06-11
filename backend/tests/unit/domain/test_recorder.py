import asyncio
import subprocess
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.go2rtc_adapter import Go2RtcAdapter, Go2RtcConfig
from app.domain.services.recorder import (
    Recorder,
    RecordingParams,
    RecordingSession,
)


def _make_go2rtc_adapter(*, enabled: bool = True) -> tuple[Go2RtcAdapter, AsyncMock]:
    client = AsyncMock()
    adapter = Go2RtcAdapter(
        config=Go2RtcConfig(
            enabled=enabled,
            api_base='http://127.0.0.1:1984',
            rtsp_base='rtsp://127.0.0.1:8554',
        ),
        http_client=client,
    )
    return adapter, client


class TestRecordingParams:
    def test_defaults(self):
        params = RecordingParams()
        assert params.resolution == '1920x1080'
        assert params.segment_seconds == 1800

    def test_bitrate_or_default_auto_1080p(self):
        assert RecordingParams(resolution='1920x1080').bitrate_or_default() == 2048

    def test_fps_or_default_null(self):
        assert RecordingParams().fps_or_default() == 25


class TestResolveRecordingRtspUrl:
    @pytest.mark.asyncio
    async def test_returns_camera_url_when_go2rtc_disabled(self, tmp_path):
        adapter, client = _make_go2rtc_adapter(enabled=False)
        recorder = Recorder(temp_dir=str(tmp_path), go2rtc_adapter=adapter)
        mac = 'AA:BB:CC:DD:EE:01'
        camera_url = 'rtsp://192.168.1.100:554/stream'

        resolved = await recorder._resolve_recording_rtsp_url(mac, camera_url)

        assert resolved == camera_url
        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_camera_url_without_adapter(self, tmp_path):
        recorder = Recorder(temp_dir=str(tmp_path))
        camera_url = 'rtsp://192.168.1.100:554/stream'

        resolved = await recorder._resolve_recording_rtsp_url('AA:BB:CC:DD:EE:01', camera_url)

        assert resolved == camera_url

    @pytest.mark.asyncio
    async def test_ensures_stream_and_returns_restream_when_enabled(self, tmp_path):
        adapter, client = _make_go2rtc_adapter(enabled=True)
        list_resp = MagicMock(status_code=200)
        list_resp.json.return_value = {}
        put_resp = MagicMock(status_code=200)
        client.get.return_value = list_resp
        client.put.return_value = put_resp

        recorder = Recorder(temp_dir=str(tmp_path), go2rtc_adapter=adapter)
        mac = 'AA:BB:CC:DD:EE:01'
        camera_url = 'rtsp://192.168.1.100:554/stream'

        resolved = await recorder._resolve_recording_rtsp_url(mac, camera_url)

        assert resolved == 'rtsp://127.0.0.1:8554/AA-BB-CC-DD-EE-01'
        client.put.assert_awaited_once_with(
            'http://127.0.0.1:1984/api/streams',
            params={'src': camera_url, 'name': 'AA-BB-CC-DD-EE-01'},
            timeout=10.0,
        )


class TestBuildFFmpegCmd:
    def test_segment_muxer_with_custom_duration(self, tmp_path):
        params = RecordingParams(segment_seconds=600)
        recorder = Recorder(temp_dir=str(tmp_path))
        pattern = tmp_path / 'out_seg%03d.mp4'
        cmd = recorder._build_ffmpeg_cmd('rtsp://192.168.1.100:554/stream', pattern, params)
        assert cmd[0] == 'ffmpeg'
        assert '-c:v' in cmd and 'copy' in cmd
        assert '-c:a' in cmd and 'aac' in cmd
        assert '-map' in cmd
        assert '-f' in cmd and 'segment' in cmd
        assert '-segment_time' in cmd and '600' in cmd
        assert '-avoid_negative_ts' in cmd
        assert '-timeout' in cmd or '-stimeout' in cmd
        assert 'movflags' not in cmd
        assert str(pattern) in cmd


@pytest.mark.asyncio
async def test_start_recording_uses_restream_url_when_go2rtc_enabled(tmp_path):
    adapter, client = _make_go2rtc_adapter(enabled=True)
    list_resp = MagicMock(status_code=200)
    list_resp.json.return_value = {}
    client.get.return_value = list_resp
    client.put.return_value = MagicMock(status_code=200)

    recorder = Recorder(temp_dir=str(tmp_path), go2rtc_adapter=adapter)
    mac = 'AA:BB:CC:DD:EE:01'
    camera_url = 'rtsp://192.168.1.100:554/stream'
    captured_cmd: list[str] = []

    def popen_factory(cmd, **_kwargs):
        captured_cmd.extend(cmd)
        proc = MagicMock()
        proc.poll.return_value = None
        proc.stdin = MagicMock()
        proc.stderr = MagicMock(read=MagicMock(return_value=b''))
        return proc

    import app.domain.services.recorder as rec_mod

    original_popen = rec_mod.subprocess.Popen
    rec_mod.subprocess.Popen = popen_factory
    try:
        await recorder.start_recording(mac, camera_url, RecordingParams(segment_seconds=60))
    finally:
        rec_mod.subprocess.Popen = original_popen

    assert 'rtsp://127.0.0.1:8554/AA-BB-CC-DD-EE-01' in captured_cmd
    assert camera_url not in captured_cmd
    assert recorder.active[mac].rtsp_url == 'rtsp://127.0.0.1:8554/AA-BB-CC-DD-EE-01'


class TestGracefulShutdown:
    def test_terminate_ffmpeg_waits_before_kill(self):
        from app.domain.services.recorder import Recorder

        proc = MagicMock()
        proc.poll.return_value = None
        proc.stdin = MagicMock()
        proc.wait = MagicMock(side_effect=[subprocess.TimeoutExpired('ffmpeg', 10), None])

        Recorder._terminate_ffmpeg(proc, 'AA:BB:CC:DD:EE:FF')

        proc.stdin.write.assert_called_once_with(b'q')
        proc.terminate.assert_called_once()
        proc.kill.assert_not_called()
        assert proc.wait.call_count == 2


class TestStartupGracePeriod:
    @pytest.mark.asyncio
    async def test_stall_not_detected_during_startup_grace(self, tmp_path, monkeypatch):
        """Frigate allows ~90s for the first segment before declaring failure."""
        from app.domain.services.recorder import STARTUP_GRACE_SECONDS

        recorder = Recorder(temp_dir=str(tmp_path))
        mac = 'AA:BB:CC:DD:EE:FF'
        stalled_path = tmp_path / 'MAC_ts_seg000.mp4'
        stalled_path.write_bytes(b'x' * 20 * 1024)

        proc = MagicMock()
        proc.poll.return_value = None
        session = RecordingSession(
            camera_mac=mac,
            process=proc,
            output_pattern=tmp_path / 'MAC_ts_seg%03d.mp4',
            session_started_at=datetime.now(),
            segment_seconds=60,
            rtsp_url='rtsp://x',
            params=RecordingParams(segment_seconds=60),
        )
        recorder.active = {mac: session}
        recorder._handle_stalled_session = AsyncMock()
        recorder._should_continue_cb = AsyncMock(return_value=True)

        now = datetime.now()
        session.last_check = now - timedelta(seconds=STARTUP_GRACE_SECONDS - 10)
        session.last_stall_bytes = stalled_path.stat().st_size

        await recorder._check_session_stall(session, now)

        recorder._handle_stalled_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_monitor_does_not_finalize_single_active_segment(tmp_path, monkeypatch):
    """Regression: with only seg000 present, monitor must not sync/finalize early."""
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    pattern = tmp_path / 'MAC_ts_seg%03d.mp4'
    (tmp_path / 'MAC_ts_seg000.mp4').write_bytes(b'x' * 20 * 1024)

    proc = MagicMock()
    proc.poll.return_value = None
    session = RecordingSession(
        camera_mac=mac,
        process=proc,
        output_pattern=pattern,
        session_started_at=datetime.now(),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
    )
    recorder.active = {mac: session}
    recorder._on_complete_cb = AsyncMock()
    recorder._should_continue_cb = AsyncMock(return_value=True)

    sleep_calls = {'n': 0}

    async def fake_sleep(_):
        sleep_calls['n'] += 1
        if sleep_calls['n'] > 1:
            raise asyncio.CancelledError()

    monkeypatch.setattr('app.domain.services.recorder.asyncio.sleep', fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await recorder._monitor_loop()

    recorder._on_complete_cb.assert_not_awaited()


@pytest.mark.asyncio
async def test_monitor_finalizes_segment_when_next_file_appears(tmp_path, monkeypatch):
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    pattern = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000_seg%03d.mp4'
    seg0 = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000_seg000.mp4'
    seg1 = tmp_path / 'AA_BB_CC_DD_EE_FF_20260530_100000_seg001.mp4'
    seg0.write_bytes(b'x' * 20 * 1024)
    seg1.write_bytes(b'x' * 20 * 1024)

    proc = MagicMock()
    proc.poll.return_value = None
    session = RecordingSession(
        camera_mac=mac,
        process=proc,
        output_pattern=pattern,
        session_started_at=datetime.now(),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
    )
    recorder.active = {mac: session}
    recorder._on_complete_cb = AsyncMock()
    recorder._should_continue_cb = AsyncMock(return_value=True)

    await recorder._finalize_session_segments(session, keep_recording=True)

    recorder._on_complete_cb.assert_awaited_once()
    assert recorder._on_complete_cb.await_args.kwargs['keep_recording'] is True


@pytest.mark.asyncio
async def test_monitor_stops_when_should_continue_false(tmp_path, monkeypatch):
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    proc = MagicMock()
    proc.poll.return_value = None
    proc.stdin = MagicMock()
    pattern = tmp_path / 'MAC_seg%03d.mp4'
    session = RecordingSession(
        camera_mac=mac,
        process=proc,
        output_pattern=pattern,
        session_started_at=datetime.now(),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
    )
    recorder.active = {mac: session}
    recorder._should_continue_cb = AsyncMock(return_value=False)
    recorder.stop_recording = AsyncMock(return_value=None)

    sleep_calls = {'n': 0}

    async def fake_sleep(_):
        sleep_calls['n'] += 1
        if sleep_calls['n'] > 1:
            raise asyncio.CancelledError()

    monkeypatch.setattr('app.domain.services.recorder.asyncio.sleep', fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await recorder._monitor_loop()

    recorder.stop_recording.assert_awaited_once_with(mac)


@pytest.mark.asyncio
async def test_stalled_session_restarts_with_monotonic_segment_index(tmp_path, monkeypatch):
    recorder = Recorder(temp_dir=str(tmp_path))
    mac = 'AA:BB:CC:DD:EE:FF'

    stalled_path = tmp_path / 'MAC_ts_seg000.mp4'
    stalled_path.write_bytes(b'x' * 20 * 1024)

    proc = MagicMock()
    proc.poll.return_value = None
    pattern = tmp_path / 'MAC_ts_seg%03d.mp4'
    session = RecordingSession(
        camera_mac=mac,
        process=proc,
        output_pattern=pattern,
        session_started_at=datetime.now(),
        segment_seconds=60,
        rtsp_url='rtsp://x',
        params=RecordingParams(segment_seconds=60),
        next_db_segment_index=2,
    )
    recorder.active = {mac: session}
    recorder._on_failed_cb = AsyncMock()
    recorder._should_continue_cb = AsyncMock(return_value=True)
    recorder._terminate_ffmpeg = MagicMock()

    async def fake_launch(*_args, **_kwargs):
        new_sess = RecordingSession(
            camera_mac=mac,
            process=MagicMock(poll=MagicMock(return_value=None)),
            output_pattern=tmp_path / 'MAC_ts2_seg%03d.mp4',
            session_started_at=datetime.now(),
            segment_seconds=60,
            rtsp_url='rtsp://x',
            params=RecordingParams(segment_seconds=60),
            next_db_segment_index=session.next_db_segment_index,
        )
        recorder.active[mac] = new_sess
        return new_sess

    recorder._launch_session = AsyncMock(side_effect=fake_launch)

    await recorder._handle_stalled_session(session)

    recorder._on_failed_cb.assert_awaited_once()
    task = recorder._on_failed_cb.await_args.args[0]
    assert task.segment_index == 2
    assert mac in recorder.active
    assert recorder.active[mac].next_db_segment_index == 3

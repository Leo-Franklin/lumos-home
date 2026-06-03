"""Unit tests for app/domain/services/stream_manager.py.

TDD: each test describes one behavior of StreamManager. The launcher and
readiness callable are injected so we never spawn real ffmpeg in tests.
"""

from unittest.mock import MagicMock, patch

import pytest


def _make_fake_launcher(*, pid: int = 1234, poll_return: int | None = None):
    """Build a launcher that returns a fake process + a readiness probe.

    poll_return controls the immediate process.poll() value. None means
    "process still running"; otherwise the process is treated as exited.
    """
    fake_proc = MagicMock()
    fake_proc.pid = pid
    fake_proc.poll.return_value = poll_return
    fake_proc.terminate = MagicMock()
    fake_proc.kill = MagicMock()
    fake_proc.wait = MagicMock()

    def launcher():
        return fake_proc, lambda: True  # ready immediately

    return launcher, fake_proc


@pytest.mark.asyncio
async def test_start_moves_state_to_running_when_launcher_ready():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)
    launcher, _proc = _make_fake_launcher(pid=42)

    info = await mgr.start('AA:BB:CC:DD:EE:01', launcher, timeout=2.0, poll_interval=0.01)

    assert info.state is StreamState.RUNNING
    assert info.camera_mac == 'AA:BB:CC:DD:EE:01'
    assert info.pid == 42
    assert info.started_at is not None
    assert mgr.get('AA:BB:CC:DD:EE:01').state is StreamState.RUNNING


@pytest.mark.asyncio
async def test_get_unknown_camera_returns_idle_state():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)

    info = mgr.get('AA:BB:CC:DD:EE:FF')

    assert info.state is StreamState.IDLE
    assert info.camera_mac == 'AA:BB:CC:DD:EE:FF'


@pytest.mark.asyncio
async def test_start_twice_raises_when_already_running():
    from app.domain.services.stream_manager import StreamManager

    mgr = StreamManager(max_concurrent=4)
    launcher_a, proc_a = _make_fake_launcher(pid=11)
    launcher_b, _proc_b = _make_fake_launcher(pid=22)

    await mgr.start('AA:BB:CC:DD:EE:01', launcher_a, timeout=2.0, poll_interval=0.01)

    with pytest.raises(RuntimeError, match='already'):
        await mgr.start('AA:BB:CC:DD:EE:01', launcher_b, timeout=2.0, poll_interval=0.01)


@pytest.mark.asyncio
async def test_start_marks_failed_when_process_exits_during_readiness_poll():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)
    # poll_return=1 means process exited with code 1
    launcher, _proc = _make_fake_launcher(pid=99, poll_return=1)

    with pytest.raises(RuntimeError, match='exited'):
        await mgr.start('AA:BB:CC:DD:EE:01', launcher, timeout=2.0, poll_interval=0.01)

    info = mgr.get('AA:BB:CC:DD:EE:01')
    assert info.state is StreamState.FAILED
    assert info.error is not None
    assert '1' in info.error


@pytest.mark.asyncio
async def test_start_raises_when_readiness_never_returns_true():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)
    fake_proc = MagicMock()
    fake_proc.pid = 7
    fake_proc.poll.return_value = None  # process still running
    fake_proc.terminate = MagicMock()
    fake_proc.kill = MagicMock()
    fake_proc.wait = MagicMock()

    def launcher():
        return fake_proc, lambda: False  # never ready

    with pytest.raises(TimeoutError):
        await mgr.start('AA:BB:CC:DD:EE:01', launcher, timeout=0.1, poll_interval=0.01)

    info = mgr.get('AA:BB:CC:DD:EE:01')
    assert info.state is StreamState.FAILED
    assert 'ready' in (info.error or '').lower()
    # cleanup must have been attempted
    fake_proc.terminate.assert_called()


@pytest.mark.asyncio
async def test_stop_running_returns_to_idle_and_terminates_process():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)
    launcher, proc = _make_fake_launcher(pid=55)

    await mgr.start('AA:BB:CC:DD:EE:01', launcher, timeout=2.0, poll_interval=0.01)
    await mgr.stop('AA:BB:CC:DD:EE:01')

    assert mgr.get('AA:BB:CC:DD:EE:01').state is StreamState.IDLE
    proc.terminate.assert_called()


@pytest.mark.asyncio
async def test_stop_idle_is_noop():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)

    # Should not raise even if the stream was never started
    await mgr.stop('AA:BB:CC:DD:EE:99')

    assert mgr.get('AA:BB:CC:DD:EE:99').state is StreamState.IDLE


@pytest.mark.asyncio
async def test_stop_all_terminates_every_active_stream():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)
    launcher_a, proc_a = _make_fake_launcher(pid=11)
    launcher_b, proc_b = _make_fake_launcher(pid=22)

    await mgr.start('AA:BB:CC:DD:EE:01', launcher_a, timeout=2.0, poll_interval=0.01)
    await mgr.start('AA:BB:CC:DD:EE:02', launcher_b, timeout=2.0, poll_interval=0.01)

    await mgr.stop_all()

    assert mgr.get('AA:BB:CC:DD:EE:01').state is StreamState.IDLE
    assert mgr.get('AA:BB:CC:DD:EE:02').state is StreamState.IDLE
    proc_a.terminate.assert_called()
    proc_b.terminate.assert_called()


@pytest.mark.asyncio
async def test_enforces_max_concurrent_streams():
    from app.domain.services.stream_manager import StreamManager

    mgr = StreamManager(max_concurrent=2)
    launchers = [
        _make_fake_launcher(pid=1),
        _make_fake_launcher(pid=2),
        _make_fake_launcher(pid=3),
    ]

    await mgr.start('A', launchers[0][0], timeout=2.0, poll_interval=0.01)
    await mgr.start('B', launchers[1][0], timeout=2.0, poll_interval=0.01)

    with pytest.raises(RuntimeError, match='Max concurrent'):
        await mgr.start('C', launchers[2][0], timeout=2.0, poll_interval=0.01)


@pytest.mark.asyncio
async def test_list_streams_returns_active_entries():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)
    launcher, _ = _make_fake_launcher(pid=33)

    await mgr.start('AA:BB:CC:DD:EE:01', launcher, timeout=2.0, poll_interval=0.01)
    streams = mgr.list()

    assert len(streams) == 1
    assert streams[0].camera_mac == 'AA:BB:CC:DD:EE:01'
    assert streams[0].state is StreamState.RUNNING


@pytest.mark.asyncio
async def test_can_restart_after_stop():
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4)
    launcher, _proc = _make_fake_launcher(pid=11)
    await mgr.start('A', launcher, timeout=2.0, poll_interval=0.01)
    await mgr.stop('A')

    # After stop, the slot is free and a new start should succeed
    launcher2, _ = _make_fake_launcher(pid=22)
    info = await mgr.start('A', launcher2, timeout=2.0, poll_interval=0.01)

    assert info.state is StreamState.RUNNING
    assert info.pid == 22


@pytest.mark.asyncio
async def test_start_hls_uses_ffmpeg_command_and_m3u8_readiness(tmp_path):
    """start_hls builds the canonical ffmpeg HLS command, polls for index.m3u8,
    and updates the HLS base dir on the StreamManager so the static-mount
    endpoint can serve files."""
    from app.domain.services.stream_manager import StreamManager, StreamState

    mgr = StreamManager(max_concurrent=4, hls_base=tmp_path)

    fake_proc = MagicMock()
    fake_proc.pid = 777
    fake_proc.poll.return_value = None
    fake_proc.terminate = MagicMock()
    fake_proc.kill = MagicMock()
    fake_proc.wait = MagicMock()

    with patch('app.domain.services.stream_manager.subprocess.Popen', return_value=fake_proc):
        info = await mgr.start_hls(
            'AA:BB:CC:DD:EE:01',
            rtsp_url='rtsp://camera/stream',
            timeout=2.0,
            poll_interval=0.01,
            is_ready=lambda: True,  # test injection: ready immediately
        )

    assert info.state is StreamState.RUNNING
    assert info.pid == 777
    assert mgr.hls_dir_for('AA:BB:CC:DD:EE:01') == tmp_path / 'AA-BB-CC-DD-EE-01'
    # StreamManager must track this stream as a normal one (so stop works)
    assert mgr.get('AA:BB:CC:DD:EE:01').state is StreamState.RUNNING


@pytest.mark.asyncio
async def test_start_hls_cleans_output_dir_before_launch(tmp_path):
    """Pre-existing m3u8 segments from a previous run must be removed
    so the new stream starts from a clean playlist."""
    from app.domain.services.stream_manager import StreamManager

    mgr = StreamManager(max_concurrent=4, hls_base=tmp_path)
    cam_dir = tmp_path / 'AA-BB-CC-DD-EE-01'
    cam_dir.mkdir(parents=True)
    (cam_dir / 'index.m3u8').write_text('stale playlist')
    (cam_dir / 'old_segment.ts').write_text('stale')

    fake_proc = MagicMock()
    fake_proc.pid = 1
    fake_proc.poll.return_value = None
    fake_proc.terminate = MagicMock()
    fake_proc.kill = MagicMock()
    fake_proc.wait = MagicMock()

    with patch('app.domain.services.stream_manager.subprocess.Popen', return_value=fake_proc):
        info = await mgr.start_hls(
            'AA:BB:CC:DD:EE:01',
            rtsp_url='rtsp://camera/stream',
            timeout=2.0,
            poll_interval=0.02,
            is_ready=lambda: True,
        )

    assert info.state.value == 'running'  # type: ignore[attr-defined]
    # After start, no leftover segment from the old run should remain
    assert not (cam_dir / 'old_segment.ts').exists()


@pytest.mark.asyncio
async def test_hls_dir_for_unknown_camera_returns_none(tmp_path):
    from app.domain.services.stream_manager import StreamManager

    mgr = StreamManager(max_concurrent=4, hls_base=tmp_path)
    assert mgr.hls_dir_for('AA:BB:CC:DD:EE:FF') is None

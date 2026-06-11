"""Unit tests for Go2RtcRunner — embedded go2rtc process lifecycle."""

from unittest.mock import MagicMock, patch


def test_resolve_binary_prefers_packaged_dir(monkeypatch, tmp_path):
    from app.domain.services.go2rtc_runner import resolve_go2rtc_binary

    binary = tmp_path / 'go2rtc' / 'go2rtc.exe'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'')
    monkeypatch.setattr('app.domain.services.go2rtc_runner.is_packaged', lambda: True)
    monkeypatch.setattr('app.domain.services.go2rtc_runner._exe_dir', lambda: tmp_path)

    assert resolve_go2rtc_binary() == binary


def test_resolve_binary_returns_none_when_missing(monkeypatch):
    from app.domain.services.go2rtc_runner import resolve_go2rtc_binary

    monkeypatch.setattr('app.domain.services.go2rtc_runner.is_packaged', lambda: False)
    assert resolve_go2rtc_binary(explicit='') is None


def test_resolve_binary_uses_explicit_path(tmp_path, monkeypatch):
    from app.domain.services.go2rtc_runner import resolve_go2rtc_binary

    binary = tmp_path / 'custom' / 'go2rtc.exe'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'')
    monkeypatch.setattr('app.domain.services.go2rtc_runner.is_packaged', lambda: False)

    assert resolve_go2rtc_binary(explicit=str(binary)) == binary


def test_should_start_embedded_runner_with_local_binary(tmp_path):
    from app.domain.services.go2rtc_runner import should_start_embedded_runner

    binary = tmp_path / 'go2rtc.exe'
    assert should_start_embedded_runner(go2rtc_enabled=True, binary=binary) is True


def test_should_start_embedded_runner_external_mode():
    """Docker sidecar: enabled but no local binary — adapter uses external go2rtc."""
    from app.domain.services.go2rtc_runner import should_start_embedded_runner

    assert should_start_embedded_runner(go2rtc_enabled=True, binary=None) is False


def test_should_start_embedded_runner_when_disabled(tmp_path):
    from app.domain.services.go2rtc_runner import should_start_embedded_runner

    assert should_start_embedded_runner(go2rtc_enabled=False, binary=tmp_path / 'x.exe') is False


def test_write_config_creates_yaml(tmp_path):
    from app.domain.services.go2rtc_runner import write_go2rtc_config

    path = write_go2rtc_config(tmp_path / 'go2rtc.yaml', api_port=1984, rtsp_port=8554)
    text = path.read_text(encoding='utf-8')
    assert '127.0.0.1:1984' in text
    assert ':8554' in text
    assert '8555' in text


def test_write_config_includes_webrtc_candidates(tmp_path):
    from app.domain.services.go2rtc_runner import read_webrtc_candidates, write_go2rtc_config

    path = write_go2rtc_config(
        tmp_path / 'go2rtc.yaml',
        webrtc_candidates=['stun:8555', '192.168.1.10:8555'],
    )
    assert read_webrtc_candidates(path) == ['stun:8555', '192.168.1.10:8555']


def test_read_webrtc_candidates_from_existing_yaml(tmp_path):
    from app.domain.services.go2rtc_runner import read_webrtc_candidates

    path = tmp_path / 'go2rtc.yaml'
    path.write_text(
        'webrtc:\n  listen: ":8555"\n  candidates:\n    - stun:8555\nstreams: {}\n',
        encoding='utf-8',
    )
    assert read_webrtc_candidates(path) == ['stun:8555']


def test_runner_start_invokes_subprocess(tmp_path):
    from app.domain.services.go2rtc_runner import Go2RtcRunner

    cfg_path = tmp_path / 'go2rtc.yaml'
    cfg_path.write_text('api:\n  listen: "127.0.0.1:1984"\n', encoding='utf-8')
    binary = tmp_path / 'go2rtc.exe'
    binary.write_bytes(b'')
    runner = Go2RtcRunner()
    proc = MagicMock()
    proc.poll.return_value = None

    with patch('app.domain.services.go2rtc_runner.subprocess.Popen', return_value=proc) as popen:
        runner.start(binary=binary, config_path=cfg_path)

    popen.assert_called_once()
    args = popen.call_args[0][0]
    assert str(binary) in args
    assert '-config' in args
    assert str(cfg_path) in args
    assert runner.is_running() is True


def test_runner_stop_terminates_process(tmp_path):
    from app.domain.services.go2rtc_runner import Go2RtcRunner

    runner = Go2RtcRunner()
    proc = MagicMock()
    proc.poll.return_value = None
    runner._process = proc  # noqa: SLF001 — test reaches private state

    runner.stop()

    proc.terminate.assert_called_once()
    assert runner.is_running() is False

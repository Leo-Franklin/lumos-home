from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_probe_rtsp_success():
    from app.services.camera_health import CameraHealthChecker

    checker = CameraHealthChecker(interval=60)

    fake_result = MagicMock()
    fake_result.returncode = 0

    with patch('subprocess.run', return_value=fake_result):
        result = await checker._probe_rtsp('rtsp://192.168.1.100:554/stream')

    assert result is True


@pytest.mark.asyncio
async def test_probe_rtsp_nonzero_exit_returns_false():
    from app.services.camera_health import CameraHealthChecker

    checker = CameraHealthChecker(interval=60)

    fake_result = MagicMock()
    fake_result.returncode = 1

    with patch('subprocess.run', return_value=fake_result):
        result = await checker._probe_rtsp('rtsp://192.168.1.100:554/stream')

    assert result is False


@pytest.mark.asyncio
async def test_probe_rtsp_timeout_returns_false():
    from app.services.camera_health import CameraHealthChecker

    checker = CameraHealthChecker(interval=60)

    with patch('subprocess.run', side_effect=TimeoutError()):
        result = await checker._probe_rtsp('rtsp://192.168.1.100:554/stream')

    assert result is False


@pytest.mark.asyncio
async def test_probe_rtsp_exception_returns_false():
    from app.services.camera_health import CameraHealthChecker

    checker = CameraHealthChecker(interval=60)

    with patch('subprocess.run', side_effect=OSError('ffprobe not found')):
        result = await checker._probe_rtsp('rtsp://192.168.1.100:554/stream')

    assert result is False

"""StreamManager — unified ffmpeg/HLS process lifecycle for cameras.

Owns per-camera stream state and a process table so HLS, recording, and
future pipelines share one place to start, stop, and observe camera streams.
"""

import asyncio
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class StreamState(StrEnum):
    IDLE = 'idle'
    STARTING = 'starting'
    RUNNING = 'running'
    STALLED = 'stalled'
    FAILED = 'failed'


@dataclass
class StreamInfo:
    camera_mac: str
    state: StreamState = StreamState.IDLE
    started_at: datetime | None = None
    last_active_at: datetime | None = None
    error: str | None = None
    pid: int | None = None


class StreamLauncher(Protocol):
    """Returns (process, is_ready). Called by StreamManager.start."""

    def __call__(self) -> tuple[subprocess.Popen, Callable[[], bool]]: ...


def _mac_to_dir(mac: str) -> str:
    return mac.replace(':', '-')


def _build_hls_cmd(rtsp_url: str, output_path: Path) -> list[str]:
    return [
        'ffmpeg',
        '-y',
        '-rtsp_transport',
        'tcp',
        '-i',
        rtsp_url,
        '-c:v',
        'libx264',
        '-preset',
        'ultrafast',
        '-tune',
        'zerolatency',
        '-g',
        '25',
        '-sc_threshold',
        '0',
        '-c:a',
        'aac',
        '-f',
        'hls',
        '-hls_time',
        '1',
        '-hls_list_size',
        '5',
        '-hls_flags',
        'delete_segments',
        str(output_path),
    ]


class StreamManager:
    def __init__(self, max_concurrent: int = 4, hls_base: Path | None = None):
        self._max_concurrent = max_concurrent
        self._hls_base = Path(hls_base) if hls_base is not None else None
        self._streams: dict[str, StreamInfo] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._lock = asyncio.Lock()

    def get(self, camera_mac: str) -> StreamInfo:
        return self._streams.get(camera_mac, StreamInfo(camera_mac=camera_mac))

    def list(self) -> list[StreamInfo]:
        return list(self._streams.values())

    def hls_dir_for(self, camera_mac: str) -> Path | None:
        """Return the HLS output directory for a camera, or None if HLS isn't configured."""
        if self._hls_base is None:
            return None
        info = self._streams.get(camera_mac)
        if info is None or info.state not in (StreamState.RUNNING, StreamState.STARTING):
            return None
        return self._hls_base / _mac_to_dir(camera_mac)

    async def start(
        self,
        camera_mac: str,
        launcher: StreamLauncher,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> StreamInfo:
        async with self._lock:
            existing = self._streams.get(camera_mac)
            if existing and existing.state in (StreamState.STARTING, StreamState.RUNNING):
                raise RuntimeError(f'Stream for {camera_mac} already in state {existing.state}')
            running_count = sum(1 for s in self._streams.values() if s.state == StreamState.RUNNING)
            if running_count >= self._max_concurrent:
                raise RuntimeError(f'Max concurrent streams ({self._max_concurrent}) reached')
            self._streams[camera_mac] = StreamInfo(
                camera_mac=camera_mac,
                state=StreamState.STARTING,
                started_at=datetime.now(),  # noqa: DTZ005 - in-process only
            )

        try:
            process, is_ready = launcher()
        except Exception as e:
            self._streams[camera_mac] = StreamInfo(
                camera_mac=camera_mac,
                state=StreamState.FAILED,
                started_at=self._streams[camera_mac].started_at,
                error=str(e),
            )
            raise

        self._processes[camera_mac] = process
        self._streams[camera_mac].pid = process.pid

        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            retcode = process.poll()
            if retcode is not None:
                self._streams[camera_mac].state = StreamState.FAILED
                self._streams[camera_mac].error = f'Process exited with code {retcode}'
                self._processes.pop(camera_mac, None)
                raise RuntimeError(f'Stream for {camera_mac} failed: exited with code {retcode}')
            if is_ready():
                self._streams[camera_mac].state = StreamState.RUNNING
                self._streams[camera_mac].last_active_at = datetime.now()  # noqa: DTZ005 - in-process only
                return self._streams[camera_mac]
            await asyncio.sleep(poll_interval)

        # Timed out waiting for readiness
        self._streams[camera_mac].state = StreamState.FAILED
        self._streams[camera_mac].error = f'Stream did not become ready within {timeout}s'
        self._terminate(process)
        self._processes.pop(camera_mac, None)
        raise TimeoutError(self._streams[camera_mac].error or 'stream not ready')

    async def start_hls(
        self,
        camera_mac: str,
        rtsp_url: str,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
        is_ready: Callable[[], bool] | None = None,
    ) -> StreamInfo:
        """Start an HLS pipeline for `camera_mac` and register the resulting
        subprocess with the manager. Cleans any prior HLS output before launch
        and considers the stream ready once `index.m3u8` appears on disk.
        `is_ready` is injectable for tests; production callers leave it None.
        """
        if self._hls_base is None:
            raise RuntimeError('HLS base directory not configured on StreamManager')

        cam_dir = self._hls_base / _mac_to_dir(camera_mac)
        # Each fresh start gets a clean playlist (Windows stop rmtree can silently fail)
        if cam_dir.exists():
            shutil.rmtree(cam_dir, ignore_errors=True)
        cam_dir.mkdir(parents=True, exist_ok=True)

        m3u8 = cam_dir / 'index.m3u8'
        default_readiness: Callable[[], bool] = lambda: m3u8.exists()
        readiness = is_ready if is_ready is not None else default_readiness

        def launcher() -> tuple[subprocess.Popen, Callable[[], bool]]:
            cmd = _build_hls_cmd(rtsp_url, m3u8)
            stderr_path = cam_dir / 'ffmpeg.log'
            stderr_file = open(stderr_path, 'w')
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=stderr_file)
            stderr_file.close()
            return proc, readiness

        return await self.start(camera_mac, launcher, timeout, poll_interval)

    async def stop(self, camera_mac: str) -> None:
        process = self._processes.pop(camera_mac, None)
        if process is not None:
            self._terminate(process)
        if camera_mac in self._streams:
            self._streams[camera_mac].state = StreamState.IDLE
            self._streams[camera_mac].pid = None
        # Clean HLS output directory on stop so stale segments don't linger
        if self._hls_base is not None:
            cam_dir = self._hls_base / _mac_to_dir(camera_mac)
            if cam_dir.exists():
                shutil.rmtree(cam_dir, ignore_errors=True)

    async def stop_all(self) -> None:
        for mac in list(self._processes.keys()):
            await self.stop(mac)

    def mark_stalled(self, camera_mac: str) -> None:
        info = self._streams.get(camera_mac)
        if info is not None:
            info.state = StreamState.STALLED

    def mark_running(self, camera_mac: str) -> None:
        info = self._streams.get(camera_mac)
        if info is not None:
            info.state = StreamState.RUNNING
            info.last_active_at = datetime.now()  # noqa: DTZ005 - in-process only

    @staticmethod
    def _terminate(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            try:
                process.kill()
                process.wait(timeout=3)
            except (subprocess.TimeoutExpired, OSError):
                pass

"""StreamManager — unified ffmpeg process lifecycle for cameras.

Owns per-camera stream state and a process table so recording and future
pipelines share one place to start, stop, and observe camera streams.
"""

import asyncio
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
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


class StreamManager:
    def __init__(self, max_concurrent: int = 4):
        self._max_concurrent = max_concurrent
        self._streams: dict[str, StreamInfo] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._lock = asyncio.Lock()

    def get(self, camera_mac: str) -> StreamInfo:
        return self._streams.get(camera_mac, StreamInfo(camera_mac=camera_mac))

    def list(self) -> list[StreamInfo]:
        return list(self._streams.values())

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

    async def stop(self, camera_mac: str) -> None:
        process = self._processes.pop(camera_mac, None)
        if process is not None:
            self._terminate(process)
        if camera_mac in self._streams:
            self._streams[camera_mac].state = StreamState.IDLE
            self._streams[camera_mac].pid = None

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

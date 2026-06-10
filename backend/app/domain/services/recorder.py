"""Camera recording via a single long-running FFmpeg segment muxer (Frigate-style).

One FFmpeg process writes ``{mac}_{ts}_seg%03d.mp4`` files. The monitor loop
detects completed segments when the next file appears (or when the process
stops) and invokes callbacks so each segment gets its own DB row.

FFmpeg flags follow Frigate ``preset-rtsp-generic`` plus a record output preset
selected by ``RecordingParams.audio_mode`` (default ``aac`` for G.711 cameras).
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from loguru import logger

# Stream stall: no bytes written to the active segment for this long → restart session
STALL_THRESHOLD_SECONDS = 90
# Frigate allows ~90s for ffmpeg to produce the first segment after start
STARTUP_GRACE_SECONDS = 90
MONITOR_INTERVAL_SECONDS = 5
MIN_VALID_BYTES = 10 * 1024
# Graceful quit before SIGTERM / kill
FFMPEG_QUIT_TIMEOUT_SECONDS = 10
FFMPEG_TERM_TIMEOUT_SECONDS = 5
_SEGMENT_INDEX_RE = re.compile(r'_seg(\d+)\.mp4$')


@dataclass
class RecordingParams:
    resolution: str = '1920x1080'
    segment_seconds: int = 1800
    bitrate: int | None = None  # kbps — ignored in copy mode, kept for preset API
    fps: int | None = None
    # Frigate record presets: 'aac' (default, G.711/pcm cameras), 'copy' (native AAC), 'none'
    audio_mode: str = 'aac'

    def bitrate_or_default(self) -> int:
        if self.bitrate:
            return self.bitrate
        w = int(self.resolution.split('x')[0])
        if w >= 1920:
            return 2048
        if w >= 1280:
            return 1024
        return 512

    def fps_or_default(self) -> int:
        return self.fps or 25


@dataclass
class RecordingTask:
    """Per-segment view passed to domain callbacks (stable interface)."""

    camera_mac: str
    output_path: Path
    started_at: datetime
    segment_seconds: int
    rtsp_url: str
    segment_index: int
    params: RecordingParams
    recording_id: int | None = None
    session_recording_id: int | None = None
    process: subprocess.Popen | None = None


@dataclass
class RecordingSession:
    camera_mac: str
    process: subprocess.Popen
    output_pattern: Path  # path containing ``%03d``, e.g. MAC_ts_seg%03d.mp4
    session_started_at: datetime
    segment_seconds: int
    rtsp_url: str
    params: RecordingParams
    recording_id: int | None = None
    session_recording_id: int | None = None
    next_db_segment_index: int = 0
    finalized_paths: set[str] = field(default_factory=set)
    file_start_times: dict[str, datetime] = field(default_factory=dict)
    segment_started_at: dict[int, datetime] = field(default_factory=dict)
    last_check: datetime | None = None
    last_stall_bytes: int = 0

    @property
    def output_path(self) -> Path:
        """Latest segment path (for callers that read ``task.output_path``)."""
        files = list_segment_files(self.output_pattern)
        return files[-1] if files else self.output_pattern

    def to_segment_task(self, segment_index: int, path: Path) -> RecordingTask:
        started = self.file_start_times.get(str(path))
        if started is None:
            started = self.segment_started_at.get(segment_index, self.session_started_at)
        return RecordingTask(
            camera_mac=self.camera_mac,
            process=self.process,
            output_path=path,
            started_at=started,
            segment_seconds=self.segment_seconds,
            rtsp_url=self.rtsp_url,
            recording_id=self.recording_id,
            session_recording_id=self.session_recording_id,
            segment_index=segment_index,
            params=self.params,
        )


def segment_index_from_path(path: Path) -> int:
    match = _SEGMENT_INDEX_RE.search(path.name)
    return int(match.group(1)) if match else 0


def list_segment_files(output_pattern: Path) -> list[Path]:
    glob_name = output_pattern.name.replace('%03d', '*')
    return sorted(output_pattern.parent.glob(glob_name))


def completed_segment_paths(session: RecordingSession) -> list[Path]:
    """Return segment files that are fully written and ready to finalize.

    While FFmpeg is still running, only segments *before* the active (last) file
    are complete — the last file is still being written and must not be synced.
    """
    files = list_segment_files(session.output_pattern)
    if not files:
        return []

    process_alive = session.process.poll() is None
    if process_alive:
        if len(files) < 2:
            return []
        candidates = files[:-1]
    else:
        candidates = files

    return [p for p in candidates if str(p) not in session.finalized_paths]


class Recorder:
    def __init__(self, temp_dir: str):
        self.temp_dir = Path(temp_dir).resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.active: dict[str, RecordingSession] = {}
        self._monitor_task: asyncio.Task | None = None
        self._on_complete_cb = None
        self._on_failed_cb = None
        self._should_continue_cb = None

    def set_callbacks(self, on_complete=None, on_failed=None, should_continue=None, **_kwargs):
        """Register domain callbacks. ``create_next_recording`` is deprecated (no-op)."""
        self._on_complete_cb = on_complete
        self._on_failed_cb = on_failed
        self._should_continue_cb = should_continue

    async def start_monitor(self):
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info('RecordingMonitor 已启动')

    async def stop_monitor(self):
        if self._monitor_task:
            self._monitor_task.cancel()
            logger.info('RecordingMonitor 已停止')

    async def start_recording(self, camera_mac: str, rtsp_url: str, params: RecordingParams) -> str:
        if camera_mac in self.active:
            raise RuntimeError(f'摄像头 {camera_mac} 已在录制中')

        session = await self._launch_session(camera_mac, rtsp_url, params)
        logger.info(f'启动录制: {camera_mac} → {session.output_pattern}')
        return str(session.output_pattern)

    async def _launch_session(
        self,
        camera_mac: str,
        rtsp_url: str,
        params: RecordingParams,
        recording_id: int | None = None,
        session_recording_id: int | None = None,
    ) -> RecordingSession:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')  # noqa: DTZ005
        safe_mac = camera_mac.replace(':', '')
        output_pattern = self.temp_dir / f'{safe_mac}_{ts}_seg%03d.mp4'
        cmd = self._build_ffmpeg_cmd(rtsp_url, output_pattern, params)

        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            ),
        )
        now = datetime.now()  # noqa: DTZ005
        session = RecordingSession(
            camera_mac=camera_mac,
            process=proc,
            output_pattern=output_pattern,
            session_started_at=now,
            segment_seconds=params.segment_seconds,
            rtsp_url=rtsp_url,
            recording_id=recording_id,
            session_recording_id=session_recording_id,
            params=params,
        )
        self.active[camera_mac] = session
        return session

    def _record_output_args(self, params: RecordingParams) -> list[str]:
        """Frigate record output presets — see ``PRESETS_RECORD_OUTPUT``."""
        mode = params.audio_mode
        if mode == 'copy':
            return ['-c', 'copy']
        if mode == 'none':
            return ['-map', '0:v:0', '-c:v', 'copy', '-an']
        # preset-record-generic-audio-aac: transcode G.711/pcm to AAC for MP4
        return ['-map', '0:v:0', '-map', '0:a:0?', '-c:v', 'copy', '-c:a', 'aac']

    def _build_ffmpeg_cmd(
        self, rtsp_url: str, output_pattern: Path, params: RecordingParams
    ) -> list:
        # Frigate preset-rtsp-generic input + record output preset (audio_mode).
        # Do NOT use movflags=empty_moov — it prevents a clean moov on graceful stop.
        return [
            'ffmpeg',
            '-hide_banner',
            '-loglevel',
            'warning',
            '-y',
            '-avoid_negative_ts',
            'make_zero',
            '-fflags',
            '+genpts+discardcorrupt',
            '-rtsp_transport',
            'tcp',
            '-timeout',
            '10000000',
            '-use_wallclock_as_timestamps',
            '1',
            '-i',
            rtsp_url,
            *self._record_output_args(params),
            '-f',
            'segment',
            '-segment_time',
            str(params.segment_seconds),
            '-segment_format',
            'mp4',
            '-reset_timestamps',
            '1',
            str(output_pattern),
        ]

    async def stop_recording(self, camera_mac: str) -> Path | None:
        session = self.active.pop(camera_mac, None)
        if not session:
            return None

        logger.info(f'停止录制: {camera_mac}')
        self._terminate_ffmpeg(session.process, camera_mac)
        await asyncio.sleep(1.0)

        try:
            if session.process.stderr:
                stderr_out = session.process.stderr.read(8192).decode(errors='replace').strip()
                if stderr_out:
                    logger.debug(f'FFmpeg stderr [{camera_mac}]: {stderr_out[-300:]}')
        except OSError as e:
            logger.debug(f'读取 FFmpeg stderr 失败 [{camera_mac}]: {e}')

        last_path = await self._finalize_all_remaining_segments(session, keep_recording=False)
        return last_path

    @staticmethod
    def _terminate_ffmpeg(proc: subprocess.Popen, camera_mac: str) -> None:
        if proc.poll() is not None:
            return
        try:
            if proc.stdin:
                proc.stdin.write(b'q')
                proc.stdin.flush()
                proc.stdin.close()
        except OSError as e:
            logger.debug(f'向 FFmpeg stdin 发送 quit 信号失败: {e}')
        try:
            proc.wait(timeout=FFMPEG_QUIT_TIMEOUT_SECONDS)
            return
        except subprocess.TimeoutExpired:
            pass
        logger.warning(
            f'FFmpeg 未在{FFMPEG_QUIT_TIMEOUT_SECONDS}秒内退出，发送 SIGTERM: {camera_mac}'
        )
        try:
            proc.terminate()
            proc.wait(timeout=FFMPEG_TERM_TIMEOUT_SECONDS)
            return
        except (subprocess.TimeoutExpired, OSError):
            pass
        logger.warning(f'FFmpeg 未响应 SIGTERM，强制终止: {camera_mac}')
        try:
            proc.kill()
            proc.wait(timeout=FFMPEG_TERM_TIMEOUT_SECONDS)
        except (subprocess.TimeoutExpired, OSError):
            logger.error(f'FFmpeg 强制终止失败: {camera_mac}')

    async def _finalize_segment_path(
        self, session: RecordingSession, path: Path, *, keep_recording: bool
    ) -> Path | None:
        path_key = str(path)
        if path_key in session.finalized_paths:
            return None

        exists = await asyncio.to_thread(path.exists)
        if not exists:
            logger.warning(f'[{session.camera_mac}] segment 文件不存在: {path}')
            session.finalized_paths.add(path_key)
            return None

        for attempt in range(5):
            try:
                size = await asyncio.to_thread(lambda: path.stat().st_size)
                if size <= MIN_VALID_BYTES:
                    logger.warning(f'录制文件过小({size}字节，丢弃): {path}')
                    await asyncio.to_thread(path.unlink, missing_ok=True)
                    session.finalized_paths.add(path_key)
                    return None
                break
            except PermissionError:
                if attempt < 4:
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f'文件持续被占用，跳过: {path}')
                    session.finalized_paths.add(path_key)
                    return None

        db_index = session.next_db_segment_index
        session.next_db_segment_index += 1
        session.finalized_paths.add(path_key)
        task = session.to_segment_task(db_index, path)
        if self._on_complete_cb:
            try:
                await self._on_complete_cb(task, keep_recording=keep_recording)
            except Exception as e:  # noqa: BLE001
                logger.error(f'[{session.camera_mac}] segment {db_index} 持久化失败: {e}')
        logger.info(
            f'[{session.camera_mac}] segment {db_index} 已落盘: {path.name} '
            f'(keep_recording={keep_recording})'
        )
        return path

    async def _finalize_all_remaining_segments(
        self, session: RecordingSession, *, keep_recording: bool
    ) -> Path | None:
        """Finalize every segment file not yet persisted (used after FFmpeg stops)."""
        last_path: Path | None = None
        for path in list_segment_files(session.output_pattern):
            if str(path) not in session.finalized_paths:
                last_path = await self._finalize_segment_path(
                    session, path, keep_recording=keep_recording
                )
        return last_path

    async def _finalize_session_segments(
        self, session: RecordingSession, *, keep_recording: bool
    ) -> Path | None:
        last_path: Path | None = None
        for path in completed_segment_paths(session):
            last_path = await self._finalize_segment_path(
                session, path, keep_recording=keep_recording
            )
        return last_path

    async def _should_continue(self, camera_mac: str) -> bool:
        if not self._should_continue_cb:
            return False
        try:
            return await self._should_continue_cb(camera_mac)
        except Exception:  # noqa: BLE001
            logger.warning(f'[{camera_mac}] should_continue_cb 异常，降级为 False')
            return False

    async def _handle_stalled_session(self, session: RecordingSession) -> None:
        mac = session.camera_mac
        logger.warning(f'[{mac}] RTSP流中断（{STALL_THRESHOLD_SECONDS}s无数据写入），终止并尝试重启')

        self._terminate_ffmpeg(session.process, mac)
        self.active.pop(mac, None)
        await asyncio.sleep(0.5)

        files = list_segment_files(session.output_pattern)
        if files:
            stalled_path = files[-1]
            db_index = session.next_db_segment_index
            session.next_db_segment_index += 1
            task = session.to_segment_task(db_index, stalled_path)
            if self._on_failed_cb:
                await self._on_failed_cb(
                    task, -1, 'RTSP stream stalled, auto-restart', keep_recording=True
                )
            session.finalized_paths.add(str(stalled_path))

        if not await self._should_continue(mac):
            logger.info(f'[{mac}] 流中断但不应继续录制，跳过重启')
            return

        session_rec_id = session.session_recording_id or session.recording_id
        new_session = await self._launch_session(
            mac,
            session.rtsp_url,
            session.params,
            recording_id=session.recording_id,
            session_recording_id=session_rec_id,
        )
        new_session.next_db_segment_index = session.next_db_segment_index
        logger.info(
            f'[{mac}] 立即重启录制 session，下一段 DB index={new_session.next_db_segment_index}'
        )

    async def _check_session_stall(self, session: RecordingSession, now: datetime) -> bool:
        """Return True if the session was handled as stalled (caller should continue)."""
        files = list_segment_files(session.output_pattern)
        if not files:
            return False
        for f in files:
            fkey = str(f)
            if fkey not in session.file_start_times:
                session.file_start_times[fkey] = now
        active_path = files[-1]
        try:
            current_bytes = await asyncio.to_thread(lambda: active_path.stat().st_size)
        except OSError as e:
            logger.debug(f'stall 检测异常 [{session.camera_mac}]: {e}')
            return False

        if session.last_check is None:
            session.last_stall_bytes = current_bytes
            session.last_check = now
            return False

        elapsed = (now - session.last_check).total_seconds()
        grew = current_bytes - session.last_stall_bytes
        session_age = (now - session.session_started_at).total_seconds()
        in_grace = session_age < STARTUP_GRACE_SECONDS

        if (
            not in_grace
            and elapsed >= STALL_THRESHOLD_SECONDS
            and grew == 0
            and current_bytes > 0
        ):
            await self._handle_stalled_session(session)
            return True

        session.last_stall_bytes = current_bytes
        session.last_check = now
        return False

    async def _monitor_loop(self):
        while True:
            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
            now = datetime.now()  # noqa: DTZ005

            for mac, session in list(self.active.items()):
                retcode = session.process.poll()
                if retcode is not None:
                    self.active.pop(mac, None)
                    if retcode == 0:
                        logger.info(f'录制进程正常结束: {mac}')
                        await self._finalize_all_remaining_segments(session, keep_recording=False)
                    else:
                        stderr = session.process.stderr.read().decode(errors='replace')[-500:]
                        logger.error(f'录制异常退出: {mac}, code={retcode}, stderr={stderr}')
                        files = list_segment_files(session.output_pattern)
                        if files:
                            idx = segment_index_from_path(files[-1])
                            task = session.to_segment_task(idx, files[-1])
                            if self._on_failed_cb:
                                await self._on_failed_cb(task, retcode, stderr)
                    continue

                # Finalize segments whose successor file has appeared
                still_recording = await self._should_continue(mac)
                for path in completed_segment_paths(session):
                    await self._finalize_segment_path(
                        session, path, keep_recording=still_recording
                    )

                if not still_recording:
                    logger.info(f'[{mac}] is_recording=False，自动停止录制')
                    await self.stop_recording(mac)
                    continue

                if await self._check_session_stall(session, now):
                    continue

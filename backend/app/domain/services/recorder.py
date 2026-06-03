import asyncio
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from loguru import logger


@dataclass
class RecordingParams:
    resolution: str = '1920x1080'
    segment_seconds: int = 1800
    bitrate: int | None = None  # kbps
    fps: int | None = None

    def bitrate_or_default(self) -> int:
        if self.bitrate:
            return self.bitrate
        # 自动匹配：基于分辨率
        w = int(self.resolution.split('x')[0])
        if w >= 1920:
            return 2048
        elif w >= 1280:
            return 1024
        else:
            return 512

    def fps_or_default(self) -> int:
        return self.fps or 25


# 流中断判定：若无数据写入超过此秒数，认为流已中断
STALL_THRESHOLD_SECONDS = 90


@dataclass
class RecordingTask:
    camera_mac: str
    process: subprocess.Popen
    output_path: Path
    started_at: datetime
    segment_seconds: int
    rtsp_url: str
    recording_id: int | None = None  # pending row id (used for DB lookup)
    session_recording_id: int | None = None  # parent session id (stable across segments)
    last_bytes: int = 0
    last_check: datetime | None = None
    session_start: datetime | None = None
    segment_index: int = 0
    params: RecordingParams = field(default_factory=RecordingParams)


class Recorder:
    def __init__(self, temp_dir: str):
        self.temp_dir = Path(temp_dir).resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.active: dict[str, RecordingTask] = {}
        self._completed_indices: dict[str, set[int]] = {}  # mac -> {completed segment indices}
        self._completed_tasks: dict[
            str, dict[int, RecordingTask]
        ] = {}  # mac -> {segment_index: task} for segments completed but not yet stop_recording'd
        self._monitor_task: asyncio.Task | None = None
        self._on_complete_cb = None
        self._on_failed_cb = None
        self._should_continue_cb = None
        self._create_next_recording_cb = None

    def set_callbacks(
        self, on_complete=None, on_failed=None, should_continue=None, create_next_recording=None
    ):
        self._on_complete_cb = on_complete
        self._on_failed_cb = on_failed
        self._should_continue_cb = should_continue
        self._create_next_recording_cb = create_next_recording

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

        task = await self._launch_segment(
            camera_mac=camera_mac,
            rtsp_url=rtsp_url,
            params=params,
            segment_index=0,
        )
        logger.info(f'启动录制: {camera_mac} → {task.output_path}')
        return str(task.output_path)

    async def _launch_segment(
        self,
        camera_mac: str,
        rtsp_url: str,
        params: RecordingParams,
        segment_index: int,
        recording_id: int | None = None,
        session_recording_id: int | None = None,
    ) -> RecordingTask:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')  # noqa: DTZ005 - filename timestamp, not DB
        safe_mac = camera_mac.replace(':', '')
        suffix = '' if segment_index == 0 else f'_seg{segment_index}'
        output_path = self.temp_dir / f'{safe_mac}_{ts}{suffix}.mp4'
        cmd = self._build_ffmpeg_cmd(rtsp_url, output_path, params)

        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            ),
        )
        task = RecordingTask(
            camera_mac=camera_mac,
            process=proc,
            output_path=output_path,
            started_at=datetime.now(),  # noqa: DTZ005 - written to Recording.started_at (naive DateTime)
            segment_seconds=params.segment_seconds,
            rtsp_url=rtsp_url,
            recording_id=recording_id,
            session_recording_id=session_recording_id,
            session_start=datetime.now(),  # noqa: DTZ005 - in-process only, kept consistent for subtraction
            segment_index=segment_index,
            params=params,
        )
        self.active[camera_mac] = task
        return task

    async def _allocate_next_recording_id(self, camera_mac: str) -> int | None:
        if not self._create_next_recording_cb:
            return None
        try:
            return await self._create_next_recording_cb(camera_mac)
        except Exception as exc:  # noqa: BLE001 - injected callback may throw anything
            logger.error(f'[{camera_mac}] 创建续录记录失败: {exc}')
            return None

    async def _restart_segment(
        self,
        task: RecordingTask,
        next_index: int,
        recording_id: int | None = None,
        session_recording_id: int | None = None,
    ) -> RecordingTask:
        new_task = await self._launch_segment(
            camera_mac=task.camera_mac,
            rtsp_url=task.rtsp_url,
            params=task.params,
            segment_index=next_index,
            recording_id=recording_id if recording_id is not None else task.recording_id,
            session_recording_id=session_recording_id
            if session_recording_id is not None
            else task.session_recording_id,
        )
        return new_task

    def _build_ffmpeg_cmd(self, rtsp_url: str, output_path: Path, params: RecordingParams) -> list:
        return [
            'ffmpeg',
            '-y',
            '-rtsp_transport',
            'tcp',
            '-i',
            rtsp_url,
            '-c:v',
            'copy',
            '-c:a',
            'aac',
            '-t',
            str(params.segment_seconds),
            '-movflags',
            '+frag_keyframe+empty_moov',
            str(output_path),
        ]

    async def stop_recording(self, camera_mac: str) -> Path | None:
        # Collect all completed segment indices and task objects before we clear active
        completed_indices = self._completed_indices.pop(camera_mac, set())
        completed_tasks = self._completed_tasks.pop(camera_mac, {})

        # Persist each segment that _monitor_loop completed but didn't finalize.
        # Segments in completed_indices were already handled by _monitor_loop with
        # keep_recording=True (Recording row created). Skip them to avoid duplicates.
        # Segments NOT in completed_indices (should_continue=False path) need to be
        # persisted now with keep_recording=False.
        for seg_idx, seg_task in completed_tasks.items():
            if seg_idx in completed_indices:
                # Already persisted by _monitor_loop; skip
                continue
            # should_continue=False path: _monitor_loop created Recording row but did
            # not add to _completed_indices. Call on_complete_cb now to finalize it.
            if self._on_complete_cb:
                try:
                    await self._on_complete_cb(seg_task, keep_recording=False)
                except Exception as e:  # noqa: BLE001 - injected callback may throw anything
                    logger.error(f'停止录制时持久化segment {seg_idx} 失败: {e}')

        task = self.active.pop(camera_mac, None)
        if not task:
            return None
        logger.info(f'停止录制: {camera_mac}')

        self._terminate_ffmpeg(task.process, camera_mac)
        await asyncio.sleep(1.0)

        # Read stderr for diagnostics
        try:
            if task.process.stderr:
                stderr_out = task.process.stderr.read(8192).decode(errors='replace').strip()
                if stderr_out:
                    logger.debug(f'FFmpeg stderr [{camera_mac}]: {stderr_out[-300:]}')
        except OSError as e:
            logger.debug(f'读取 FFmpeg stderr 失败 [{camera_mac}]: {e}')

        min_valid_bytes = 10 * 1024
        for attempt in range(5):
            try:
                if not task.output_path.exists():
                    logger.warning(f'录制文件不存在（FFmpeg未写入数据）: {task.output_path}')
                    return None
                size = task.output_path.stat().st_size
                if size > min_valid_bytes:
                    # Flush this segment to DB via on_complete_cb so no segment data is lost
                    if self._on_complete_cb:
                        await self._on_complete_cb(task, keep_recording=False)
                    return task.output_path
                logger.warning(f'录制文件过小({size}字节，丢弃): {task.output_path}')
                task.output_path.unlink(missing_ok=True)
                return None
            except PermissionError:
                if attempt < 4:
                    logger.warning(f'文件被占用，重试 ({attempt + 1}/5): {task.output_path}')
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f'文件持续被占用，跳过: {task.output_path}')
                    return None
        return None

    @staticmethod
    def _terminate_ffmpeg(proc: subprocess.Popen, camera_mac: str) -> None:
        """Terminate ffmpeg gracefully, then forcefully if needed."""
        if proc.poll() is not None:
            return
        # Best-effort graceful stop via stdin
        try:
            if proc.stdin:
                proc.stdin.write(b'q')
                proc.stdin.flush()
                proc.stdin.close()
        except OSError as e:
            logger.debug(f'向 FFmpeg stdin 发送 quit 信号失败: {e}')
        # Wait briefly for graceful exit
        try:
            proc.wait(timeout=3)
            return
        except subprocess.TimeoutExpired:
            pass
        # Force kill
        logger.warning(f'FFmpeg 未在3秒内退出，强制终止: {camera_mac}')
        try:
            proc.kill()
            proc.wait(timeout=3)
        except (subprocess.TimeoutExpired, OSError):
            logger.error(f'FFmpeg 强制终止失败: {camera_mac}')

    async def _monitor_loop(self):
        while True:
            await asyncio.sleep(10)
            now = datetime.now()  # noqa: DTZ005 - in-process only, kept naive for consistency with task.last_check
            finished = []
            stalled = []
            for mac, task in list(self.active.items()):
                retcode = task.process.poll()
                if retcode is not None:
                    finished.append((mac, retcode, task))
                    continue
                # Stream health check: detect RTSP disconnection
                try:
                    if task.output_path.exists():
                        current_bytes = task.output_path.stat().st_size
                        if task.last_check is not None:
                            elapsed = (now - task.last_check).total_seconds()
                            grew = current_bytes - task.last_bytes
                            # If no growth for 90s, stream is dead — terminate segment
                            if (
                                elapsed >= STALL_THRESHOLD_SECONDS
                                and grew == 0
                                and current_bytes > 0
                            ):
                                stalled.append((mac, task))
                                continue
                        task.last_bytes = current_bytes
                        task.last_check = now
                except OSError as e:
                    logger.debug(f'stall 检测异常 [{mac}]: {e}')
            # Handle stalled streams — kill then immediately restart new segment
            for mac, task in stalled:
                logger.warning(f'[{mac}] RTSP流中断（90s无数据写入），终止segment并立即重启')
                self._terminate_ffmpeg(task.process, mac)
                self.active.pop(mac, None)
                # Record completed segment so stop_recording skips it (even though it's a failed segment)
                completed = self._completed_indices.setdefault(mac, set())
                completed.add(task.segment_index)
                # Fire on_failed so DB records this segment (completed if ≥30s, failed otherwise)
                if self._on_failed_cb:
                    await self._on_failed_cb(
                        task, -1, 'RTSP stream stalled, auto-restart', keep_recording=True
                    )
                # Check should_continue_cb before restarting new segment
                try:
                    should_continue = (
                        await self._should_continue_cb(mac) if self._should_continue_cb else True
                    )
                except Exception:  # noqa: BLE001 - injected callback may throw anything
                    logger.warning(f'[{mac}] should_continue_cb 异常，降级为True')
                    should_continue = True
                if not should_continue:
                    logger.info(f'[{mac}] 流中断但不应继续录制，跳过重启')
                    continue
                # Immediately start next segment — same camera, same session
                next_index = task.segment_index + 1
                session_rec_id = task.session_recording_id or task.recording_id
                new_recording_id = await self._allocate_next_recording_id(mac)
                new_task = await self._restart_segment(
                    task, next_index, new_recording_id, session_recording_id=session_rec_id
                )
                self.active[mac] = new_task
                logger.info(f'[{mac}] 立即重启segment {next_index}: {new_task.output_path}')
            # Handle normally finished
            for mac, retcode, task in finished:
                self.active.pop(mac, None)
                if retcode == 0:
                    logger.info(f'录制正常完成: {mac}')
                    # Check should_continue_cb to decide whether to auto-continue
                    try:
                        should_continue = (
                            await self._should_continue_cb(mac)
                            if self._should_continue_cb
                            else False
                        )
                    except Exception:  # noqa: BLE001 - injected callback may throw anything
                        logger.warning(f'[{mac}] should_continue_cb 异常，降级为False')
                        should_continue = False
                    if should_continue:
                        # Record this segment index as completed so stop_recording skips it
                        completed = self._completed_indices.setdefault(mac, set())
                        completed.add(task.segment_index)
                        # Persist this completed segment BEFORE incrementing segment_index,
                        # so on_complete_cb stores the correct segment_index in the DB.
                        original_seg_index = task.segment_index
                        if self._on_complete_cb:
                            await self._on_complete_cb(task, keep_recording=True)
                        # Store task object so stop_recording can call on_complete_cb for this segment
                        completed_tasks = self._completed_tasks.setdefault(mac, {})
                        completed_tasks[original_seg_index] = task
                        # Capture session recording_id from first segment; propagate through restarts
                        session_rec_id = task.session_recording_id or task.recording_id
                        task.segment_index = task.segment_index + 1
                        next_index = task.segment_index
                        new_recording_id = await self._allocate_next_recording_id(mac)
                        new_task = await self._restart_segment(
                            task, next_index, new_recording_id, session_recording_id=session_rec_id
                        )
                        self.active[mac] = new_task
                        logger.info(
                            f'[{mac}] 自动继续录制segment {next_index}: {new_task.output_path}'
                        )
                    else:
                        # should_continue=False: _monitor_loop calls on_complete_cb directly.
                        # Track this segment so stop_recording skips it (Recording already created).
                        completed = self._completed_indices.setdefault(mac, set())
                        completed.add(task.segment_index)
                        completed_tasks = self._completed_tasks.setdefault(mac, {})
                        completed_tasks[task.segment_index] = task
                        if self._on_complete_cb:
                            await self._on_complete_cb(task)
                        # Do NOT restart a new segment when should_continue=False
                else:
                    stderr = task.process.stderr.read().decode(errors='replace')[-500:]
                    logger.error(f'录制异常退出: {mac}, code={retcode}, stderr={stderr}')
                    if self._on_failed_cb:
                        await self._on_failed_cb(task, retcode, stderr)

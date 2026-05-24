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
    recording_id: int | None = None
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
        self._monitor_task: asyncio.Task | None = None
        self._on_complete_cb = None
        self._on_failed_cb = None
        self._should_continue_cb = None

    def set_callbacks(self, on_complete=None, on_failed=None, should_continue=None):
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

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_mac = camera_mac.replace(':', '')
        output_path = self.temp_dir / f'{safe_mac}_{ts}.mp4'

        cmd = self._build_ffmpeg_cmd(rtsp_url, output_path, params)

        logger.info(f'启动录制: {camera_mac} → {output_path}')
        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            ),
        )

        self.active[camera_mac] = RecordingTask(
            camera_mac=camera_mac,
            process=proc,
            output_path=output_path,
            started_at=datetime.now(),
            segment_seconds=params.segment_seconds,
            rtsp_url=rtsp_url,
            session_start=datetime.now(),
            segment_index=0,
            params=params,
        )
        return str(output_path)

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
        except Exception:
            pass

        min_valid_bytes = 10 * 1024
        for attempt in range(5):
            try:
                if not task.output_path.exists():
                    logger.warning(f'录制文件不存在（FFmpeg未写入数据）: {task.output_path}')
                    return None
                size = task.output_path.stat().st_size
                if size > min_valid_bytes:
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
        except Exception:
            pass
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
            now = datetime.now()
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
                except Exception:
                    pass
            # Handle stalled streams — kill then immediately restart new segment
            for mac, task in stalled:
                logger.warning(f'[{mac}] RTSP流中断（90s无数据写入），终止segment并立即重启')
                self._terminate_ffmpeg(task.process, mac)
                # Fire on_failed so DB records this segment (completed if ≥30s, failed otherwise)
                if self._on_failed_cb:
                    await self._on_failed_cb(task, -1, 'RTSP stream stalled, auto-restart')
                # Immediately start next segment — same camera, same session
                next_index = task.segment_index + 1
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_mac = mac.replace(':', '')
                seg_path = self.temp_dir / f'{safe_mac}_{ts}_seg{next_index}.mp4'
                cmd = self._build_ffmpeg_cmd(task.rtsp_url, seg_path, task.params)
                loop = asyncio.get_event_loop()
                proc = await loop.run_in_executor(
                    None,
                    lambda: subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    ),
                )
                new_task = RecordingTask(
                    camera_mac=mac,
                    process=proc,
                    output_path=seg_path,
                    started_at=datetime.now(),
                    segment_seconds=task.segment_seconds,
                    rtsp_url=task.rtsp_url,
                    recording_id=None,
                    last_bytes=0,
                    last_check=None,
                    segment_index=next_index,
                    params=task.params,
                )
                self.active[mac] = new_task
                logger.info(f'[{mac}] 立即重启segment {next_index}: {seg_path}')
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
                    except Exception:
                        logger.warning(f'[{mac}] should_continue_cb 异常，降级为False')
                        should_continue = False
                    if should_continue:
                        # Auto-continue: start new segment with same recording_id
                        next_index = task.segment_index + 1
                        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                        safe_mac = mac.replace(':', '')
                        seg_path = self.temp_dir / f'{safe_mac}_{ts}_seg{next_index}.mp4'
                        cmd = self._build_ffmpeg_cmd(task.rtsp_url, seg_path, task.params)
                        loop = asyncio.get_event_loop()
                        proc = await loop.run_in_executor(
                            None,
                            lambda: subprocess.Popen(
                                cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE,
                            ),
                        )
                        new_task = RecordingTask(
                            camera_mac=mac,
                            process=proc,
                            output_path=seg_path,
                            started_at=datetime.now(),
                            segment_seconds=task.segment_seconds,
                            rtsp_url=task.rtsp_url,
                            recording_id=task.recording_id,
                            last_bytes=0,
                            last_check=None,
                            segment_index=next_index,
                            params=task.params,
                        )
                        self.active[mac] = new_task
                        logger.info(f'[{mac}] 自动继续录制segment {next_index}: {seg_path}')
                    elif self._on_complete_cb:
                        await self._on_complete_cb(task)
                else:
                    stderr = task.process.stderr.read().decode(errors='replace')[-500:]
                    logger.error(f'录制异常退出: {mac}, code={retcode}, stderr={stderr}')
                    if self._on_failed_cb:
                        await self._on_failed_cb(task, retcode, stderr)

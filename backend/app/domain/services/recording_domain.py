import asyncio
import shutil
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.domain.services._bg import spawn_bg
from app.domain.services.dlna_service import DLNAController
from app.models.camera import Camera
from app.models.dlna_device import DLNADevice
from app.models.recording import Recording
from app.services.nas_syncer import NasSyncer
from app.services.ws_manager import ws_manager


class RecordingDomainService:
    def __init__(self, nas_syncer: NasSyncer):
        self._nas_syncer = nas_syncer
        self._ws_manager = ws_manager
        self._bg_tasks: set[asyncio.Task] = set()

    async def create_continued_recording(self, camera_mac: str) -> int | None:
        async with AsyncSessionLocal() as db:
            cam = (
                await db.execute(select(Camera).where(Camera.device_mac == camera_mac))
            ).scalar_one_or_none()
            if not cam or not cam.is_recording:
                return None

            rec = Recording(
                camera_mac=camera_mac,
                file_path='(pending)',
                started_at=datetime.now(),  # noqa: DTZ005 - Recording.started_at is naive DateTime
                status='recording',
            )
            db.add(rec)
            await db.commit()
            await db.refresh(rec)
            return rec.id

    async def should_continue_recording(self, camera_mac: str) -> bool:
        async with AsyncSessionLocal() as db:
            cam = (
                await db.execute(select(Camera).where(Camera.device_mac == camera_mac))
            ).scalar_one_or_none()
            return cam.is_recording if cam else False

    async def on_recording_complete(self, task, keep_recording: bool = False):
        """Handle segment completion: sync to NAS, insert per-segment DB record, trigger DLNA cast."""
        loop = asyncio.get_running_loop()
        try:
            dest = await loop.run_in_executor(
                None, lambda: self._nas_syncer.sync_file(task.output_path, task.camera_mac)
            )
            file_size = dest.stat().st_size if dest.exists() else None
            dest_str = str(dest)
        except Exception as e:  # noqa: BLE001 - nas_syncer is custom module, may throw broadly
            logger.error(f'NAS同步失败 [{task.camera_mac}]: {e}')
            dest_str = str(task.output_path)
            file_size = task.output_path.stat().st_size if task.output_path.exists() else None

        ended_at = datetime.now()  # noqa: DTZ005 - Recording.ended_at is naive DateTime

        # Probe actual media duration; fallback to wall clock if unavailable
        actual_duration = None
        if task.output_path.exists():
            try:
                actual_duration = await self._probe_duration(task.output_path)
            except (OSError, subprocess.SubprocessError) as e:
                logger.debug(f'probe_duration on complete 失败 [{task.camera_mac}]: {e}')
        duration = (
            actual_duration
            if actual_duration
            else int((ended_at - task.started_at).total_seconds())
        )

        session_id = task.session_recording_id or task.recording_id

        async with AsyncSessionLocal() as db:
            # 幂等性检查：相同 recording_id + segment_index 的记录已存在则跳过
            existing = await db.execute(
                select(Recording).where(
                    Recording.recording_id == session_id,
                    Recording.segment_index == task.segment_index,
                )
            )
            rec = existing.scalar_one_or_none()
            # 如果未找到，尝试查找待更新的 pending 行（id == task.recording_id 且 segment_index 为空）
            if not rec and task.recording_id:
                pending_result = await db.execute(
                    select(Recording).where(
                        Recording.id == task.recording_id,
                        Recording.segment_index.is_(None),
                    )
                )
                rec = pending_result.scalar_one_or_none()
            # 找到了则更新已有行，否则创建新行
            if rec:
                rec.file_path = dest_str
                rec.file_size = file_size
                rec.duration = duration
                rec.started_at = task.started_at
                rec.ended_at = ended_at
                rec.status = 'completed'
                rec.segment_index = task.segment_index
                rec.recording_id = session_id
            else:
                rec = Recording(
                    camera_mac=task.camera_mac,
                    file_path=dest_str,
                    file_size=file_size,
                    duration=duration,
                    started_at=task.started_at,
                    ended_at=ended_at,
                    status='completed',
                    segment_index=task.segment_index,
                    recording_id=session_id,
                )
                db.add(rec)
            await db.commit()

        async with AsyncSessionLocal() as db:
            cam = (
                await db.execute(select(Camera).where(Camera.device_mac == task.camera_mac))
            ).scalar_one_or_none()
            if cam and cam.is_recording and not keep_recording:
                cam.is_recording = False
                await db.commit()

            if cam and cam.auto_cast_dlna:
                dlna_dev = (
                    await db.execute(select(DLNADevice).where(DLNADevice.udn == cam.auto_cast_dlna))
                ).scalar_one_or_none()
                if dlna_dev and dlna_dev.av_transport_url:
                    await self._cast_recording(dlna_dev.av_transport_url, dest_str, task.camera_mac)

        logger.info(
            f'录制完成 [{task.camera_mac}] id={session_id} seg={task.segment_index} 时长={duration}s'
        )
        await self._ws_manager.broadcast(
            'recording_completed',
            {'camera_mac': task.camera_mac, 'recording_id': session_id},
        )

    async def _probe_duration(self, path: Path) -> int | None:
        """Probe actual media duration via ffprobe. Returns None if unreachable or 0."""
        import subprocess

        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                import json

                d = json.loads(result.stdout)
                dur = float(d['format'].get('duration', 0))
                return int(dur) if dur > 0 else None
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug(f'ffprobe 失败 {path}: {e}')
        return None

    async def on_recording_failed(
        self, task, retcode: int, stderr: str, keep_recording: bool = False
    ):
        """Handle recording failure: probe actual duration, treat as completed if >= 30s."""
        actual_duration = None
        dest_str = str(task.output_path)
        loop = asyncio.get_running_loop()

        # Probe actual media duration from file
        if task.output_path.exists():
            try:
                actual_duration = await self._probe_duration(task.output_path)
            except (OSError, subprocess.SubprocessError) as e:
                logger.debug(f'probe_duration on failed 失败 [{task.camera_mac}]: {e}')

        session_id = task.session_recording_id or task.recording_id

        async with AsyncSessionLocal() as db:
            # Determine status: ≥30s actual media = completed, <30s or no probe = failed
            actual_ok = actual_duration is not None and actual_duration >= 30
            status = 'completed' if actual_ok else 'failed'
            ended_at = datetime.now()  # noqa: DTZ005 - Recording.ended_at is naive DateTime
            duration = actual_duration if actual_duration else 0

            # 幂等性检查：相同 recording_id + segment_index 的 segment 记录已存在则更新该条
            existing_seg = await db.execute(
                select(Recording).where(
                    Recording.recording_id == session_id,
                    Recording.segment_index == task.segment_index,
                )
            )
            rec = existing_seg.scalar_one_or_none()
            if not rec and task.recording_id:
                # 回退：尝试按 id 查找（兼容旧逻辑）
                result = await db.execute(
                    select(Recording).where(Recording.id == task.recording_id)
                )
                rec = result.scalar_one_or_none()

            if rec:
                rec.segment_index = task.segment_index
                rec.status = status
                rec.ended_at = ended_at
                rec.duration = duration
                rec.recording_id = session_id
                # Sync to NAS only for completed segments
                if actual_ok:
                    try:
                        sync_dest = await loop.run_in_executor(
                            None,
                            lambda: self._nas_syncer.sync_file(task.output_path, task.camera_mac),
                        )
                        rec.file_path = str(sync_dest)
                        rec.file_size = sync_dest.stat().st_size if sync_dest.exists() else None
                    except Exception as e:  # noqa: BLE001 - nas_syncer is custom module, may throw broadly
                        logger.error(f'NAS同步失败 [{task.camera_mac}]: {e}')
                        rec.file_path = dest_str
                        rec.file_size = (
                            task.output_path.stat().st_size if task.output_path.exists() else None
                        )
                else:
                    rec.file_path = dest_str
                    rec.file_size = (
                        task.output_path.stat().st_size if task.output_path.exists() else None
                    )
                    rec.error_msg = (stderr or f'退出码 {retcode}')[:500]
                logger.info(
                    f'录制异常终止 [{task.camera_mac}] id={task.recording_id}，实际时长={actual_duration}s，标记为{status}'
                )
            else:
                # recording_id is None → this segment stalled before parent was allocated.
                # Insert a new per-segment row so no segment data is lost.
                if task.output_path.exists():
                    try:
                        sync_dest = await loop.run_in_executor(
                            None,
                            lambda: self._nas_syncer.sync_file(task.output_path, task.camera_mac),
                        )
                        file_path_val = str(sync_dest)
                        file_size_val = sync_dest.stat().st_size if sync_dest.exists() else None
                    except Exception as e:  # noqa: BLE001 - nas_syncer is custom module, may throw broadly
                        logger.error(f'NAS同步失败 [{task.camera_mac}]: {e}')
                        file_path_val = dest_str
                        file_size_val = (
                            task.output_path.stat().st_size if task.output_path.exists() else None
                        )
                else:
                    file_path_val = dest_str
                    file_size_val = (
                        task.output_path.stat().st_size if task.output_path.exists() else None
                    )
                rec = Recording(
                    camera_mac=task.camera_mac,
                    file_path=file_path_val,
                    file_size=file_size_val,
                    duration=duration,
                    started_at=task.started_at,
                    ended_at=ended_at,
                    status=status,
                    segment_index=task.segment_index,
                    recording_id=session_id,
                    error_msg=(stderr or f'退出码 {retcode}')[:500] if status == 'failed' else None,
                )
                db.add(rec)
                await db.flush()
                task.recording_id = rec.id
                logger.info(
                    f'录制中断 [{task.camera_mac}] segment_index={task.segment_index}，实际时长={actual_duration}s，标记为{status}'
                )

            cam = (
                await db.execute(select(Camera).where(Camera.device_mac == task.camera_mac))
            ).scalar_one_or_none()
            if cam and cam.is_recording and not keep_recording:
                cam.is_recording = False

            await db.commit()

        await self._ws_manager.broadcast(
            'recording_completed'
            if actual_duration and actual_duration >= 30
            else 'recording_failed',
            {'camera_mac': task.camera_mac, 'recording_id': session_id},
        )

    async def _cast_recording(self, av_transport_url: str, file_path: str, camera_mac: str):
        """Copy recording to dlna-media directory and cast to target DLNA device."""
        src = Path(file_path)
        if not await asyncio.to_thread(src.exists):
            logger.warning(f'[A4] 投屏跳过，文件不存在: {file_path}')
            return

        media_dir = Path('data/dlna_media')
        await asyncio.to_thread(media_dir.mkdir, parents=True, exist_ok=True)
        fname = f'auto_{int(time.time())}_{src.name}'
        dest = media_dir / fname

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: shutil.copy2(src, dest))
        except OSError as e:
            logger.error(f'[A4] 复制录制文件到 dlna_media 失败: {e}')
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
        except OSError:
            local_ip = '127.0.0.1'

        port = get_settings().server_port
        media_url = f'http://{local_ip}:{port}/dlna-media/{fname}'

        try:
            ctrl = DLNAController(av_transport_url)
            await ctrl.set_uri(media_url)
            await ctrl.play()
            logger.info(f'[A4] 自动投屏成功: {camera_mac} → {media_url}')
        except Exception as e:  # noqa: BLE001 - DLNAController wraps third-party zeep/requests, may throw broadly
            logger.error(f'[A4] 自动投屏失败: {e}')
            return

        async def _cleanup():
            await asyncio.sleep(3600)
            dest.unlink(missing_ok=True)
            logger.info(f'[A4] DLNA 临时文件已清理: {fname}')

        spawn_bg(_cleanup(), self._bg_tasks)

import asyncio
import subprocess
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import AsyncSessionLocal
from app.domain.models.camera import Camera
from app.domain.models.device import Device
from app.domain.services.recorder import Recorder
from app.services.ws_manager import ws_manager


class CameraHealthChecker:
    def __init__(
        self,
        interval: int = 60,
        fail_threshold: int = 2,
        success_threshold: int = 2,
        session_factory: async_sessionmaker | None = None,
        recorder: Recorder | None = None,
    ):
        self._interval = interval
        self._fail_threshold = fail_threshold
        self._success_threshold = success_threshold
        self._session_factory = session_factory or AsyncSessionLocal
        self._recorder = recorder
        # Per-camera probe-result streaks. Reset to 0 on a state transition.
        self._failure_streak: dict[str, int] = {}
        self._success_streak: dict[str, int] = {}
        self._task: asyncio.Task | None = None

    async def start(self):
        self._task = asyncio.create_task(self._loop())
        logger.info(f'CameraHealthChecker 已启动，间隔 {self._interval}s')

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info('CameraHealthChecker 已停止')

    async def _loop(self):
        while True:
            try:
                await self._check_all()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 — keep the polling loop alive on any probe/DB error
                logger.error(f'CameraHealthChecker 轮询异常: {e}')
            await asyncio.sleep(self._interval)

    async def _check_all(self):
        # Short-lived read session — released before spawning concurrent probe tasks
        async with self._session_factory() as db:
            result = await db.execute(select(Camera).where(Camera.rtsp_url.isnot(None)))
            cameras = result.scalars().all()
            snapshots = [
                (cam.device_mac, cam.rtsp_url, cam.onvif_user, cam.onvif_password, cam.is_online)
                for cam in cameras
                if cam.rtsp_url is not None
            ]
        await asyncio.gather(
            *[
                self._check_camera(device_mac, rtsp_url, onvif_user, onvif_password, was_online)
                for device_mac, rtsp_url, onvif_user, onvif_password, was_online in snapshots
            ],
            return_exceptions=True,
        )

    async def _check_camera(
        self,
        device_mac: str,
        rtsp_url: str,
        onvif_user: str | None,
        onvif_password: str | None,
        was_online: bool,
    ):
        probe_url = self._build_rtsp_url(rtsp_url, onvif_user, onvif_password)
        is_now_online = await self._probe_rtsp(probe_url)

        # Consecutive-N debounce: a single transient failure must not flip
        # is_online. Track per-camera streaks and only transition on a
        # threshold-met sample. The opposite streak is reset on each probe
        # so that a single success in the middle of a failure streak doesn't
        # re-arm the timer.
        if is_now_online:
            self._failure_streak[device_mac] = 0
            self._success_streak[device_mac] = self._success_streak.get(device_mac, 0) + 1
        else:
            self._success_streak[device_mac] = 0
            self._failure_streak[device_mac] = self._failure_streak.get(device_mac, 0) + 1

        if was_online:
            transition_to_offline = (
                not is_now_online and self._failure_streak[device_mac] >= self._fail_threshold
            )
        else:
            transition_to_offline = False
        if not was_online:
            transition_to_online = (
                is_now_online and self._success_streak[device_mac] >= self._success_threshold
            )
        else:
            transition_to_online = False

        # Always persist the freshest liveness read so last_probe_at stays
        # current, but only flip is_online when the streak actually crosses
        # the threshold. This keeps short probe blips from being persisted as
        # a real state change in the database.
        async with self._session_factory() as db:
            cam = (
                await db.execute(select(Camera).where(Camera.device_mac == device_mac))
            ).scalar_one_or_none()
            if cam is None:
                return
            # naive on purpose: `DateTime` SQLite column stores local wall time; see migrations
            cam.last_probe_at = datetime.now()  # noqa: DTZ005
            if transition_to_offline:
                cam.is_online = False
            elif transition_to_online:
                cam.is_online = True
            # Keep Device.is_online in sync with Camera.is_online
            dev = (
                await db.execute(select(Device).where(Device.mac == device_mac))
            ).scalar_one_or_none()
            if dev:
                dev.is_online = cam.is_online

            # C.7: when we cross into offline, stop any active recording so
            # the UI does not show "offline + 录制中" simultaneously. The
            # recorder's own on_failed callback will finalize the segment;
            # we still force is_recording=False here so the cameras list
            # reflects the new state immediately.
            if transition_to_offline and cam.is_recording:
                logger.warning(f'[CameraHealth] 摄像头掉线，联动停止录制: {device_mac}')
                if self._recorder is not None:
                    try:
                        await self._recorder.stop_recording(device_mac)
                    except Exception as e:  # noqa: BLE001 — recorder 边界
                        logger.error(f'[CameraHealth] 联动 stop_recording 失败 [{device_mac}]: {e}')
                cam.is_recording = False
            await db.commit()

        if transition_to_offline:
            self._failure_streak[device_mac] = 0
            self._success_streak[device_mac] = 0
            await ws_manager.broadcast('camera_offline', {'mac': device_mac})
            logger.warning(f'[CameraHealth] 摄像头掉线: {device_mac}')
        elif transition_to_online:
            self._failure_streak[device_mac] = 0
            self._success_streak[device_mac] = 0
            await ws_manager.broadcast('camera_online', {'mac': device_mac})
            logger.info(f'[CameraHealth] 摄像头恢复: {device_mac}')

    @staticmethod
    def _build_rtsp_url(rtsp_url: str, user: str | None, password: str | None) -> str:
        if not (user or password):
            return rtsp_url
        parsed = urlparse(rtsp_url)
        netloc = f'{user or ""}:{password or ""}@{parsed.hostname or ""}'
        if parsed.port:
            netloc += f':{parsed.port}'
        return urlunparse(parsed._replace(netloc=netloc))

    async def _probe_rtsp(self, rtsp_url: str) -> bool:
        # Use run_in_executor + subprocess.run to avoid asyncio.create_subprocess_exec,
        # which requires ProactorEventLoop on Windows (unavailable under uvicorn SelectorEventLoop).
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        [
                            'ffprobe',
                            '-v',
                            'quiet',
                            '-show_entries',
                            'format=duration',
                            '-i',
                            rtsp_url,
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    ),
                ),
                timeout=6,
            )
            return result.returncode == 0
        except Exception as e:  # noqa: BLE001 — ffprobe failure is expected (network/auth/timeout)
            logger.debug(f'[CameraHealth] _probe_rtsp 失败: {e}')
            return False

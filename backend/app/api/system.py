import asyncio
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import exists, func, not_, select

from app.config import get_settings
from app.deps import CurrentUser, DBDep
from app.domain.services.go2rtc_adapter import Go2RtcAdapter
from app.domain.services.go2rtc_runner import (
    Go2RtcRunner,
    read_webrtc_candidates,
    should_start_embedded_runner,
    write_go2rtc_config,
)
from app.models.camera import Camera
from app.models.device import Device
from app.models.member import Member, MemberDevice
from app.models.recording import Recording
from app.schemas.go2rtc_settings import Go2RtcSettingsUpdate, Go2RtcStatusOut

router = APIRouter()
_start_time = time.time()
_ffmpeg_available: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class HealthResponse(BaseModel):
    status: str
    checks: dict
    uptime_seconds: float
    version: str


def _check_ffmpeg() -> bool:
    global _ffmpeg_available
    if _ffmpeg_available is None:
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=3)
            _ffmpeg_available = result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            # ffmpeg 不在 PATH 上 (FileNotFoundError) 或执行失败, 健康检查降级
            logger.debug(f'ffmpeg 可用性检测失败: {e}')
            _ffmpeg_available = False
    return _ffmpeg_available


@router.get('/health', response_model=HealthResponse, tags=['system'])
async def health_check(request: Request):
    import asyncio

    from fastapi.responses import JSONResponse

    settings = get_settings()
    nas_syncer = request.app.state.nas_syncer
    loop = asyncio.get_running_loop()
    ffmpeg_ok, nas_ok = await asyncio.gather(
        loop.run_in_executor(None, _check_ffmpeg),
        loop.run_in_executor(None, nas_syncer.check_writable),
    )
    checks = {
        'database': True,
        'ffmpeg': ffmpeg_ok,
        'nas_writable': nas_ok,
    }
    all_ok = all(checks.values())
    response_data = HealthResponse(
        status='healthy' if all_ok else 'degraded',
        checks=checks,
        uptime_seconds=round(time.time() - _start_time, 1),
        version=settings.app_version,
    )
    status_code = 200 if all_ok else 503
    return JSONResponse(content=response_data.model_dump(), status_code=status_code)


def _go2rtc_state(request: Request) -> tuple[Go2RtcAdapter, Go2RtcRunner | None, Path | None]:
    adapter: Go2RtcAdapter | None = getattr(request.app.state, 'go2rtc_adapter', None)
    if adapter is None:
        raise HTTPException(status_code=503, detail='Go2rtcAdapter not initialized')
    runner: Go2RtcRunner | None = getattr(request.app.state, 'go2rtc_runner', None)
    binary: Path | None = getattr(request.app.state, 'go2rtc_binary', None)
    return adapter, runner, binary


async def _build_go2rtc_status(
    adapter: Go2RtcAdapter,
    runner: Go2RtcRunner | None,
    binary: Path | None,
) -> Go2RtcStatusOut:
    settings = get_settings()
    cfg_path = Path(settings.go2rtc_config_path)
    connected = await adapter.ping() if adapter.config.enabled else False
    has_binary = binary is not None and await asyncio.to_thread(binary.is_file)
    candidates = await asyncio.to_thread(read_webrtc_candidates, cfg_path)
    return Go2RtcStatusOut(
        enabled=adapter.config.enabled,
        connected=connected,
        embedded_runner=runner.is_running() if runner is not None else False,
        has_embedded_binary=has_binary,
        api_url=adapter.config.api_base,
        rtsp_url=adapter.config.rtsp_base,
        webrtc_candidates=candidates,
    )


@router.get('/go2rtc', response_model=Go2RtcStatusOut, tags=['system'])
async def get_go2rtc_status(request: Request, _: CurrentUser) -> Go2RtcStatusOut:
    adapter, runner, binary = _go2rtc_state(request)
    return await _build_go2rtc_status(adapter, runner, binary)


@router.put('/go2rtc', response_model=Go2RtcStatusOut, tags=['system'])
async def update_go2rtc_settings(
    body: Go2RtcSettingsUpdate,
    request: Request,
    _: CurrentUser,
) -> Go2RtcStatusOut:
    adapter, runner, binary = _go2rtc_state(request)
    settings = get_settings()
    cfg_path = Path(settings.go2rtc_config_path)

    if body.enabled is not None:
        adapter.config.enabled = body.enabled
        if not body.enabled and runner is not None and runner.is_running():
            runner.stop()
        elif should_start_embedded_runner(go2rtc_enabled=body.enabled, binary=binary):
            candidates = read_webrtc_candidates(cfg_path)
            write_go2rtc_config(cfg_path, webrtc_candidates=candidates or None)
            if runner is not None:
                # should_start_embedded_runner only returns True when binary is not None
                # — narrow the type for mypy.
                assert binary is not None
                runner.start(binary=binary, config_path=cfg_path)

    if body.webrtc_candidates is not None:
        write_go2rtc_config(cfg_path, webrtc_candidates=body.webrtc_candidates)
        if (
            adapter.config.enabled
            and runner is not None
            and runner.is_running()
            and binary is not None
        ):
            runner.stop()
            runner.start(binary=binary, config_path=cfg_path)

    return await _build_go2rtc_status(adapter, runner, binary)


@router.get('/dashboard', tags=['system'])
async def dashboard(db: DBDep, _: CurrentUser):
    today_start = datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)

    async def scalar(stmt):
        result = await db.execute(stmt)
        return result.scalar_one()

    (
        members_home,
        members_total,
        cameras_recording,
        cameras_online,
        cameras_total,
        devices_online,
        devices_total,
        recordings_today_count,
        recordings_today_duration,
        unknown_devices_today,
    ) = await asyncio.gather(
        scalar(select(func.count()).select_from(Member).where(Member.is_home)),
        scalar(select(func.count()).select_from(Member)),
        scalar(select(func.count()).select_from(Camera).where(Camera.is_recording)),
        scalar(select(func.count()).select_from(Camera).where(Camera.is_online)),
        scalar(select(func.count()).select_from(Camera)),
        scalar(select(func.count()).select_from(Device).where(Device.is_online)),
        scalar(select(func.count()).select_from(Device)),
        scalar(
            select(func.count()).select_from(Recording).where(Recording.started_at >= today_start)
        ),
        scalar(
            select(func.coalesce(func.sum(Recording.duration), 0))
            .where(Recording.started_at >= today_start)
            .where(Recording.status.in_(['completed', 'synced']))
        ),
        scalar(
            select(func.count())
            .select_from(Device)
            .where(Device.created_at >= today_start)
            .where(not_(exists(select(MemberDevice.mac).where(MemberDevice.mac == Device.mac))))
        ),
    )

    return {
        'members_home': members_home,
        'members_total': members_total,
        'cameras_recording': cameras_recording,
        'cameras_online': cameras_online,
        'cameras_total': cameras_total,
        'devices_online': devices_online,
        'devices_total': devices_total,
        'recordings_today_count': recordings_today_count,
        'recordings_today_duration_seconds': recordings_today_duration,
        'unknown_devices_today': unknown_devices_today,
    }

import asyncio
import subprocess
import threading
import uuid
from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, HTTPException, Query, Request, Response, WebSocket, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select

from app.auth import verify_token
from app.config import get_settings
from app.deps import CurrentUser, DBDep, Go2RtcDep, RecorderDep, StreamUser
from app.domain.models.camera import RecordingPreset
from app.domain.models.camera_event import (
    CameraEvent,
    EventSource,
    EventStatus,
    EventType,
)
from app.domain.services.go2rtc_adapter import Go2RtcAdapter, mac_to_stream_name
from app.domain.services.go2rtc_proxy import proxy_go2rtc_websocket
from app.domain.services.mqtt_service import MqttService
from app.domain.services.recorder import RecordingParams
from app.models.camera import Camera
from app.models.recording import Recording
from app.schemas.camera import (
    CameraCreate,
    CameraOut,
    CameraUpdate,
    LiveStreamOut,
    RecordingPresetCreate,
    RecordingPresetUpdate,
    StartRecordingRequest,
)
from app.services.onvif_client import OnvifClient
from app.services.ws_manager import ws_manager


def _get_mqtt(request: Request) -> MqttService | None:
    return getattr(request.app.state, 'mqtt_service', None)


router = APIRouter(prefix='/cameras', tags=['cameras'])


@router.get('', response_model=list[CameraOut])
async def list_cameras(db: DBDep, _: CurrentUser):
    result = await db.execute(select(Camera))
    return result.scalars().all()


@router.post('', response_model=CameraOut, status_code=status.HTTP_201_CREATED)
async def create_camera(body: CameraCreate, db: DBDep, _: CurrentUser, adapter: Go2RtcDep):
    camera = Camera(**body.model_dump())
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    await _sync_go2rtc_stream(adapter, camera)
    return camera


@router.get('/{mac}', response_model=CameraOut)
async def get_camera(mac: str, db: DBDep, _: CurrentUser):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    return camera


@router.put('/{mac}', response_model=CameraOut)
async def update_camera(
    mac: str, body: CameraUpdate, db: DBDep, _: CurrentUser, adapter: Go2RtcDep
):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(camera, field, value)
    await db.commit()
    await db.refresh(camera)
    if updates.keys() & {'rtsp_url', 'onvif_user', 'onvif_password'}:
        await _sync_go2rtc_stream(adapter, camera)
    return camera


@router.delete('/{mac}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(mac: str, db: DBDep, _: CurrentUser, adapter: Go2RtcDep):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    await _remove_go2rtc_stream(adapter, mac)
    await db.delete(camera)
    await db.commit()


@router.post('/{mac}/probe')
async def probe_camera(mac: str, db: DBDep, _: CurrentUser, http_request: Request):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    if not camera.onvif_host:
        raise HTTPException(
            status_code=422, detail='摄像头 onvif_host 未设置，请先通过 PUT 接口更新 IP 地址'
        )
    client = OnvifClient(
        camera.onvif_host, camera.onvif_port, camera.onvif_user or '', camera.onvif_password or ''
    )
    try:
        info = await asyncio.wait_for(client.get_device_info(), timeout=12)
        profiles = await asyncio.wait_for(client.get_profiles(), timeout=12)

        # 为每个 profile 获取 RTSP URI
        for p in profiles:
            try:
                p['rtsp_url'] = await asyncio.wait_for(
                    client.get_stream_uri(p['index']), timeout=12
                )
            except Exception as e:  # noqa: BLE001 — OnvifClient 第三方库, 单 profile 失败不应中断整个探测
                logger.warning(f'获取 profile {p.get("index")} RTSP URL 失败: {e}')
                p['rtsp_url'] = None

        # 自动将第一个有效 RTSP 地址写入摄像头配置
        auto_url = next((p['rtsp_url'] for p in profiles if p['rtsp_url']), None)
        if auto_url and not camera.rtsp_url:
            camera.rtsp_url = auto_url
            await db.commit()
            adapter: Go2RtcAdapter | None = getattr(http_request.app.state, 'go2rtc_adapter', None)
            if adapter is not None:
                await _sync_go2rtc_stream(adapter, camera)

        return {'device_info': info, 'profiles': profiles, 'auto_set_rtsp_url': auto_url}
    except TimeoutError:
        raise HTTPException(
            status_code=504, detail='ONVIF 连接超时，请确认摄像头 IP 和端口是否正确'
        )
    except Exception as e:  # noqa: BLE001 — OnvifClient 第三方库边界, 捕获所有非超时错误并转换为 500
        logger.error(f'ONVIF 探测异常 [{mac}]: {e}')
        err_str = str(e).lower()
        if 'timeout' in err_str or 'timed out' in err_str:
            raise HTTPException(
                status_code=504, detail='ONVIF 连接超时，请确认摄像头 IP 和端口是否正确'
            )
        raise HTTPException(status_code=500, detail=f'ONVIF 通信异常: {e}')


@router.post('/{mac}/record/start', status_code=status.HTTP_202_ACCEPTED)
async def start_recording(
    mac: str,
    db: DBDep,
    _: CurrentUser,
    recorder: RecorderDep,
    http_request: Request,
    request: StartRecordingRequest | None = None,
):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    if camera.is_recording:
        raise HTTPException(status_code=409, detail='该摄像头已在录制中')
    if not camera.rtsp_url:
        raise HTTPException(
            status_code=422, detail='摄像头 rtsp_url 未设置，请先通过 PUT 接口配置 RTSP 地址'
        )

    # Build RecordingParams from explicit preset, then camera default preset, then defaults.
    params = RecordingParams()
    preset = None
    if request and request.preset_id:
        presets = camera.get_presets()
        preset = next((p for p in presets if p.id == request.preset_id), None)
        if not preset:
            raise HTTPException(status_code=404, detail='预设不存在')
    elif camera.default_preset_id:
        preset = camera.get_default_preset()
        if camera.default_preset_id and not preset:
            raise HTTPException(status_code=404, detail='默认预设不存在，请重新设置')

    if preset:
        params = RecordingParams(
            resolution=preset.resolution,
            segment_seconds=preset.segment_duration,
            bitrate=preset.bitrate,
            fps=preset.fps,
        )
    if request and request.overrides:
        if 'resolution' in request.overrides:
            params.resolution = request.overrides['resolution']
        if 'segment_seconds' in request.overrides:
            params.segment_seconds = request.overrides['segment_seconds']
        if 'bitrate' in request.overrides:
            params.bitrate = request.overrides['bitrate']
        if 'fps' in request.overrides:
            params.fps = request.overrides['fps']

    rtsp_url = _rtsp_with_creds(camera)

    # Recording.started_at is a naive DateTime column; keep naive.
    # Also create a CameraEvent so this manual recording participates in the
    # unified timeline (P0-2). The Recording row gets linked to the event via
    # event_id; if recorder startup fails below, we roll back both rows.
    event = CameraEvent(
        camera_mac=mac,
        event_type=EventType.MANUAL_RECORDING,
        source=EventSource.USER,
        status=EventStatus.ACTIVE,
        started_at=datetime.now(),  # noqa: DTZ005
        summary='手动录制',
    )
    db.add(event)
    await db.flush()  # populate event.id

    rec = Recording(
        camera_mac=mac,
        file_path='(pending)',
        started_at=event.started_at,
        status='recording',
        event_id=event.id,
    )
    db.add(rec)
    camera.is_recording = True
    await db.commit()
    await db.refresh(rec)
    await db.refresh(event)

    try:
        await recorder.start_recording(mac, rtsp_url, params)
    except Exception as e:  # noqa: BLE001 — recorder 服务边界, 失败需回滚 DB 状态
        logger.error(f'启动录制失败 [{mac}]: {e}')
        camera.is_recording = False
        rec.status = 'failed'
        rec.error_msg = str(e)
        event.status = EventStatus.FAILED
        event.ended_at = datetime.now()  # noqa: DTZ005
        event.summary = f'启动失败: {e}'
        await db.commit()
        raise HTTPException(status_code=500, detail=f'启动录制失败: {e}')

    if mac in recorder.active:
        recorder.active[mac].recording_id = rec.id
        recorder.active[mac].session_recording_id = rec.id

    mqtt = _get_mqtt(http_request)
    if mqtt is not None:
        mqtt.publish_recording_started(mac, event_id=event.id)

    return {'message': '录制已启动', 'recording_id': rec.id}


@router.post('/{mac}/record/stop', status_code=status.HTTP_202_ACCEPTED)
async def stop_recording(mac: str, db: DBDep, _: CurrentUser, recorder: RecorderDep):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    if not camera.is_recording:
        raise HTTPException(status_code=409, detail='该摄像头未在录制')

    session = recorder.active.get(mac)
    session_id = (session.session_recording_id or session.recording_id) if session else None

    if session_id is None:
        orphan_result = await db.execute(
            select(Recording)
            .where(Recording.camera_mac == mac, Recording.status == 'recording')
            .order_by(Recording.started_at.desc())
            .limit(1)
        )
        orphan = orphan_result.scalar_one_or_none()
        if orphan:
            session_id = orphan.recording_id or orphan.id

    try:
        await recorder.stop_recording(mac)
    except Exception as e:  # noqa: BLE001 — recorder 服务边界, 停止失败不应中断后续清理
        logger.error(f'停止录制异常 [{mac}]: {e}')

    camera.is_recording = False
    ended_at = datetime.now()  # noqa: DTZ005

    # Close linked timeline event; segment rows are persisted by recorder callbacks.
    if session_id:
        parent_result = await db.execute(select(Recording).where(Recording.id == session_id))
        parent = parent_result.scalar_one_or_none()
        if parent and parent.event_id:
            ev_result = await db.execute(
                select(CameraEvent).where(CameraEvent.id == parent.event_id)
            )
            event = ev_result.scalar_one_or_none()
            if event and event.status == EventStatus.ACTIVE:
                event.status = EventStatus.COMPLETED
                event.ended_at = ended_at
                segments_result = await db.execute(
                    select(Recording).where(Recording.recording_id == session_id)
                )
                total_duration = sum(seg.duration or 0 for seg in segments_result.scalars().all())
                event.summary = f'手动录制，共 {total_duration}s'

    await db.commit()
    await ws_manager.broadcast(
        'recording_completed', {'camera_mac': mac, 'recording_id': session_id}
    )
    return {'message': '录制已停止'}


# ── MJPEG live stream ─────────────────────────────────────────


def _rtsp_with_creds(camera: Camera) -> str:
    """Embed ONVIF credentials into the RTSP URL if present."""
    url = camera.rtsp_url or ''
    if camera.onvif_user or camera.onvif_password:
        parsed = urlparse(url)
        netloc = f'{camera.onvif_user or ""}:{camera.onvif_password or ""}@{parsed.hostname or ""}'
        if parsed.port:
            netloc += f':{parsed.port}'
        url = urlunparse(parsed._replace(netloc=netloc))
    return url


async def _sync_go2rtc_stream(adapter: Go2RtcAdapter, camera: Camera) -> None:
    if not adapter.config.enabled or not camera.rtsp_url:
        return
    await adapter.ensure_stream(mac_to_stream_name(camera.device_mac), _rtsp_with_creds(camera))


async def _remove_go2rtc_stream(adapter: Go2RtcAdapter, mac: str) -> None:
    if not adapter.config.enabled:
        return
    await adapter.remove_stream(mac_to_stream_name(mac))


async def _mjpeg_generate(rtsp_url: str):
    """Async generator: reads RTSP via FFmpeg and yields multipart/x-mixed-replace frames.
    Uses subprocess.Popen + thread to avoid asyncio.create_subprocess_exec which requires
    ProactorEventLoop on Windows (not available under uvicorn reload/SelectorEventLoop).
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=5)
    proc_holder: list = [None]

    def _run_ffmpeg():
        proc = subprocess.Popen(
            [
                'ffmpeg',
                '-y',
                '-rtsp_transport',
                'tcp',
                '-i',
                rtsp_url,
                '-f',
                'mjpeg',
                '-q:v',
                '5',
                '-vf',
                'fps=10',
                'pipe:1',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        proc_holder[0] = proc
        if proc.stdout is None:
            raise RuntimeError('ffmpeg subprocess 未提供 stdout 管道')
        buf = b''
        SOI, EOI = b'\xff\xd8', b'\xff\xd9'
        try:
            while True:
                chunk = proc.stdout.read(32768)
                if not chunk:
                    break
                buf += chunk
                while True:
                    start = buf.find(SOI)
                    if start < 0:
                        buf = b''
                        break
                    end = buf.find(EOI, start + 2)
                    if end < 0:
                        buf = buf[start:]
                        break
                    frame = buf[start : end + 2]
                    buf = buf[end + 2 :]
                    future = asyncio.run_coroutine_threadsafe(queue.put(frame), loop)
                    try:
                        future.result(timeout=3)
                    except Exception as e:  # noqa: BLE001 — 跨线程 future, 客户端断开/超时统一静默退出
                        logger.debug(f'MJPEG 帧推送中断: {e}')
                        return  # client disconnected or timeout
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    t = threading.Thread(target=_run_ffmpeg, daemon=True)
    t.start()
    try:
        while True:
            frame = await queue.get()
            if frame is None:
                break
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        proc = proc_holder[0]
        if proc and proc.poll() is None:
            proc.kill()


@router.get('/{mac}/stream/mjpeg')
async def stream_mjpeg(mac: str, db: DBDep, _: StreamUser):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    if not camera.rtsp_url:
        raise HTTPException(
            status_code=422, detail='摄像头 rtsp_url 未设置，请先通过 ONVIF 探测配置 RTSP 地址'
        )
    return StreamingResponse(
        _mjpeg_generate(_rtsp_with_creds(camera)),
        media_type='multipart/x-mixed-replace; boundary=frame',
    )


# ── Snapshot ──────────────────────────────────────────────────


@router.get('/{mac}/snapshot')
async def snapshot_camera(mac: str, db: DBDep, _: CurrentUser):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    if not camera.rtsp_url:
        raise HTTPException(
            status_code=422, detail='摄像头 rtsp_url 未设置，请先通过 ONVIF 探测配置 RTSP 地址'
        )
    rtsp_url = _rtsp_with_creds(camera)
    loop = asyncio.get_running_loop()
    try:
        completed = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [
                        'ffmpeg',
                        '-y',
                        '-rtsp_transport',
                        'tcp',
                        '-i',
                        rtsp_url,
                        '-vframes',
                        '1',
                        '-f',
                        'image2',
                        'pipe:1',
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=14,
                ),
            ),
            timeout=15,
        )
    except (TimeoutError, subprocess.TimeoutExpired):
        raise HTTPException(status_code=408, detail='截图超时，摄像头可能无信号')
    if not completed.stdout:
        raise HTTPException(status_code=500, detail='截图失败，摄像头可能无信号或连接异常')
    return Response(content=completed.stdout, media_type='image/jpeg')


# ── go2rtc live stream ───────────────────────────────────────────


async def _get_camera_or_404(db: DBDep, mac: str) -> Camera:
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    return camera


@router.get('/{mac}/live', response_model=LiveStreamOut)
async def get_live_info(mac: str, db: DBDep, _: CurrentUser, adapter: Go2RtcDep) -> LiveStreamOut:
    mac = mac.upper()
    camera = await _get_camera_or_404(db, mac)
    if not camera.rtsp_url:
        raise HTTPException(
            status_code=422, detail='摄像头 rtsp_url 未设置，请先通过 ONVIF 探测配置 RTSP 地址'
        )
    stream_name = mac_to_stream_name(mac)
    if adapter.config.enabled:
        await adapter.ensure_stream(stream_name, _rtsp_with_creds(camera))
        if not await adapter.ping():
            info = adapter.build_live_info(mac)
            return LiveStreamOut(
                mode='mjpeg_fallback',
                stream_name=info.stream_name,
                status='unavailable',
                mjpeg_url=info.mjpeg_url,
            )
    info = adapter.build_live_info(mac)
    return LiveStreamOut(
        mode=info.mode,
        stream_name=info.stream_name,
        status=info.status,
        mse_ws_url=info.mse_ws_url,
        webrtc_url=info.webrtc_url,
        mjpeg_url=info.mjpeg_url,
    )


@router.websocket('/{mac}/live/ws')
async def live_ws_proxy(
    websocket: WebSocket,
    mac: str,
    token: Annotated[str | None, Query()] = None,
):
    settings = get_settings()
    raw = token
    if not raw:
        await websocket.close(code=4401)
        return
    if verify_token(raw, settings.jwt_secret_key) is None:
        await websocket.close(code=4401)
        return
    adapter: Go2RtcAdapter | None = getattr(websocket.app.state, 'go2rtc_adapter', None)
    if adapter is None or not adapter.config.enabled:
        await websocket.close(code=4503)
        return
    stream_name = mac_to_stream_name(mac.upper())
    await proxy_go2rtc_websocket(websocket, adapter.go2rtc_ws_url(stream_name))


@router.post('/{mac}/live/webrtc')
async def live_webrtc_proxy(
    mac: str,
    request: Request,
    db: DBDep,
    _: StreamUser,
    adapter: Go2RtcDep,
):
    mac = mac.upper()
    await _get_camera_or_404(db, mac)
    if not adapter.config.enabled:
        raise HTTPException(status_code=503, detail='go2rtc 未启用')
    stream_name = mac_to_stream_name(mac)
    body = await request.body()
    content_type = request.headers.get('content-type', 'application/json')
    resp = await adapter.post_webrtc(stream_name, body, content_type)
    media_type = resp.headers.get('content-type')
    return Response(content=resp.content, status_code=resp.status_code, media_type=media_type)


# ── HLS live stream (removed) ─────────────────────────────────

_HLS_LIVE_REMOVED = 'HLS 直播已移除，后续将改用 go2rtc 低延迟直播'


@router.post('/{mac}/live/start', deprecated=True)
async def start_live_removed(mac: str, _: CurrentUser):
    raise HTTPException(status_code=410, detail=_HLS_LIVE_REMOVED)


@router.delete('/{mac}/live/stop', deprecated=True)
async def stop_live_removed(mac: str, _: CurrentUser):
    raise HTTPException(status_code=410, detail=_HLS_LIVE_REMOVED)


# ── Recording Presets ───────────────────────────────────────────


@router.get('/{mac}/presets')
async def list_presets(mac: str, db: DBDep, _: CurrentUser):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    presets = camera.get_presets()
    default_id = camera.default_preset_id
    return [p.to_dict(is_default=p.id == default_id) for p in presets]


@router.post('/{mac}/presets', status_code=status.HTTP_201_CREATED)
async def create_preset(mac: str, body: RecordingPresetCreate, db: DBDep, _: CurrentUser):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')

    preset = RecordingPreset(
        id=str(uuid.uuid4()),
        name=body.name,
        resolution=body.resolution,
        segment_duration=body.segment_duration,
        bitrate=body.bitrate,
        fps=body.fps,
    )
    camera.add_preset(preset)
    await db.commit()
    return preset.to_dict()


@router.put('/{mac}/presets/{preset_id}', status_code=status.HTTP_200_OK)
async def update_preset(
    mac: str, preset_id: str, body: RecordingPresetUpdate, db: DBDep, _: CurrentUser
):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')

    presets = camera.get_presets()
    if not any(p.id == preset_id for p in presets):
        raise HTTPException(status_code=404, detail='预设不存在')

    camera.update_preset(preset_id, body.model_dump(exclude_unset=True))
    await db.commit()
    updated = next(p for p in camera.get_presets() if p.id == preset_id)
    return updated.to_dict()


@router.delete('/{mac}/presets/{preset_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(mac: str, preset_id: str, db: DBDep, _: CurrentUser):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')

    presets = camera.get_presets()
    if not any(p.id == preset_id for p in presets):
        raise HTTPException(status_code=404, detail='预设不存在')

    camera.remove_preset(preset_id)
    await db.commit()


@router.post('/{mac}/presets/default', status_code=status.HTTP_200_OK)
async def set_default_preset(mac: str, body: dict, db: DBDep, _: CurrentUser):
    mac = mac.upper()
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail='摄像头未配置')
    preset_id = body.get('preset_id')
    if preset_id:
        presets = camera.get_presets()
        if not any(p.id == preset_id for p in presets):
            raise HTTPException(status_code=404, detail='预设不存在')
    camera.default_preset_id = preset_id
    await db.commit()
    return {'default_preset_id': camera.default_preset_id}

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from loguru import logger
from sqlalchemy import select

from app.deps import CurrentUser, DBDep
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleCreate, ScheduleOut, ScheduleUpdate
from app.services.scheduler_service import scheduler_service

router = APIRouter(prefix='/schedules', tags=['schedules'])


def _make_recording_callback(request: Request, schedule: Schedule):
    from app.domain.services.recorder import RecordingParams

    recorder = request.app.state.recorder

    async def _trigger(camera_mac: str):
        from urllib.parse import urlparse, urlunparse

        from sqlalchemy import select as _select

        from app.database import AsyncSessionLocal
        from app.models.camera import Camera as CameraModel
        from app.models.recording import Recording as RecordingModel

        rec_id = None
        async with AsyncSessionLocal() as db:
            cam = (
                await db.execute(_select(CameraModel).where(CameraModel.device_mac == camera_mac))
            ).scalar_one_or_none()
            if not cam or not cam.rtsp_url:
                logger.warning(f'调度录制: 摄像头 {camera_mac} 不存在或无 RTSP URL')
                return
            if cam.is_recording:
                logger.info(f'调度录制: 摄像头 {camera_mac} 已在录制中，跳过')
                return
            rtsp_url = cam.rtsp_url
            if cam.onvif_user or cam.onvif_password:
                parsed = urlparse(rtsp_url)
                netloc = (
                    f'{cam.onvif_user or ""}:{cam.onvif_password or ""}@{parsed.hostname or ""}'
                )
                if parsed.port:
                    netloc += f':{parsed.port}'
                rtsp_url = urlunparse(parsed._replace(netloc=netloc))
            # RecordingModel.started_at is a naive DateTime column; keep naive.
            rec = RecordingModel(
                camera_mac=camera_mac,
                file_path='(pending)',
                started_at=datetime.now(),  # noqa: DTZ005
                status='recording',
            )
            db.add(rec)
            cam.is_recording = True
            await db.commit()
            await db.refresh(rec)
            rec_id = rec.id

        # Resolve segment_seconds: overrides > preset > schedule field
        segment_seconds = schedule.segment_duration
        if schedule.preset_id:
            preset = next((p for p in cam.get_presets() if p.id == schedule.preset_id), None)
            if preset:
                segment_seconds = preset.segment_duration
            else:
                logger.warning(
                    f'调度录制: preset_id="{schedule.preset_id}" 未找到，'
                    f'回退到 schedule.segment_duration={schedule.segment_duration}'
                )
        # overrides always take precedence (even over preset)
        overrides = schedule.get_overrides()
        if overrides and 'segment_duration' in overrides:
            segment_seconds = overrides['segment_duration']

        try:
            await recorder.start_recording(
                camera_mac=camera_mac,
                rtsp_url=rtsp_url,
                params=RecordingParams(segment_seconds=segment_seconds),
            )
        except Exception as e:  # noqa: BLE001 — recorder 服务边界, 调度触发失败需回滚 DB
            logger.error(f'调度录制启动失败 {camera_mac}: {e}')
            async with AsyncSessionLocal() as db:
                rec_db = (
                    await db.execute(_select(RecordingModel).where(RecordingModel.id == rec_id))
                ).scalar_one_or_none()
                if rec_db:
                    rec_db.status = 'failed'
                    rec_db.error_msg = str(e)
                cam_db = (
                    await db.execute(
                        _select(CameraModel).where(CameraModel.device_mac == camera_mac)
                    )
                ).scalar_one_or_none()
                if cam_db:
                    cam_db.is_recording = False
                await db.commit()
            return
        if camera_mac in recorder.active:
            recorder.active[camera_mac].recording_id = rec_id
            recorder.active[camera_mac].session_recording_id = rec_id

    return _trigger


@router.get('', response_model=list[ScheduleOut])
async def list_schedules(db: DBDep, _: CurrentUser):
    result = await db.execute(select(Schedule))
    return result.scalars().all()


@router.post('', response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(body: ScheduleCreate, request: Request, db: DBDep, _: CurrentUser):
    parts = body.cron_expr.split()
    if len(parts) != 5:
        raise HTTPException(status_code=400, detail='cron 表达式必须是 5 字段格式')
    data = body.model_dump(exclude={'preset_id', 'overrides'})
    schedule = Schedule(**data)
    if body.preset_id is not None:
        schedule.preset_id = body.preset_id
    if body.overrides is not None:
        schedule.set_overrides(body.overrides)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    if schedule.enabled:
        callback = _make_recording_callback(request, schedule)
        try:
            scheduler_service.add_recording_job(
                job_id=f'schedule_{schedule.id}',
                cron_expr=schedule.cron_expr,
                camera_mac=schedule.camera_mac,
                callback=callback,
            )
            logger.info(f'已注册调度任务: schedule_{schedule.id} ({schedule.cron_expr})')
        except Exception as e:  # noqa: BLE001 — APScheduler 第三方库边界, 注册失败不阻断 schedule 入库
            logger.error(f'APScheduler 注册失败 schedule_{schedule.id}: {e}')
    return schedule


@router.get('/{schedule_id}', response_model=ScheduleOut)
async def get_schedule(schedule_id: int, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail='计划不存在')
    return schedule


@router.patch('/{schedule_id}', response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int, body: ScheduleUpdate, request: Request, db: DBDep, _: CurrentUser
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail='计划不存在')
    if body.cron_expr is not None and len(body.cron_expr.split()) != 5:
        raise HTTPException(status_code=400, detail='cron 表达式必须是 5 字段格式')
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == 'overrides':
            schedule.set_overrides(value)
        elif field == 'preset_id':
            schedule.preset_id = value
        else:
            setattr(schedule, field, value)
    await db.commit()
    await db.refresh(schedule)

    job_id = f'schedule_{schedule.id}'
    if schedule.enabled:
        callback = _make_recording_callback(request, schedule)
        try:
            scheduler_service.add_recording_job(
                job_id=job_id,
                cron_expr=schedule.cron_expr,
                camera_mac=schedule.camera_mac,
                callback=callback,
            )
            logger.info(f'已更新调度任务: {job_id} ({schedule.cron_expr})')
        except Exception as e:  # noqa: BLE001 — APScheduler 第三方库边界, 更新失败不阻断 schedule 入库
            logger.error(f'APScheduler 注册失败 {job_id}: {e}')
    else:
        scheduler_service.remove_job(job_id)
        logger.info(f'已禁用调度任务: {job_id}')
    return schedule


@router.delete('/{schedule_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: int, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail='计划不存在')
    scheduler_service.remove_job(f'schedule_{schedule_id}')
    await db.delete(schedule)
    await db.commit()

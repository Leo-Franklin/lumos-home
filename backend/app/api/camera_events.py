"""Camera-events API — list, get, patch, delete the unified event model
that the timeline UI, retention policy, and Frigate bridge all read from.
"""

import math
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from sqlalchemy import func, select

from app.deps import CurrentUser, DBDep
from app.domain.models.camera_event import (
    CameraEvent,
    EventSeverity,
    EventStatus,
)
from app.schemas import PagedResponse
from app.schemas.camera_event import CameraEventOut, CameraEventPatch

router = APIRouter(prefix='/camera-events', tags=['camera-events'])


def _to_dto(event: CameraEvent) -> CameraEventOut:
    return CameraEventOut.model_validate(event)


_VALID_STATUSES = {
    EventStatus.ACTIVE,
    EventStatus.COMPLETED,
    EventStatus.FAILED,
    EventStatus.LOCKED,
}
_VALID_SEVERITIES = {
    EventSeverity.INFO,
    EventSeverity.NOTICE,
    EventSeverity.WARNING,
    EventSeverity.ALERT,
}


@router.get('', response_model=PagedResponse[CameraEventOut])
async def list_events(
    db: DBDep,
    _: CurrentUser,
    camera_mac: str | None = None,
    event_type: str | None = None,
    source: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = select(CameraEvent)
    count_q = select(func.count()).select_from(CameraEvent)
    if camera_mac:
        q = q.where(CameraEvent.camera_mac == camera_mac.upper())
        count_q = count_q.where(CameraEvent.camera_mac == camera_mac.upper())
    if event_type:
        q = q.where(CameraEvent.event_type == event_type)
        count_q = count_q.where(CameraEvent.event_type == event_type)
    if source:
        q = q.where(CameraEvent.source == source)
        count_q = count_q.where(CameraEvent.source == source)
    if status:
        q = q.where(CameraEvent.status == status)
        count_q = count_q.where(CameraEvent.status == status)

    total = (await db.execute(count_q)).scalar_one()
    q = q.order_by(CameraEvent.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return PagedResponse(
        items=[_to_dto(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get('/{event_id}', response_model=CameraEventOut)
async def get_event(event_id: int, db: DBDep, _: CurrentUser):
    result = await db.execute(select(CameraEvent).where(CameraEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail='事件不存在')
    return _to_dto(event)


@router.patch('/{event_id}', response_model=CameraEventOut)
async def patch_event(event_id: int, body: CameraEventPatch, db: DBDep, _: CurrentUser):
    result = await db.execute(select(CameraEvent).where(CameraEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail='事件不存在')

    patch_data: dict[str, Any] = body.model_dump(exclude_unset=True)
    if 'status' in patch_data and patch_data['status'] is not None:
        if patch_data['status'] not in _VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f'status 必须是 {_VALID_STATUSES} 之一',
            )
    if 'severity' in patch_data and patch_data['severity'] is not None:
        if patch_data['severity'] not in _VALID_SEVERITIES:
            raise HTTPException(
                status_code=422,
                detail=f'severity 必须是 {_VALID_SEVERITIES} 之一',
            )

    for field_name, value in patch_data.items():
        setattr(event, field_name, value)
    await db.commit()
    await db.refresh(event)
    return _to_dto(event)


@router.delete('/{event_id}', status_code=204)
async def delete_event(event_id: int, db: DBDep, _: CurrentUser):
    result = await db.execute(select(CameraEvent).where(CameraEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail='事件不存在')
    # Note: linked Recording rows keep their `event_id` (orphan link). Future
    # retention sweeper may detect and clean them. For now, the API simply
    # removes the event row — the plan says "删除事件" not "删除录像".
    await db.delete(event)
    await db.commit()
    logger.info(f'已删除事件 id={event_id} camera={event.camera_mac}')
    return None

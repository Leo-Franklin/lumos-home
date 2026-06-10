import math
from datetime import datetime, timedelta
from typing import NoReturn

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBDep
from app.models.device import Device
from app.models.member import Member, MemberDevice, PresenceLog
from app.schemas import PagedResponse
from app.schemas.device import DeviceOut
from app.schemas.member import (
    DailyStats,
    MemberCreate,
    MemberDeviceCreate,
    MemberDeviceOut,
    MemberOut,
    MemberStatsOut,
    MemberUpdate,
    PresenceLogOut,
)

router = APIRouter(prefix='/members', tags=['members'])


def _not_found() -> NoReturn:
    raise HTTPException(status_code=404, detail='成员不存在')


async def _device_summary_by_member(
    db: AsyncSession, member_ids: list[int]
) -> dict[int, tuple[int, int]]:
    if not member_ids:
        return {}
    bound_result = await db.execute(
        select(MemberDevice.member_id, MemberDevice.mac).where(
            MemberDevice.member_id.in_(member_ids)
        )
    )
    macs_by_member: dict[int, list[str]] = {}
    all_macs: set[str] = set()
    for member_id, mac in bound_result.all():
        macs_by_member.setdefault(member_id, []).append(mac)
        all_macs.add(mac)

    online_macs: set[str] = set()
    if all_macs:
        online_result = await db.execute(
            select(Device.mac).where(Device.mac.in_(all_macs), Device.is_online.is_(True))
        )
        online_macs = set(online_result.scalars().all())

    return {
        mid: (len(macs), sum(1 for mac in macs if mac in online_macs))
        for mid, macs in macs_by_member.items()
    }


def _to_member_out(member: Member, summary: dict[int, tuple[int, int]]) -> MemberOut:
    device_count, devices_online = summary.get(member.id, (0, 0))
    return MemberOut(
        id=member.id,
        name=member.name,
        avatar_url=member.avatar_url,
        webhook_url=member.webhook_url,
        is_home=member.is_home,
        last_arrived_at=member.last_arrived_at,
        last_left_at=member.last_left_at,
        auto_record_cameras=member.auto_record_cameras or [],
        created_at=member.created_at,
        device_count=device_count,
        devices_online=devices_online,
    )


async def _member_out(db: AsyncSession, member: Member) -> MemberOut:
    summary = await _device_summary_by_member(db, [member.id])
    return _to_member_out(member, summary)


async def _members_out(db: AsyncSession, members: list[Member]) -> list[MemberOut]:
    if not members:
        return []
    summary = await _device_summary_by_member(db, [m.id for m in members])
    return [_to_member_out(m, summary) for m in members]


@router.get('', response_model=list[MemberOut])
async def list_members(db: DBDep, _: CurrentUser):
    result = await db.execute(select(Member).order_by(Member.id))
    return await _members_out(db, list(result.scalars().all()))


@router.post('', response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def create_member(body: MemberCreate, db: DBDep, _: CurrentUser):
    member = Member(**body.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return await _member_out(db, member)


@router.get('/{member_id}', response_model=MemberOut)
async def get_member(member_id: int, db: DBDep, _: CurrentUser):
    member = (await db.execute(select(Member).where(Member.id == member_id))).scalar_one_or_none()
    if not member:
        _not_found()
    return await _member_out(db, member)


@router.patch('/{member_id}', response_model=MemberOut)
async def update_member(member_id: int, body: MemberUpdate, db: DBDep, _: CurrentUser):
    member = (await db.execute(select(Member).where(Member.id == member_id))).scalar_one_or_none()
    if not member:
        _not_found()
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    await db.commit()
    await db.refresh(member)
    return await _member_out(db, member)


@router.delete('/{member_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(member_id: int, db: DBDep, _: CurrentUser):
    member = (await db.execute(select(Member).where(Member.id == member_id))).scalar_one_or_none()
    if not member:
        _not_found()
    await db.delete(member)
    await db.commit()


@router.get('/{member_id}/devices', response_model=list[MemberDeviceOut])
async def list_member_devices(member_id: int, db: DBDep, _: CurrentUser):
    member = (await db.execute(select(Member).where(Member.id == member_id))).scalar_one_or_none()
    if not member:
        _not_found()
    result = await db.execute(select(MemberDevice).where(MemberDevice.member_id == member_id))
    bound = result.scalars().all()

    macs = [d.mac for d in bound]
    device_map: dict[str, Device] = {}
    if macs:
        dev_result = await db.execute(select(Device).where(Device.mac.in_(macs)))
        for dev in dev_result.scalars().all():
            device_map[dev.mac] = dev

    return [
        MemberDeviceOut(
            id=d.id,
            member_id=d.member_id,
            mac=d.mac,
            label=d.label,
            device_info=DeviceOut.model_validate(device_map[d.mac])
            if d.mac in device_map
            else None,
        )
        for d in bound
    ]


@router.post(
    '/{member_id}/devices', response_model=MemberDeviceOut, status_code=status.HTTP_201_CREATED
)
async def bind_device(member_id: int, body: MemberDeviceCreate, db: DBDep, _: CurrentUser):
    member = (await db.execute(select(Member).where(Member.id == member_id))).scalar_one_or_none()
    if not member:
        _not_found()

    existing = (
        await db.execute(
            select(MemberDevice).where(
                MemberDevice.member_id == member_id, MemberDevice.mac == body.mac
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail='该设备已绑定到此成员')

    other_member = (
        await db.execute(
            select(MemberDevice).where(
                MemberDevice.mac == body.mac, MemberDevice.member_id != member_id
            )
        )
    ).scalar_one_or_none()
    if other_member:
        raise HTTPException(status_code=409, detail='该设备已绑定到其他成员')

    md = MemberDevice(member_id=member_id, mac=body.mac, label=body.label)
    db.add(md)
    await db.commit()
    await db.refresh(md)

    device = (await db.execute(select(Device).where(Device.mac == body.mac))).scalar_one_or_none()
    return MemberDeviceOut(
        id=md.id,
        member_id=md.member_id,
        mac=md.mac,
        label=md.label,
        device_info=DeviceOut.model_validate(device) if device else None,
    )


@router.delete('/{member_id}/devices/{mac}', status_code=status.HTTP_204_NO_CONTENT)
async def unbind_device(member_id: int, mac: str, db: DBDep, _: CurrentUser):
    md = (
        await db.execute(
            select(MemberDevice).where(MemberDevice.member_id == member_id, MemberDevice.mac == mac)
        )
    ).scalar_one_or_none()
    if not md:
        raise HTTPException(status_code=404, detail='绑定关系不存在')
    await db.delete(md)
    await db.commit()


@router.get('/{member_id}/logs', response_model=PagedResponse[PresenceLogOut])
async def list_presence_logs(
    member_id: int,
    db: DBDep,
    _: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    member = (await db.execute(select(Member).where(Member.id == member_id))).scalar_one_or_none()
    if not member:
        _not_found()

    q = (
        select(PresenceLog)
        .where(PresenceLog.member_id == member_id)
        .order_by(PresenceLog.occurred_at.desc())
    )
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return PagedResponse(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get('/{member_id}/stats', response_model=MemberStatsOut)
async def get_member_stats(
    member_id: int,
    db: DBDep,
    _: CurrentUser,
    range_: str = Query('7d', alias='range', pattern='^(7d|30d)$'),
):
    member = (await db.execute(select(Member).where(Member.id == member_id))).scalar_one_or_none()
    if not member:
        _not_found()

    days = 30 if range_ == '30d' else 7
    # PresenceLog.occurred_at is a naive DateTime column; keep naive.
    now = datetime.now()  # noqa: DTZ005
    start_dt = now - timedelta(days=days)

    # Determine if member was already home at start_dt
    last_before = (
        await db.execute(
            select(PresenceLog)
            .where(PresenceLog.member_id == member_id, PresenceLog.occurred_at < start_dt)
            .order_by(PresenceLog.occurred_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    home_since: datetime | None = (
        start_dt if (last_before and last_before.event == 'arrived') else None
    )

    # All logs within range, oldest first
    in_range = (
        (
            await db.execute(
                select(PresenceLog)
                .where(PresenceLog.member_id == member_id, PresenceLog.occurred_at >= start_dt)
                .order_by(PresenceLog.occurred_at.asc())
            )
        )
        .scalars()
        .all()
    )

    # Build home intervals
    intervals: list[tuple[datetime, datetime]] = []
    for log in in_range:
        if log.event == 'arrived' and home_since is None:
            home_since = log.occurred_at
        elif log.event == 'left' and home_since is not None:
            intervals.append((home_since, log.occurred_at))
            home_since = None
    if home_since is not None:
        intervals.append((home_since, now))

    # Sum per-day overlap minutes
    daily: list[DailyStats] = []
    total_minutes = 0
    for i in range(days):
        day_start = datetime.combine((start_dt + timedelta(days=i)).date(), datetime.min.time())
        day_end = day_start + timedelta(days=1)
        mins = sum(
            int((min(iv_end, day_end) - max(iv_start, day_start)).total_seconds() / 60)
            for iv_start, iv_end in intervals
            if min(iv_end, day_end) > max(iv_start, day_start)
        )
        daily.append(DailyStats(date=day_start.date().isoformat(), minutes=mins))
        total_minutes += mins

    return MemberStatsOut(total_minutes=total_minutes, daily=daily)

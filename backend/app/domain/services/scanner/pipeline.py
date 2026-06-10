"""Device scan orchestration: discovery pipeline, persistence, analytics."""

from __future__ import annotations

import asyncio
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.domain.models.camera import Camera
from app.domain.models.device import Device
from app.domain.models.device_online_log import DeviceOnlineLog
from app.domain.models.member import MemberDevice
from app.domain.services.ws_manager import ws_manager

from .enrichment import build_upnp_cache, enrich_device
from .metadata import persist_scan_fields
from .network import detect_default_gateway_ips
from .probe import Scanner


def find_unknown_devices(
    enriched: list[dict],
    original_last_seen: dict[str, datetime | None],
    bound_macs: set[str],
    now: datetime,
    staleness_hours: int = 24,
) -> list[dict]:
    """Return devices not bound to any member that are new or stale (not seen recently)."""
    result = []
    for data in enriched:
        mac = data['mac']
        if mac in bound_macs:
            continue
        is_new = mac not in original_last_seen
        last_seen = original_last_seen.get(mac)
        is_stale = (
            not is_new
            and last_seen is not None
            and (now - last_seen).total_seconds() > staleness_hours * 3600
        )
        if is_new or is_stale:
            result.append(data)
    return result


async def log_scan_result(
    db: AsyncSession,
    enriched: list[dict],
    bucket_hour: datetime,
) -> None:
    """Upsert per-device presence into DeviceOnlineLog for the given hour bucket."""
    online_macs = {d['mac'] for d in enriched}
    all_result = await db.execute(select(Device.mac, Device.device_type))
    all_devices = all_result.all()
    if not all_devices:
        return

    rows = [
        {
            'mac': d.mac,
            'bucket_hour': bucket_hour,
            'device_type': d.device_type or 'unknown',
            'online_count': 1 if d.mac in online_macs else 0,
            'scan_count': 1,
        }
        for d in all_devices
    ]
    stmt = sqlite_insert(DeviceOnlineLog).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=['mac', 'bucket_hour'],
        set_={
            'online_count': DeviceOnlineLog.online_count + stmt.excluded.online_count,
            'scan_count': DeviceOnlineLog.scan_count + stmt.excluded.scan_count,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def run_device_scan(network_range: str) -> None:
    """Run device scan: arp scan → enrich → upsert → mark offline → analytics."""
    loop = asyncio.get_running_loop()
    scanner = await loop.run_in_executor(None, Scanner, network_range)
    await ws_manager.broadcast('scan_started', {'subnet': ', '.join(scanner.networks)})
    try:
        devices = await scanner.arp_scan()
        upnp_cache = await build_upnp_cache()
        gateway_ips = await loop.run_in_executor(None, detect_default_gateway_ips)
        results = {'found': len(devices), 'new': 0, 'offline': 0}

        sem = asyncio.Semaphore(64)

        async def enrich_with_sem(d: dict) -> dict:
            async with sem:
                return await enrich_device(scanner, d, upnp_cache, gateway_ips)

        enriched = await asyncio.gather(*[enrich_with_sem(d) for d in devices])

        async with AsyncSessionLocal() as db:
            macs = [d['mac'] for d in enriched]
            camera_macs_result = await db.execute(select(Camera.device_mac))
            camera_macs: set[str] = {row[0] for row in camera_macs_result.all()}
            existing_rows = (
                (await db.execute(select(Device).where(Device.mac.in_(macs)))).scalars().all()
            )
            existing_map = {d.mac: d for d in existing_rows}
            original_last_seen: dict[str, datetime | None] = {
                mac: dev.last_seen for mac, dev in existing_map.items()
            }

            now = datetime.now()  # noqa: DTZ005 - Device.last_seen is DateTime (naive)
            for data in enriched:
                mac = data['mac']
                if mac in camera_macs:
                    existing = existing_map.get(mac)
                    if existing:
                        existing.is_online = True
                        existing.last_seen = now
                        existing.ip = data['ip']
                    continue
                existing = existing_map.get(mac)
                if existing:
                    persist_scan_fields(existing, data)
                    existing.is_online = True
                    existing.last_seen = now
                    if mac not in camera_macs:
                        new_type = data['device_type']
                        if existing.device_type in ('unknown', None) or new_type != 'unknown':
                            existing.device_type = new_type
                else:
                    results['new'] += 1
                    device_type = data['device_type']
                    new_device = Device(
                        mac=mac,
                        device_type=device_type,
                        is_online=True,
                        last_seen=now,
                    )
                    persist_scan_fields(new_device, data)
                    db.add(new_device)
            await db.commit()

            if macs:
                offline_result = await db.execute(
                    select(Device).where(Device.is_online, Device.mac.notin_(macs))
                )
                offline_devices = offline_result.scalars().all()
                for dev in offline_devices:
                    dev.is_online = False
                results['offline'] += len(offline_devices)
                await db.commit()

            try:
                bound_result = await db.execute(select(MemberDevice.mac))
                bound_macs = {row[0] for row in bound_result.all()}
                unknowns = find_unknown_devices(enriched, original_last_seen, bound_macs, now)
                for u in unknowns:
                    await ws_manager.broadcast(
                        'unknown_device_detected',
                        {
                            'mac': u['mac'],
                            'ip': u['ip'],
                            'vendor': u.get('vendor'),
                            'hostname': u.get('hostname'),
                            'device_type': u.get('device_type'),
                            'open_ports': u.get('open_ports'),
                            'first_seen': now.isoformat(),
                        },
                    )
            except Exception as e:  # noqa: BLE001 - mixes SQLAlchemy + websockets, both can throw
                logger.debug(f'写入未知设备广播失败: {e}')

            try:
                bucket_hour = now.replace(minute=0, second=0, microsecond=0)
                await log_scan_result(db, enriched, bucket_hour)
            except Exception as e:  # noqa: BLE001 - mixes SQLAlchemy + sqlite upsert paths
                logger.debug(f'写入扫描结果日志失败: {e}')

        await ws_manager.broadcast('scan_completed', results)
    except Exception as e:  # noqa: BLE001 - top-level catch-all for entire scan flow
        await ws_manager.broadcast('scan_completed', {'error': str(e)})


# Backward-compatible private aliases.
_find_unknown_devices = find_unknown_devices
_log_scan_result = log_scan_result
_run_scan = run_device_scan

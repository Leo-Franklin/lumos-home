"""Cleanup phantom camera Device records and sync online status."""

import pytest
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.domain.models.camera import Camera
from app.domain.models.device import Device


@pytest.mark.asyncio
async def test_cleanup_phantom_cameras():
    """Delete Device records with device_type='camera' but no corresponding Camera record."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Device).where(
                Device.device_type == 'camera',
                ~Device.mac.in_(select(Camera.device_mac)),
            )
        )
        phantoms = result.scalars().all()

        print(f'\nFound {len(phantoms)} phantom camera Device record(s):')
        for d in phantoms:
            print(f'  - {d.mac}  ip={d.ip}  hostname={d.hostname}  vendor={d.vendor}')

        for p in phantoms:
            await db.delete(p)
        await db.commit()
        print(f'Deleted {len(phantoms)} phantom camera Device record(s).')


@pytest.mark.asyncio
async def test_sync_device_online_status():
    """Ensure Device.is_online matches Camera.is_online for all camera Device records."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Device).join(Camera, Device.mac == Camera.device_mac))
        devices = result.scalars().all()
        count = 0
        for dev in devices:
            cam = (
                await db.execute(select(Camera).where(Camera.device_mac == dev.mac))
            ).scalar_one()
            if dev.is_online != cam.is_online:
                print(f'  Syncing {dev.mac}: Device.is_online={dev.is_online} -> {cam.is_online}')
                dev.is_online = cam.is_online
                count += 1
        if count:
            await db.commit()
            print(f'Synced {count} Device.is_online value(s).')
        else:
            print('All Device.is_online already in sync with Camera.is_online.')

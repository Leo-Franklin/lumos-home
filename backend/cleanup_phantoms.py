"""Standalone cleanup script for phantom camera/device/schedule records.

Run this script to clean up fake/phantom camera records that may have
been created by tests leaking into the production database.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import String, Boolean, DateTime, Float, Text, func, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_data_dir = Path('./data')
_database_url = f'sqlite+aiosqlite:///{_data_dir / "smart_home.db"}'


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = 'devices'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mac: Mapped[str] = mapped_column(String(17), unique=True, nullable=False, index=True)
    ip: Mapped[str | None] = mapped_column(String(45))
    hostname: Mapped[str | None] = mapped_column(String(256))
    vendor: Mapped[str | None] = mapped_column(String(128))
    device_type: Mapped[str] = mapped_column(String(32), default='unknown')
    alias: Mapped[str | None] = mapped_column(String(128))
    open_ports: Mapped[str | None] = mapped_column(Text)
    response_time_ms: Mapped[float | None] = mapped_column(Float)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)


class Camera(Base):
    __tablename__ = 'cameras'
    device_mac: Mapped[str] = mapped_column(String(17), primary_key=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    onvif_host: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class Schedule(Base):
    __tablename__ = 'schedules'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_mac: Mapped[str] = mapped_column(String(17), nullable=False)


async def main():
    engine = create_async_engine(_database_url, echo=False, connect_args={'check_same_thread': False})
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        # ── Phase 1: Phantom Camera records ──────────────────────────
        # Camera records whose MAC has no matching Device record (orphan/fake cameras)
        camera_macs_result = await db.execute(select(Camera.device_mac))
        all_camera_macs = {row[0] for row in camera_macs_result.all()}

        device_macs_result = await db.execute(select(Device.mac))
        all_device_macs = {row[0] for row in device_macs_result.all()}

        phantom_camera_macs = all_camera_macs - all_device_macs

        print(f"\n=== Phase 1: Phantom Camera Cleanup ===")
        print(f"Total Camera records: {len(all_camera_macs)}")
        print(f"Total Device records: {len(all_device_macs)}")
        print(f"Phantom Camera records (no matching Device): {len(phantom_camera_macs)}")
        for mac in sorted(phantom_camera_macs):
            cam = (await db.execute(
                select(Camera).where(Camera.device_mac == mac)
            )).scalar_one()
            print(f"  - {mac}  onvif_host={cam.onvif_host}  created_at={cam.created_at}")

        if phantom_camera_macs:
            answer = input("\nDelete these phantom Camera records? [y/N]: ")
            if answer.lower() == 'y':
                for mac in phantom_camera_macs:
                    cam = (await db.execute(
                        select(Camera).where(Camera.device_mac == mac)
                    )).scalar_one()
                    await db.delete(cam)
                await db.commit()
                print(f"Deleted {len(phantom_camera_macs)} phantom Camera record(s).")

        # ── Phase 2: Orphan Schedule records ─────────────────────────
        schedule_result = await db.execute(select(Schedule))
        schedules = schedule_result.scalars().all()

        orphan_schedules = [s for s in schedules if s.camera_mac not in all_device_macs]

        print(f"\n=== Phase 2: Orphan Schedule Cleanup ===")
        print(f"Total Schedule records: {len(schedules)}")
        print(f"Orphan Schedules (camera_mac has no Device): {len(orphan_schedules)}")
        for s in orphan_schedules:
            print(f"  - schedule_{s.id}  camera_mac={s.camera_mac}")

        if orphan_schedules:
            answer = input("\nDelete these orphan Schedule records? [y/N]: ")
            if answer.lower() == 'y':
                for s in orphan_schedules:
                    await db.delete(s)
                await db.commit()
                print(f"Deleted {len(orphan_schedules)} orphan Schedule record(s).")

        # ── Phase 3: Phantom Device records ──────────────────────────
        # Device records with device_type='camera' but no matching Camera record
        result = await db.execute(
            select(Device).where(
                Device.device_type == 'camera',
                ~Device.mac.in_(select(Camera.device_mac)),
            )
        )
        phantom_devices = result.scalars().all()

        print(f"\n=== Phase 3: Phantom Camera-Device Cleanup ===")
        print(f"Phantom Device records (type='camera', no Camera record): {len(phantom_devices)}")
        for d in phantom_devices:
            print(f"  - {d.mac}  ip={d.ip}  hostname={d.hostname}  vendor={d.vendor}")

        if phantom_devices:
            answer = input("\nDelete these phantom Device records? [y/N]: ")
            if answer.lower() == 'y':
                for d in phantom_devices:
                    await db.delete(d)
                await db.commit()
                print(f"Deleted {len(phantom_devices)} phantom Device record(s).")

        # ── Phase 4: Sync Device.is_online with Camera.is_online ─────
        print(f"\n=== Phase 4: Online Status Sync ===")
        result = await db.execute(
            select(Device).join(Camera, Device.mac == Camera.device_mac)
        )
        devices = result.scalars().all()
        count = 0
        for dev in devices:
            cam = (await db.execute(
                select(Camera).where(Camera.device_mac == dev.mac)
            )).scalar_one()
            if dev.is_online != cam.is_online:
                print(f"  Syncing {dev.mac}: Device.is_online={dev.is_online} -> {cam.is_online}")
                dev.is_online = cam.is_online
                count += 1
        if count:
            await db.commit()
            print(f"Synced {count} Device.is_online value(s).")
        else:
            print("All Device.is_online already in sync with Camera.is_online.")

    await engine.dispose()
    print("\nDone.")


if __name__ == '__main__':
    asyncio.run(main())

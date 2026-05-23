"""Standalone cleanup script for phantom camera Device records."""
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


async def main():
    engine = create_async_engine(_database_url, echo=False, connect_args={'check_same_thread': False})
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        # Phase 1: Delete Device records with device_type='camera' but no corresponding Camera record
        result = await db.execute(
            select(Device).where(
                Device.device_type == 'camera',
                ~Device.mac.in_(select(Camera.device_mac)),
            )
        )
        phantoms = result.scalars().all()

        print(f"\n=== Phase 1: Phantom Camera Cleanup ===")
        print(f"Found {len(phantoms)} phantom camera Device record(s):")
        for d in phantoms:
            print(f"  - {d.mac}  ip={d.ip}  hostname={d.hostname}  vendor={d.vendor}")

        for p in phantoms:
            await db.delete(p)
        await db.commit()
        print(f"Deleted {len(phantoms)} phantom camera Device record(s).")

        # Phase 2: Sync Device.is_online with Camera.is_online
        print(f"\n=== Phase 2: Online Status Sync ===")
        result2 = await db.execute(
            select(Device).join(Camera, Device.mac == Camera.device_mac)
        )
        devices = result2.scalars().all()
        count = 0
        for dev in devices:
            cam = (await db.execute(select(Camera).where(Camera.device_mac == dev.mac))).scalar_one()
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
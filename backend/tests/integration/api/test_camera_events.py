"""Integration tests for the /api/v1/camera-events endpoints.

TDD: describe the API contract that the timeline UI, Frigate bridge, and
retention policies will rely on. The plan's P0-2 milestone depends on this
surface.
"""

from datetime import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture
async def mem_db():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    from app.database import Base
    from app.domain.models import (  # noqa: F401
        camera,
        camera_event,
        device,
        device_online_log,
        dlna_device,
        member,
        recording,
        schedule,
        user_settings,
    )
    from app.models import user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    yield Session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(mem_db):
    from app.database import get_db
    from app.deps import get_current_user
    from app.main import app as fastapi_app

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as c:
        yield c

    fastapi_app.dependency_overrides.clear()


async def _seed_camera(mem_db, mac: str = 'AA:BB:CC:DD:EE:01'):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=mac, device_type='camera', is_online=True))
        await db.commit()
        db.add(Camera(device_mac=mac, onvif_host='192.168.1.10', rtsp_url='rtsp://x'))
        await db.commit()


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_events_returns_paged_response(client, mem_db):
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )

    await _seed_camera(mem_db)
    async with mem_db() as db:
        for i in range(3):
            db.add(
                CameraEvent(
                    camera_mac='AA:BB:CC:DD:EE:01',
                    event_type=EventType.MANUAL_RECORDING,
                    source=EventSource.USER,
                    status=EventStatus.COMPLETED,
                    started_at=datetime(2026, 6, 1, 10, 0, i),
                )
            )
        await db.commit()

    r = await client.get('/api/v1/camera-events')
    assert r.status_code == 200
    body = r.json()
    assert body['total'] == 3
    assert len(body['items']) == 3


@pytest.mark.asyncio
async def test_list_events_filters_by_camera_mac(client, mem_db):
    from app.domain.models.camera import Camera
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )
    from app.models.device import Device

    async with mem_db() as db:
        for mac in ('AA:BB:CC:DD:EE:01', 'AA:BB:CC:DD:EE:02'):
            db.add(Device(mac=mac, device_type='camera', is_online=True))
            await db.commit()
            db.add(Camera(device_mac=mac, onvif_host='192.168.1.10', rtsp_url='rtsp://x'))
            await db.commit()
        db.add(
            CameraEvent(
                camera_mac='AA:BB:CC:DD:EE:01',
                event_type=EventType.MANUAL_RECORDING,
                source=EventSource.USER,
                status=EventStatus.COMPLETED,
                started_at=datetime(2026, 6, 1, 10, 0, 0),
            )
        )
        db.add(
            CameraEvent(
                camera_mac='AA:BB:CC:DD:EE:02',
                event_type=EventType.MOTION,
                source=EventSource.FRIGATE,
                status=EventStatus.ACTIVE,
                started_at=datetime(2026, 6, 1, 11, 0, 0),
            )
        )
        await db.commit()

    r = await client.get('/api/v1/camera-events', params={'camera_mac': 'AA:BB:CC:DD:EE:01'})
    body = r.json()
    assert body['total'] == 1
    assert body['items'][0]['camera_mac'] == 'AA:BB:CC:DD:EE:01'


@pytest.mark.asyncio
async def test_list_events_filters_by_event_type_and_status(client, mem_db):
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )

    await _seed_camera(mem_db)
    async with mem_db() as db:
        db.add(
            CameraEvent(
                camera_mac='AA:BB:CC:DD:EE:01',
                event_type=EventType.MOTION,
                source=EventSource.FRIGATE,
                status=EventStatus.ACTIVE,
                started_at=datetime(2026, 6, 1, 10, 0, 0),
            )
        )
        db.add(
            CameraEvent(
                camera_mac='AA:BB:CC:DD:EE:01',
                event_type=EventType.MANUAL_RECORDING,
                source=EventSource.USER,
                status=EventStatus.COMPLETED,
                started_at=datetime(2026, 6, 1, 10, 0, 1),
            )
        )
        await db.commit()

    r = await client.get(
        '/api/v1/camera-events', params={'event_type': 'motion', 'status': 'active'}
    )
    body = r.json()
    assert body['total'] == 1
    assert body['items'][0]['event_type'] == 'motion'


# ---------------------------------------------------------------------------
# Get / Patch / Delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_event_returns_full_record(client, mem_db):
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )

    await _seed_camera(mem_db)
    async with mem_db() as db:
        ev = CameraEvent(
            camera_mac='AA:BB:CC:DD:EE:01',
            event_type=EventType.MANUAL_RECORDING,
            source=EventSource.USER,
            status=EventStatus.COMPLETED,
            started_at=datetime(2026, 6, 1, 10, 0, 0),
            summary='Front door',
            metadata_json={'label': 'person', 'score': 0.91},
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        ev_id = ev.id

    r = await client.get(f'/api/v1/camera-events/{ev_id}')
    assert r.status_code == 200
    body = r.json()
    assert body['id'] == ev_id
    assert body['summary'] == 'Front door'
    assert body['metadata_json']['label'] == 'person'


@pytest.mark.asyncio
async def test_patch_event_can_lock_and_set_summary(client, mem_db):
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )

    await _seed_camera(mem_db)
    async with mem_db() as db:
        ev = CameraEvent(
            camera_mac='AA:BB:CC:DD:EE:01',
            event_type=EventType.MANUAL_RECORDING,
            source=EventSource.USER,
            status=EventStatus.COMPLETED,
            started_at=datetime(2026, 6, 1, 10, 0, 0),
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        ev_id = ev.id

    r = await client.patch(
        f'/api/v1/camera-events/{ev_id}',
        json={'status': 'locked', 'summary': 'Important — keep'},
    )
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'locked'
    assert body['summary'] == 'Important — keep'


@pytest.mark.asyncio
async def test_patch_event_rejects_invalid_status(client, mem_db):
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )

    await _seed_camera(mem_db)
    async with mem_db() as db:
        ev = CameraEvent(
            camera_mac='AA:BB:CC:DD:EE:01',
            event_type=EventType.MANUAL_RECORDING,
            source=EventSource.USER,
            status=EventStatus.COMPLETED,
            started_at=datetime(2026, 6, 1, 10, 0, 0),
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        ev_id = ev.id

    r = await client.patch(f'/api/v1/camera-events/{ev_id}', json={'status': 'bogus'})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_event_removes_it(client, mem_db):
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )

    await _seed_camera(mem_db)
    async with mem_db() as db:
        ev = CameraEvent(
            camera_mac='AA:BB:CC:DD:EE:01',
            event_type=EventType.MANUAL_RECORDING,
            source=EventSource.USER,
            status=EventStatus.COMPLETED,
            started_at=datetime(2026, 6, 1, 10, 0, 0),
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        ev_id = ev.id

    r = await client.delete(f'/api/v1/camera-events/{ev_id}')
    assert r.status_code == 204

    r2 = await client.get(f'/api/v1/camera-events/{ev_id}')
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_event_returns_404(client):
    r = await client.get('/api/v1/camera-events/9999')
    assert r.status_code == 404

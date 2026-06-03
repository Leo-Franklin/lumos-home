"""Integration test: starting a manual recording creates a CameraEvent
and links the Recording row to it via event_id.

This is the P0-2 acceptance criterion: "手动录制...能生成统一事件".
We use a fake Recorder that doesn't actually spawn ffmpeg, so the test
runs on any machine without RTSP or ffmpeg installed.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
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
async def client(mem_db, monkeypatch):
    from app.database import get_db
    from app.deps import get_current_user
    from app.main import app as fastapi_app

    # Replace the recorder with a no-op fake. The routers read it from
    # app.state, set by the lifespan; lifespan doesn't run under ASGITransport.
    fake_recorder = MagicMock()
    fake_recorder.start_recording = AsyncMock(return_value=None)
    fake_recorder.active = {}  # start_recording inserts here in real code
    fastapi_app.state.recorder = fake_recorder
    fastapi_app.state.nas_syncer = MagicMock()

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as c:
        yield c, fake_recorder

    fastapi_app.dependency_overrides.clear()


async def _seed_camera(mem_db, mac: str = 'AA:BB:CC:DD:EE:01'):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=mac, device_type='camera', is_online=True))
        await db.commit()
        db.add(Camera(device_mac=mac, onvif_host='192.168.1.10', rtsp_url='rtsp://x/y'))
        await db.commit()


@pytest.mark.asyncio
async def test_start_recording_creates_manual_recording_event(client, mem_db):
    await _seed_camera(mem_db)
    c, recorder = client

    response = await c.post('/api/v1/cameras/AA:BB:CC:DD:EE:01/record/start')
    assert response.status_code == 202, response.text
    body = response.json()
    assert 'recording_id' in body
    rec_id = body['recording_id']

    # Verify a CameraEvent was created with the right type/source
    from app.domain.models.camera_event import (
        CameraEvent,
        EventSource,
        EventStatus,
        EventType,
    )
    from app.domain.models.recording import Recording

    async with mem_db() as db:
        # Recording row links to the event
        rec = (await db.execute(select(Recording).where(Recording.id == rec_id))).scalar_one()
        assert rec.event_id is not None
        ev = (
            await db.execute(select(CameraEvent).where(CameraEvent.id == rec.event_id))
        ).scalar_one()
        assert ev.camera_mac == 'AA:BB:CC:DD:EE:01'
        assert ev.event_type == EventType.MANUAL_RECORDING
        assert ev.source == EventSource.USER
        assert ev.status == EventStatus.ACTIVE
        assert ev.started_at is not None


@pytest.mark.asyncio
async def test_recording_event_is_visible_via_api(client, mem_db):
    await _seed_camera(mem_db)
    c, _ = client

    await c.post('/api/v1/cameras/AA:BB:CC:DD:EE:01/record/start')

    r = await c.get('/api/v1/camera-events', params={'event_type': 'manual_recording'})
    assert r.status_code == 200
    body = r.json()
    assert body['total'] == 1
    assert body['items'][0]['source'] == 'user'
    assert body['items'][0]['status'] == 'active'


@pytest.mark.asyncio
async def test_start_recording_marks_event_failed_when_recorder_fails(client, mem_db):
    await _seed_camera(mem_db)
    c, recorder = client
    recorder.start_recording.side_effect = RuntimeError('ffmpeg not found')

    response = await c.post('/api/v1/cameras/AA:BB:CC:DD:EE:01/record/start')
    assert response.status_code == 500

    # Event is preserved as a failed audit record — never silently deleted
    from app.domain.models.camera_event import CameraEvent, EventStatus

    async with mem_db() as db:
        events = (await db.execute(select(CameraEvent))).scalars().all()
        assert len(events) == 1
        assert events[0].status == EventStatus.FAILED
        assert events[0].ended_at is not None
        assert 'ffmpeg not found' in (events[0].summary or '')

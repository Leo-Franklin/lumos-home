"""End-to-end test: FrigateBridgeService.handle_message writes CameraEvent
rows that the /camera-events API can then read.

The bridge is the consumer side of the MQTT pipeline; this test proves
that what Frigate publishes lands in our event store without needing
a real broker.
"""

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
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
async def seeded_db(mem_db):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac='AA:BB:CC:DD:EE:01', device_type='camera', is_online=True))
        await db.commit()
        db.add(
            Camera(
                device_mac='AA:BB:CC:DD:EE:01',
                onvif_host='192.168.1.10',
                rtsp_url='rtsp://x',
                frigate_name='front_door',
            )
        )
        await db.commit()
    return mem_db


@pytest.mark.asyncio
async def test_person_message_creates_external_frigate_event(seeded_db):
    from app.domain.services.frigate_bridge import (
        FrigateBridgeConfig,
        FrigateBridgeService,
    )

    client = MagicMock()
    cfg = FrigateBridgeConfig(enabled=True, topic_prefix='frigate')
    svc = FrigateBridgeService(
        mqtt_client=client,
        session_factory=seeded_db,
        config=cfg,
    )

    payload = {
        'type': 'new',
        'after': {
            'id': '1700000000.abc',
            'camera': 'front_door',
            'label': 'person',
            'start_time': 1700000000.0,
            'score': 0.91,
            'top_score': 0.91,
        },
    }
    event = await svc.handle_message('frigate/front_door/person', payload)
    assert event is not None
    assert event.camera_mac == 'AA:BB:CC:DD:EE:01'  # resolved from frigate_name
    assert event.event_type == 'external_frigate'
    assert event.source == 'frigate'
    assert event.metadata_json['label'] == 'person'
    assert event.metadata_json['frigate_event_id'] == '1700000000.abc'


@pytest.mark.asyncio
async def test_end_message_marks_event_completed(seeded_db):
    from app.domain.services.frigate_bridge import (
        FrigateBridgeConfig,
        FrigateBridgeService,
    )

    client = MagicMock()
    cfg = FrigateBridgeConfig(enabled=True, topic_prefix='frigate')
    svc = FrigateBridgeService(mqtt_client=client, session_factory=seeded_db, config=cfg)

    new_payload = {
        'type': 'new',
        'after': {
            'id': '1700000100.xyz',
            'camera': 'front_door',
            'label': 'car',
            'start_time': 1700000100.0,
        },
    }
    end_payload = {
        'type': 'end',
        'after': {
            'id': '1700000100.xyz',
            'camera': 'front_door',
            'label': 'car',
            'start_time': 1700000100.0,
            'end_time': 1700000160.0,
        },
    }

    first = await svc.handle_message('frigate/front_door/car', new_payload)
    assert first.status == 'active'
    assert first.ended_at is None

    second = await svc.handle_message('frigate/front_door/car', end_payload)
    assert second.status == 'completed'
    assert second.ended_at is not None


@pytest.mark.asyncio
async def test_unknown_camera_name_falls_back_to_uppercased_name(seeded_db):
    from app.domain.services.frigate_bridge import (
        FrigateBridgeConfig,
        FrigateBridgeService,
    )

    client = MagicMock()
    cfg = FrigateBridgeConfig(enabled=True, topic_prefix='frigate')
    svc = FrigateBridgeService(mqtt_client=client, session_factory=seeded_db, config=cfg)

    payload = {
        'type': 'new',
        'after': {
            'id': '1700000200.q',
            'camera': 'unconfigured_gate',
            'label': 'motion',
            'start_time': 1700000200.0,
        },
    }
    event = await svc.handle_message('frigate/unconfigured_gate/motion', payload)
    # Bridge stores the unknown name uppercased — operators can correct later
    assert event.camera_mac == 'UNCONFIGURED_GATE'


@pytest.mark.asyncio
async def test_events_are_visible_via_camera_events_api(seeded_db):
    """End-to-end: bridge writes a row, API reads it back."""
    from app.database import get_db
    from app.deps import get_current_user
    from app.domain.services.frigate_bridge import (
        FrigateBridgeConfig,
        FrigateBridgeService,
    )
    from app.main import app as fastapi_app

    # Wire bridge + DB override (lifespan not running under ASGITransport)
    bridge = FrigateBridgeService(
        mqtt_client=MagicMock(),
        session_factory=seeded_db,
        config=FrigateBridgeConfig(enabled=True),
    )
    fastapi_app.state.frigate_bridge = bridge

    async def override_get_db():
        async with seeded_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    from httpx import ASGITransport, AsyncClient

    payload = {
        'type': 'new',
        'after': {
            'id': '1700000999.api',
            'camera': 'front_door',
            'label': 'package',
            'start_time': 1700000999.0,
        },
    }
    await bridge.handle_message('frigate/front_door/package', payload)

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as ac:
        r = await ac.get('/api/v1/camera-events', params={'event_type': 'external_frigate'})
        assert r.status_code == 200
        body = r.json()
        assert body['total'] == 1
        assert body['items'][0]['source'] == 'frigate'
        assert body['items'][0]['metadata_json']['label'] == 'package'

    fastapi_app.dependency_overrides.clear()

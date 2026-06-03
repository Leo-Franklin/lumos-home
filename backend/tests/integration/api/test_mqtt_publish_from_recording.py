"""Integration test: starting a manual recording fires an MQTT publish
on the configured MqttService.

The router reads MqttService from app.state (set by the lifespan). We
inject a service with a MagicMock client so we can assert the publish
that the recording flow triggers.
"""

from unittest.mock import AsyncMock, MagicMock

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
    from app.domain.services.mqtt_service import MqttConfig, MqttService
    from app.main import app as fastapi_app

    fake_recorder = MagicMock()
    fake_recorder.start_recording = AsyncMock(return_value=None)
    fake_recorder.active = {}
    fastapi_app.state.recorder = fake_recorder
    fastapi_app.state.nas_syncer = MagicMock()

    fake_mqtt_client = MagicMock()
    mqtt_svc = MqttService(client=fake_mqtt_client, config=MqttConfig(topic_prefix='lumos'))
    fastapi_app.state.mqtt_service = mqtt_svc

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as c:
        yield c, fake_mqtt_client

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
async def test_start_recording_publishes_to_mqtt(client, mem_db):
    await _seed_camera(mem_db)
    c, mqtt_client = client

    response = await c.post('/api/v1/cameras/AA:BB:CC:DD:EE:01/record/start')
    assert response.status_code == 202

    # The recording flow must have published a 'recording/started' event
    topics = [call_args[0][0] for call_args in mqtt_client.publish.call_args_list]
    assert 'lumos/recording/started' in topics


@pytest.mark.asyncio
async def test_mqtt_disabled_means_no_publish(client, mem_db):
    from app.database import get_db
    from app.deps import get_current_user
    from app.domain.services.mqtt_service import MqttConfig, MqttService
    from app.main import app as fastapi_app

    await _seed_camera(mem_db)
    fake_recorder = MagicMock()
    fake_recorder.start_recording = AsyncMock(return_value=None)
    fake_recorder.active = {}
    fastapi_app.state.recorder = fake_recorder
    fastapi_app.state.nas_syncer = MagicMock()

    mqtt_client = MagicMock()
    mqtt_svc = MqttService(client=mqtt_client, config=MqttConfig(topic_prefix='lumos'))
    mqtt_svc.disable()
    fastapi_app.state.mqtt_service = mqtt_svc

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://t') as ac:
        response = await ac.post('/api/v1/cameras/AA:BB:CC:DD:EE:01/record/start')
        assert response.status_code == 202

    fastapi_app.dependency_overrides.clear()

    # Disabled service must not have called publish at all
    mqtt_client.publish.assert_not_called()

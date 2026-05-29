"""Integration tests for app/api/members.py endpoints.

Covers:
  GET    /api/v1/members
  POST   /api/v1/members
  GET    /api/v1/members/{id}
  PATCH  /api/v1/members/{id}
  DELETE /api/v1/members/{id}
  GET    /api/v1/members/{id}/devices
  POST   /api/v1/members/{id}/devices
  DELETE /api/v1/members/{id}/devices/{mac}
  GET    /api/v1/members/{id}/logs
  GET    /api/v1/members/{id}/stats
"""

import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

_JWT_KEY = 'test_secret_key_that_is_at_least_32_characters_long'
_ADMIN_PW = 'testpassword_for_ci_only'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mem_db():
    """In-memory SQLite with all tables created, StaticPool so all sessions share one connection."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    # Import all models so Base.metadata is fully populated
    from app.database import Base
    from app.domain.models import (  # noqa: F401
        camera,
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
    """AsyncClient wired to mem_db with auth override and get_db override."""
    monkeypatch.setenv('JWT_SECRET_KEY', _JWT_KEY)
    monkeypatch.setenv('ADMIN_PASSWORD', _ADMIN_PW)

    from app.config import get_settings

    get_settings.cache_clear()

    from app.database import get_db
    from app.deps import get_current_user
    from app.main import app as fastapi_app

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://test') as c:
        yield c

    fastapi_app.dependency_overrides.clear()
    get_settings.cache_clear()


def _unique_name(prefix: str = 'member') -> str:
    return f'{prefix}-{uuid.uuid4().hex[:8]}'


# ---------------------------------------------------------------------------
# Helpers to seed data directly into mem_db
# ---------------------------------------------------------------------------


async def _create_member(mem_db, name=None, **kwargs):
    from app.domain.models.member import Member

    name = name or _unique_name()
    async with mem_db() as db:
        m = Member(name=name, **kwargs)
        db.add(m)
        await db.commit()
        await db.refresh(m)
        return m.id, m.name


async def _bind_device(mem_db, member_id: int, mac: str, label: str | None = None):
    from app.domain.models.member import MemberDevice

    async with mem_db() as db:
        md = MemberDevice(member_id=member_id, mac=mac, label=label)
        db.add(md)
        await db.commit()
        await db.refresh(md)
        return md.id


async def _add_log(mem_db, member_id: int, event: str, occurred_at: datetime):
    from app.domain.models.member import PresenceLog

    async with mem_db() as db:
        log = PresenceLog(member_id=member_id, event=event, occurred_at=occurred_at)
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log.id


# ---------------------------------------------------------------------------
# GET /api/v1/members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_members_empty(client):
    resp = await client.get('/api/v1/members')
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_members_returns_created(client, mem_db):
    mid, name = await _create_member(mem_db)
    resp = await client.get('/api/v1/members')
    assert resp.status_code == 200
    ids = [m['id'] for m in resp.json()]
    assert mid in ids


# ---------------------------------------------------------------------------
# POST /api/v1/members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_member_minimal(client):
    name = _unique_name()
    resp = await client.post('/api/v1/members', json={'name': name})
    assert resp.status_code == 201
    data = resp.json()
    assert data['name'] == name
    assert 'id' in data
    assert data['is_home'] is False


@pytest.mark.asyncio
async def test_create_member_full(client):
    name = _unique_name()
    payload = {
        'name': name,
        'avatar_url': 'https://example.com/avatar.png',
        'webhook_url': 'https://hooks.example.com/notify',
        'auto_record_cameras': ['AA:BB:CC:DD:EE:01'],
    }
    resp = await client.post('/api/v1/members', json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data['name'] == name
    assert data['avatar_url'] == payload['avatar_url']
    assert data['webhook_url'] == payload['webhook_url']
    assert data['auto_record_cameras'] == ['AA:BB:CC:DD:EE:01']


# ---------------------------------------------------------------------------
# GET /api/v1/members/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_member_found(client, mem_db):
    mid, name = await _create_member(mem_db)
    resp = await client.get(f'/api/v1/members/{mid}')
    assert resp.status_code == 200
    assert resp.json()['id'] == mid
    assert resp.json()['name'] == name


@pytest.mark.asyncio
async def test_get_member_not_found(client):
    resp = await client.get('/api/v1/members/99999')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/members/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_member_name(client, mem_db):
    mid, _name = await _create_member(mem_db)
    new_name = _unique_name('updated')
    resp = await client.patch(f'/api/v1/members/{mid}', json={'name': new_name})
    assert resp.status_code == 200
    assert resp.json()['name'] == new_name


@pytest.mark.asyncio
async def test_update_member_partial(client, mem_db):
    mid, original_name = await _create_member(mem_db)
    resp = await client.patch(
        f'/api/v1/members/{mid}',
        json={'avatar_url': 'https://example.com/new.png'},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['name'] == original_name
    assert data['avatar_url'] == 'https://example.com/new.png'


@pytest.mark.asyncio
async def test_update_member_not_found(client):
    resp = await client.patch('/api/v1/members/99999', json={'name': 'ghost'})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/members/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_member(client, mem_db):
    mid, _name = await _create_member(mem_db)
    resp = await client.delete(f'/api/v1/members/{mid}')
    assert resp.status_code == 204

    # Confirm it's gone
    resp2 = await client.get(f'/api/v1/members/{mid}')
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_member_not_found(client):
    resp = await client.delete('/api/v1/members/99999')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/members/{id}/devices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_member_devices_empty(client, mem_db):
    mid, _ = await _create_member(mem_db)
    resp = await client.get(f'/api/v1/members/{mid}/devices')
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_member_devices_returns_bound(client, mem_db):
    mid, _ = await _create_member(mem_db)
    mac = 'AA:BB:CC:DD:EE:FF'
    await _bind_device(mem_db, mid, mac, label='Phone')
    resp = await client.get(f'/api/v1/members/{mid}/devices')
    assert resp.status_code == 200
    devices = resp.json()
    assert len(devices) == 1
    assert devices[0]['mac'] == mac
    assert devices[0]['label'] == 'Phone'
    assert devices[0]['member_id'] == mid


@pytest.mark.asyncio
async def test_list_member_devices_404_on_missing_member(client):
    resp = await client.get('/api/v1/members/99999/devices')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/members/{id}/devices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bind_device_success(client, mem_db):
    mid, _ = await _create_member(mem_db)
    mac = 'BB:BB:CC:DD:EE:01'
    resp = await client.post(
        f'/api/v1/members/{mid}/devices',
        json={'mac': mac, 'label': 'Laptop'},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data['mac'] == mac
    assert data['label'] == 'Laptop'
    assert data['member_id'] == mid
    assert data['device_info'] is None  # no Device row in DB


@pytest.mark.asyncio
async def test_bind_device_duplicate_returns_409(client, mem_db):
    mid, _ = await _create_member(mem_db)
    mac = 'CC:CC:CC:DD:EE:01'
    await _bind_device(mem_db, mid, mac)

    resp = await client.post(f'/api/v1/members/{mid}/devices', json={'mac': mac})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_bind_device_member_not_found(client):
    resp = await client.post('/api/v1/members/99999/devices', json={'mac': 'DD:DD:DD:DD:DD:DD'})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/members/{id}/devices/{mac}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unbind_device_success(client, mem_db):
    mid, _ = await _create_member(mem_db)
    mac = 'EE:EE:EE:EE:EE:01'
    await _bind_device(mem_db, mid, mac)

    resp = await client.delete(f'/api/v1/members/{mid}/devices/{mac}')
    assert resp.status_code == 204

    # Confirm it's no longer listed
    resp2 = await client.get(f'/api/v1/members/{mid}/devices')
    assert resp2.status_code == 200
    assert not any(d['mac'] == mac for d in resp2.json())


@pytest.mark.asyncio
async def test_unbind_device_not_found(client, mem_db):
    mid, _ = await _create_member(mem_db)
    resp = await client.delete(f'/api/v1/members/{mid}/devices/FF:FF:FF:FF:FF:FF')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/members/{id}/logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_presence_logs_empty(client, mem_db):
    mid, _ = await _create_member(mem_db)
    resp = await client.get(f'/api/v1/members/{mid}/logs')
    assert resp.status_code == 200
    body = resp.json()
    assert body['total'] == 0
    assert body['items'] == []


@pytest.mark.asyncio
async def test_list_presence_logs_returns_items(client, mem_db):
    mid, _ = await _create_member(mem_db)
    now = datetime.now()
    await _add_log(mem_db, mid, 'arrived', now - timedelta(hours=2))
    await _add_log(mem_db, mid, 'left', now - timedelta(hours=1))

    resp = await client.get(f'/api/v1/members/{mid}/logs')
    assert resp.status_code == 200
    body = resp.json()
    assert body['total'] == 2
    assert len(body['items']) == 2
    events = {item['event'] for item in body['items']}
    assert events == {'arrived', 'left'}


@pytest.mark.asyncio
async def test_list_presence_logs_pagination(client, mem_db):
    mid, _ = await _create_member(mem_db)
    now = datetime.now()
    for i in range(5):
        await _add_log(mem_db, mid, 'arrived', now - timedelta(hours=i + 1))

    resp = await client.get(f'/api/v1/members/{mid}/logs?page=1&page_size=3')
    assert resp.status_code == 200
    body = resp.json()
    assert body['total'] == 5
    assert len(body['items']) == 3
    assert body['pages'] == 2


@pytest.mark.asyncio
async def test_list_presence_logs_404_on_missing_member(client):
    resp = await client.get('/api/v1/members/99999/logs')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/members/{id}/stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_member_stats_no_logs(client, mem_db):
    mid, _ = await _create_member(mem_db)
    resp = await client.get(f'/api/v1/members/{mid}/stats?range=7d')
    assert resp.status_code == 200
    body = resp.json()
    assert body['total_minutes'] == 0
    assert len(body['daily']) == 7


@pytest.mark.asyncio
async def test_get_member_stats_30d(client, mem_db):
    mid, _ = await _create_member(mem_db)
    resp = await client.get(f'/api/v1/members/{mid}/stats?range=30d')
    assert resp.status_code == 200
    body = resp.json()
    assert len(body['daily']) == 30


@pytest.mark.asyncio
async def test_get_member_stats_with_home_time(client, mem_db):
    """Member arrived and left within the 7-day window — total_minutes should be nonzero.

    Use logs 2 days ago to ensure they fall cleanly inside the 7-day daily buckets
    (the stats loop covers start_dt..start_dt+7days, where start_dt = now-7days).
    """
    mid, _ = await _create_member(mem_db)
    now = datetime.now()
    # 2 days ago: arrived at 10:00, left at 12:00 => 120 minutes on that day
    base = now - timedelta(days=2)
    arrived_at = base.replace(hour=10, minute=0, second=0, microsecond=0)
    left_at = base.replace(hour=12, minute=0, second=0, microsecond=0)
    await _add_log(mem_db, mid, 'arrived', arrived_at)
    await _add_log(mem_db, mid, 'left', left_at)

    resp = await client.get(f'/api/v1/members/{mid}/stats?range=7d')
    assert resp.status_code == 200
    body = resp.json()
    assert body['total_minutes'] == 120


@pytest.mark.asyncio
async def test_get_member_stats_currently_home(client, mem_db):
    """Member arrived yesterday and never left — home time is counted up to now."""
    mid, _ = await _create_member(mem_db)
    now = datetime.now()
    # arrived yesterday at midnight => has been home for at least ~24 hours = 1440 minutes
    yesterday_midnight = (now - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    await _add_log(mem_db, mid, 'arrived', yesterday_midnight)

    resp = await client.get(f'/api/v1/members/{mid}/stats?range=7d')
    assert resp.status_code == 200
    body = resp.json()
    # Should be at least ~24 hours worth of minutes
    assert body['total_minutes'] >= 1380  # 23 hours minimum (allow some slack)


@pytest.mark.asyncio
async def test_get_member_stats_invalid_range(client, mem_db):
    mid, _ = await _create_member(mem_db)
    resp = await client.get(f'/api/v1/members/{mid}/stats?range=999d')
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_member_stats_404_on_missing_member(client):
    resp = await client.get('/api/v1/members/99999/stats?range=7d')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_member_stats_was_home_before_range(client, mem_db):
    """Member arrived before the range window — stats should count from window start."""
    mid, _ = await _create_member(mem_db)
    now = datetime.now()
    # arrived 10 days ago (outside 7d window), left 1 hour ago (inside window)
    await _add_log(mem_db, mid, 'arrived', now - timedelta(days=10))
    await _add_log(mem_db, mid, 'left', now - timedelta(hours=1))

    resp = await client.get(f'/api/v1/members/{mid}/stats?range=7d')
    assert resp.status_code == 200
    body = resp.json()
    # Should count from window start to when they left (~7 days minus 1 hour ≈ 9960 minutes)
    assert body['total_minutes'] > 9000

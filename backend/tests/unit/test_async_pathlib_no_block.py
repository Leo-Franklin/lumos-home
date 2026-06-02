"""ASYNC240 contract tests: async functions must not call blocking pathlib
methods on the event loop thread.

We monkeypatch the offending Path methods (`exists`, `stat`, `unlink`,
`mkdir`, `resolve`) so each call records the OS thread id it ran on. After
invoking the async function, we assert the recorded thread is NOT the main
event-loop thread — i.e. the call was dispatched via `asyncio.to_thread` /
`run_in_executor`.

These tests start RED before the fix (direct sync calls run on the loop
thread) and turn GREEN once the calls are wrapped in `asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Shared fixtures (mirror tests/integration/api/test_recordings.py)
# ---------------------------------------------------------------------------

_MAC = 'AA:BB:CC:DD:EE:F1'


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
    from app.deps import get_current_user, get_stream_user
    from app.main import app as fastapi_app

    async def override_get_db():
        async with mem_db() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: 'test@example.com'
    fastapi_app.dependency_overrides[get_stream_user] = lambda: 'test@example.com'

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url='http://test') as c:
        yield c

    fastapi_app.dependency_overrides.clear()


async def _seed_camera_and_device(mem_db):
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=_MAC, device_type='camera', is_online=True))
        await db.commit()
        db.add(Camera(device_mac=_MAC, onvif_host='192.168.1.10', rtsp_url='rtsp://x'))
        await db.commit()


async def _seed_recording(mem_db, **kwargs):
    from app.domain.models.recording import Recording

    defaults = {
        'camera_mac': _MAC,
        'file_path': '/data/recordings/test_video.mp4',
        'started_at': datetime(2025, 1, 15, 10, 0, 0),
        'status': 'completed',
        'file_size': 512 * 1024,
        'duration': 60,
    }
    defaults.update(kwargs)
    async with mem_db() as db:
        rec = Recording(**defaults)
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        return rec.id


# ---------------------------------------------------------------------------
# Thread-recording helpers
# ---------------------------------------------------------------------------


class _ThreadRecorder:
    """Wraps a callable and records the thread id of each call."""

    def __init__(self, real_callable):
        self._real = real_callable
        self.thread_ids: list[int] = []

    def __call__(self, *args, **kwargs):
        self.thread_ids.append(threading.get_ident())
        return self._real(*args, **kwargs)


def _patch_path_method(method_name: str, return_value):
    """Patch `pathlib.Path.<method_name>` so it records the calling thread.

    Returns the patcher (call .start()/.stop()) and the recorder.
    """
    recorder = _ThreadRecorder(lambda *a, **kw: return_value)

    def fake(self, *args, **kwargs):
        return recorder(self, *args, **kwargs)

    patcher = patch.object(Path, method_name, fake)
    return patcher, recorder


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_recording_unlink_runs_off_event_loop(client, mem_db):
    """DELETE /recordings/{id} → Path.unlink must run in a worker thread."""
    await _seed_camera_and_device(mem_db)
    rid = await _seed_recording(mem_db)

    main_tid = threading.get_ident()

    exists_patcher, exists_rec = _patch_path_method('exists', True)
    unlink_patcher, unlink_rec = _patch_path_method('unlink', None)

    exists_patcher.start()
    unlink_patcher.start()
    try:
        resp = await client.delete(f'/api/v1/recordings/{rid}')
    finally:
        unlink_patcher.stop()
        exists_patcher.stop()

    assert resp.status_code == 204
    # Both must have been observed, and on a non-loop thread.
    assert exists_rec.thread_ids, 'Path.exists was never called'
    assert unlink_rec.thread_ids, 'Path.unlink was never called'
    for tid in exists_rec.thread_ids + unlink_rec.thread_ids:
        assert tid != main_tid, (
            'blocking pathlib call ran on the event-loop thread '
            '(expected dispatch via asyncio.to_thread)'
        )


@pytest.mark.asyncio
async def test_open_folder_exists_runs_off_event_loop(client, mem_db):
    """POST /recordings/{id}/open-folder → Path.exists must run off-loop."""
    await _seed_camera_and_device(mem_db)
    rid = await _seed_recording(mem_db)

    main_tid = threading.get_ident()
    exists_patcher, exists_rec = _patch_path_method('exists', False)
    exists_patcher.start()
    try:
        resp = await client.post(f'/api/v1/recordings/{rid}/open-folder')
    finally:
        exists_patcher.stop()

    # File "does not exist" -> 404, but we only care the call happened off-loop.
    assert resp.status_code == 404
    assert exists_rec.thread_ids
    for tid in exists_rec.thread_ids:
        assert tid != main_tid


@pytest.mark.asyncio
async def test_recording_domain_cast_recording_runs_off_event_loop(tmp_path):
    """RecordingDomainService._cast_recording → src.exists + media_dir.mkdir off-loop."""
    from app.domain.services.recording_domain import RecordingDomainService

    main_tid = threading.get_ident()
    exists_patcher, exists_rec = _patch_path_method('exists', False)
    mkdir_patcher, mkdir_rec = _patch_path_method('mkdir', None)

    svc = RecordingDomainService(nas_syncer=None)  # type: ignore[arg-type]

    exists_patcher.start()
    mkdir_patcher.start()
    try:
        # exists -> False short-circuits before mkdir, so we test exists separately
        await svc._cast_recording(
            av_transport_url='http://x/AVTransport',
            file_path=str(tmp_path / 'missing.mp4'),
            camera_mac=_MAC,
        )
    finally:
        mkdir_patcher.stop()
        exists_patcher.stop()

    assert exists_rec.thread_ids, 'src.exists was never called'
    for tid in exists_rec.thread_ids:
        assert tid != main_tid, 'src.exists ran on event-loop thread'


@pytest.mark.asyncio
async def test_dlna_cleanup_media_file_unlink_runs_off_event_loop(tmp_path):
    """dlna._cleanup_media_file → Path.unlink must run off-loop."""
    from app.api.dlna import _cleanup_media_file

    main_tid = threading.get_ident()
    unlink_patcher, unlink_rec = _patch_path_method('unlink', None)

    target = tmp_path / 'whatever.mp4'
    unlink_patcher.start()
    try:
        await _cleanup_media_file(target, delay_seconds=0)
    finally:
        unlink_patcher.stop()

    assert unlink_rec.thread_ids, 'Path.unlink was never called'
    for tid in unlink_rec.thread_ids:
        assert tid != main_tid


@pytest.mark.asyncio
async def test_ruff_async240_clean():
    """Meta-test: ruff ASYNC240 violations must be zero across app/.

    This is the canonical contract — every blocking pathlib call in an
    async function should be wrapped via asyncio.to_thread / run_in_executor.
    """
    proc = await asyncio.create_subprocess_exec(
        'uv',
        'run',
        'ruff',
        'check',
        'app/',
        '--select=ASYNC240',
        '--output-format=concise',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode('utf-8', errors='replace')
    # ruff exits 0 with "All checks passed!" when clean.
    assert proc.returncode == 0, f'ASYNC240 violations remain:\n{output}'

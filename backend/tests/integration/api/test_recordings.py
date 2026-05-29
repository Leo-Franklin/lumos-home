"""Integration tests for app/api/recordings.py.

Patterns:
- in-memory SQLite with StaticPool (shared connection, data visible across sessions)
- override get_db via dependency_overrides
- override get_current_user / get_stream_user to skip JWT auth
- mock Path.exists / Path.stat / builtins.open for stream/download/delete endpoints
- pure-function unit tests for _compute_recording_extra
"""

from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, mock_open, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Shared in-memory DB fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mem_db():
    """In-memory SQLite engine (StaticPool) with all tables created."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    from app.database import Base

    # Import all models so Base.metadata knows about them
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


# ---------------------------------------------------------------------------
# HTTP client fixture — overrides DB + auth
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(mem_db):
    """AsyncClient wired to in-memory DB, with auth bypassed."""
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


# ---------------------------------------------------------------------------
# Helpers for seeding data
# ---------------------------------------------------------------------------

_MAC = 'AA:BB:CC:DD:EE:01'


async def _seed_camera_and_device(mem_db):
    """Create a Device + Camera row required by the FK on recordings.camera_mac."""
    from app.domain.models.camera import Camera
    from app.models.device import Device

    async with mem_db() as db:
        db.add(Device(mac=_MAC, device_type='camera', is_online=True))
        await db.commit()
        db.add(Camera(device_mac=_MAC, onvif_host='192.168.1.10', rtsp_url='rtsp://x'))
        await db.commit()


async def _seed_recording(mem_db, **kwargs):
    """Insert a Recording row and return its id."""
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


# ===========================================================================
# Unit tests: _compute_recording_extra
# ===========================================================================


class TestComputeRecordingExtra:
    """Pure-function unit tests — no HTTP, no DB."""

    def _settings(self, **overrides):
        s = MagicMock()
        s.nas_mode = 'local'
        s.nas_mount_path = '/nas/cameras'
        s.nas_smb_host = ''
        s.nas_smb_share = ''
        for k, v in overrides.items():
            setattr(s, k, v)
        return s

    def test_local_mode_returns_local(self):
        from app.api.recordings import _compute_recording_extra

        storage_type, url, fname = _compute_recording_extra(
            '/data/recordings/cam_20250115.mp4', self._settings(nas_mode='local')
        )
        assert storage_type == 'local'
        assert url is None
        assert fname == 'cam_20250115.mp4'

    def test_mount_mode_file_under_mount_path(self):
        from app.api.recordings import _compute_recording_extra

        s = self._settings(nas_mode='mount', nas_mount_path='/nas/cameras')
        storage_type, url, fname = _compute_recording_extra('/nas/cameras/2025/video.mp4', s)
        assert storage_type == 'nas'
        assert url is None

    def test_mount_mode_file_not_under_mount_path(self):
        from app.api.recordings import _compute_recording_extra

        s = self._settings(nas_mode='mount', nas_mount_path='/nas/cameras')
        storage_type, url, fname = _compute_recording_extra('/local/data/video.mp4', s)
        assert storage_type == 'local'
        assert url is None

    def test_smb_mode_unc_path_constructs_url(self):
        from app.api.recordings import _compute_recording_extra

        s = self._settings(nas_mode='smb', nas_smb_host='192.168.1.100', nas_smb_share='videos')
        unc = '\\\\192.168.1.100\\videos\\cams\\video.mp4'
        storage_type, url, fname = _compute_recording_extra(unc, s)
        assert storage_type == 'nas'
        assert url == 'smb://192.168.1.100/videos/cams/video.mp4'
        assert fname == 'video.mp4'

    def test_smb_mode_unc_path_minimal(self):
        """UNC path with only host\\share (no sub-path)."""
        from app.api.recordings import _compute_recording_extra

        s = self._settings(nas_mode='smb')
        unc = '\\\\host\\share'
        storage_type, url, fname = _compute_recording_extra(unc, s)
        assert storage_type == 'nas'
        assert url == 'smb://host/share'

    def test_smb_mode_mount_path_with_host_and_share(self):
        from app.api.recordings import _compute_recording_extra

        s = self._settings(
            nas_mode='smb',
            nas_mount_path='/nas/cameras',
            nas_smb_host='nas-server',
            nas_smb_share='recordings',
        )
        storage_type, url, fname = _compute_recording_extra('/nas/cameras/video.mp4', s)
        assert storage_type == 'nas'
        assert url == 'smb://nas-server/recordings/video.mp4'

    def test_smb_mode_mount_path_no_host(self):
        from app.api.recordings import _compute_recording_extra

        s = self._settings(
            nas_mode='smb', nas_mount_path='/nas/cameras', nas_smb_host='', nas_smb_share=''
        )
        storage_type, url, fname = _compute_recording_extra('/nas/cameras/video.mp4', s)
        assert storage_type == 'nas'
        assert url is None

    def test_smb_mode_local_path(self):
        from app.api.recordings import _compute_recording_extra

        s = self._settings(nas_mode='smb', nas_mount_path='/nas/cameras')
        storage_type, url, fname = _compute_recording_extra('/data/video.mp4', s)
        assert storage_type == 'local'
        assert url is None

    def test_unknown_mode_falls_back_to_local(self):
        from app.api.recordings import _compute_recording_extra

        s = self._settings(nas_mode='unknown')
        storage_type, url, fname = _compute_recording_extra('/data/video.mp4', s)
        assert storage_type == 'local'
        assert url is None


# ===========================================================================
# Integration tests: GET /api/v1/recordings
# ===========================================================================


@pytest.mark.asyncio
async def test_list_recordings_empty(client):
    resp = await client.get('/api/v1/recordings')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 0
    assert data['items'] == []


@pytest.mark.asyncio
async def test_list_recordings_returns_items(client, mem_db):
    await _seed_camera_and_device(mem_db)
    await _seed_recording(mem_db)

    resp = await client.get('/api/v1/recordings')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 1
    assert len(data['items']) == 1
    item = data['items'][0]
    assert item['camera_mac'] == _MAC
    assert item['status'] == 'completed'
    assert 'storage_type' in item
    assert 'file_name' in item


@pytest.mark.asyncio
async def test_list_recordings_filter_by_camera_mac(client, mem_db):
    await _seed_camera_and_device(mem_db)
    await _seed_recording(mem_db)

    resp = await client.get(f'/api/v1/recordings?camera_mac={_MAC}')
    assert resp.status_code == 200
    assert resp.json()['total'] == 1

    resp2 = await client.get('/api/v1/recordings?camera_mac=00:00:00:00:00:00')
    assert resp2.status_code == 200
    assert resp2.json()['total'] == 0


@pytest.mark.asyncio
async def test_list_recordings_filter_by_date(client, mem_db):
    await _seed_camera_and_device(mem_db)
    await _seed_recording(mem_db, started_at=datetime(2025, 1, 15, 10, 0, 0))

    resp = await client.get('/api/v1/recordings?date=2025-01-15')
    assert resp.status_code == 200
    assert resp.json()['total'] == 1

    resp2 = await client.get('/api/v1/recordings?date=2025-01-16')
    assert resp2.status_code == 200
    assert resp2.json()['total'] == 0


@pytest.mark.asyncio
async def test_list_recordings_pagination(client, mem_db):
    await _seed_camera_and_device(mem_db)
    for i in range(5):
        await _seed_recording(
            mem_db, started_at=datetime(2025, 1, 15, 10, i, 0), file_path=f'/data/r{i}.mp4'
        )

    resp = await client.get('/api/v1/recordings?page=1&page_size=2')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 5
    assert len(data['items']) == 2
    assert data['pages'] == 3
    assert data['page'] == 1


# ===========================================================================
# Integration tests: GET /api/v1/recordings/stats
# ===========================================================================


@pytest.mark.asyncio
async def test_recording_stats_empty(client):
    resp = await client.get('/api/v1/recordings/stats')
    assert resp.status_code == 200
    data = resp.json()
    assert data['count'] == 0
    assert data['total_duration'] == 0
    assert data['total_size'] == 0
    assert data['range'] == '7d'


@pytest.mark.asyncio
async def test_recording_stats_with_data(client, mem_db):
    from datetime import timedelta

    # Use recent dates so they fall within the stats range window
    now = datetime.utcnow()
    recent1 = now - timedelta(days=1)
    recent2 = now - timedelta(days=2)

    await _seed_camera_and_device(mem_db)
    await _seed_recording(mem_db, duration=120, file_size=1024 * 1024, started_at=recent1)
    await _seed_recording(
        mem_db,
        duration=60,
        file_size=512 * 1024,
        file_path='/data/r2.mp4',
        started_at=recent2,
    )

    resp = await client.get('/api/v1/recordings/stats?range=30d')
    assert resp.status_code == 200
    data = resp.json()
    assert data['count'] == 2
    assert data['total_duration'] == 180
    assert data['total_size'] == 1024 * 1024 + 512 * 1024
    assert data['range'] == '30d'


@pytest.mark.asyncio
async def test_recording_stats_invalid_range(client):
    resp = await client.get('/api/v1/recordings/stats?range=invalid')
    assert resp.status_code == 422


# ===========================================================================
# Integration tests: GET /api/v1/recordings/{id}
# ===========================================================================


@pytest.mark.asyncio
async def test_get_recording_not_found(client):
    resp = await client.get('/api/v1/recordings/9999')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_recording_found(client, mem_db):
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db)

    resp = await client.get(f'/api/v1/recordings/{rec_id}')
    assert resp.status_code == 200
    data = resp.json()
    assert data['id'] == rec_id
    assert data['camera_mac'] == _MAC
    assert data['file_name'] == 'test_video.mp4'
    assert data['storage_type'] == 'local'
    assert data['nas_access_url'] is None


# ===========================================================================
# Integration tests: DELETE /api/v1/recordings/{id}
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_recording_not_found(client):
    resp = await client.delete('/api/v1/recordings/9999')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_recording_file_not_exist(client, mem_db):
    """File does not exist on disk — should delete DB row and return 204."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db)

    with patch('app.api.recordings.Path') as mock_path_cls:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        resp = await client.delete(f'/api/v1/recordings/{rec_id}')

    assert resp.status_code == 204

    # Verify DB row was removed
    resp2 = await client.get(f'/api/v1/recordings/{rec_id}')
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_recording_file_exists(client, mem_db):
    """File exists on disk — should call unlink and return 204."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db)

    with patch('app.api.recordings.Path') as mock_path_cls:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_cls.return_value = mock_path_instance

        resp = await client.delete(f'/api/v1/recordings/{rec_id}')

    assert resp.status_code == 204
    mock_path_instance.unlink.assert_called_once()


@pytest.mark.asyncio
async def test_delete_recording_oserror(client, mem_db):
    """unlink raises OSError — should return 409."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db)

    with patch('app.api.recordings.Path') as mock_path_cls:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        err = OSError('file in use')
        err.strerror = 'file in use'
        mock_path_instance.unlink.side_effect = err
        mock_path_cls.return_value = mock_path_instance

        resp = await client.delete(f'/api/v1/recordings/{rec_id}')

    assert resp.status_code == 409


# ===========================================================================
# Integration tests: GET /api/v1/recordings/{id}/stream
# ===========================================================================

# Use a storage path that matches the file path in seeded recordings
_STORAGE_ROOT = '/data/recordings'
_FILE_PATH = f'{_STORAGE_ROOT}/test_video.mp4'
_FILE_SIZE = 1024 * 1024  # 1 MB (> 10 KB minimum)


def _make_path_mock(exists=True, file_size=_FILE_SIZE, is_absolute=True):
    """Build a Path mock that passes the security check."""
    mock_path = MagicMock()
    mock_path.exists.return_value = exists
    mock_path.is_absolute.return_value = is_absolute

    stat_result = MagicMock()
    stat_result.st_size = file_size
    mock_path.stat.return_value = stat_result

    # resolve() must return itself (or something is_relative_to passes)
    mock_path.resolve.return_value = mock_path
    mock_path.is_relative_to.return_value = True
    mock_path.__str__ = lambda self: _FILE_PATH
    return mock_path


@pytest.mark.asyncio
async def test_stream_recording_not_found(client):
    resp = await client.get('/api/v1/recordings/9999/stream')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stream_recording_not_completed(client, mem_db):
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, status='recording')

    resp = await client.get(f'/api/v1/recordings/{rec_id}/stream')
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_stream_recording_relative_path_rejected(client, mem_db):
    """Relative file paths should be rejected with 403."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path='relative/path/video.mp4')

    resp = await client.get(f'/api/v1/recordings/{rec_id}/stream')
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stream_recording_path_outside_storage_root(client, mem_db):
    """File path outside storage root should return 403."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path='/etc/passwd')

    # Don't mock Path — let real path resolution run to trigger the security check
    # The real storage_root won't contain /etc/passwd
    resp = await client.get(f'/api/v1/recordings/{rec_id}/stream')
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stream_recording_file_not_found_on_disk(client, mem_db):
    """Completed recording but file missing on disk → 404."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    with (
        patch('pathlib.Path.exists', return_value=False),
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
    ):
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(f'/api/v1/recordings/{rec_id}/stream')

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stream_recording_file_too_small(client, mem_db):
    """File exists but too small (< 10 KB) → 422."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    fake_data = b'x' * 100  # tiny file
    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.stat') as mock_stat,
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
    ):
        stat_result = MagicMock()
        stat_result.st_size = len(fake_data)
        mock_stat.return_value = stat_result
        mock_resolve.return_value = MagicMock(
            is_relative_to=lambda *a, **kw: True,
        )

        resp = await client.get(f'/api/v1/recordings/{rec_id}/stream')

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stream_recording_full_response(client, mem_db):
    """Full stream (no Range header) returns 200 with video/mp4."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    fake_data = b'A' * _FILE_SIZE
    m = mock_open(read_data=fake_data)

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.stat') as mock_stat,
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
        patch('builtins.open', m),
    ):
        stat_result = MagicMock()
        stat_result.st_size = _FILE_SIZE
        mock_stat.return_value = stat_result
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(f'/api/v1/recordings/{rec_id}/stream')

    assert resp.status_code == 200
    assert resp.headers['content-type'] == 'video/mp4'
    assert resp.headers['accept-ranges'] == 'bytes'
    assert resp.headers['content-length'] == str(_FILE_SIZE)


@pytest.mark.asyncio
async def test_stream_recording_range_request(client, mem_db):
    """Range request returns 206 Partial Content."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    fake_data = b'B' * _FILE_SIZE

    def mock_open_factory(*args, **kwargs):
        buf = BytesIO(fake_data)
        m = MagicMock()
        m.__enter__ = lambda s: buf
        m.__exit__ = MagicMock(return_value=False)
        return m

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.stat') as mock_stat,
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
        patch('builtins.open', side_effect=mock_open_factory),
    ):
        stat_result = MagicMock()
        stat_result.st_size = _FILE_SIZE
        mock_stat.return_value = stat_result
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(
            f'/api/v1/recordings/{rec_id}/stream', headers={'Range': 'bytes=0-1023'}
        )

    assert resp.status_code == 206
    assert 'content-range' in resp.headers
    assert resp.headers['content-range'] == f'bytes 0-1023/{_FILE_SIZE}'
    assert resp.headers['content-length'] == '1024'


@pytest.mark.asyncio
async def test_stream_recording_range_out_of_bounds(client, mem_db):
    """Range exceeding file size → 416."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.stat') as mock_stat,
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
    ):
        stat_result = MagicMock()
        stat_result.st_size = _FILE_SIZE
        mock_stat.return_value = stat_result
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(
            f'/api/v1/recordings/{rec_id}/stream',
            headers={'Range': f'bytes=0-{_FILE_SIZE + 9999}'},
        )

    assert resp.status_code == 416


@pytest.mark.asyncio
async def test_stream_recording_range_bad_format(client, mem_db):
    """Malformed Range header → 400."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.stat') as mock_stat,
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
    ):
        stat_result = MagicMock()
        stat_result.st_size = _FILE_SIZE
        mock_stat.return_value = stat_result
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(
            f'/api/v1/recordings/{rec_id}/stream',
            headers={'Range': 'bytes=notanumber-'},
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_stream_recording_suffix_range(client, mem_db):
    """Suffix range (bytes=-N) returns last N bytes as 206."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    fake_data = b'C' * _FILE_SIZE

    def mock_open_factory(*args, **kwargs):
        buf = BytesIO(fake_data)
        m = MagicMock()
        m.__enter__ = lambda s: buf
        m.__exit__ = MagicMock(return_value=False)
        return m

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.stat') as mock_stat,
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
        patch('builtins.open', side_effect=mock_open_factory),
    ):
        stat_result = MagicMock()
        stat_result.st_size = _FILE_SIZE
        mock_stat.return_value = stat_result
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(
            f'/api/v1/recordings/{rec_id}/stream', headers={'Range': 'bytes=-512'}
        )

    assert resp.status_code == 206
    expected_start = _FILE_SIZE - 512
    assert resp.headers['content-range'] == f'bytes {expected_start}-{_FILE_SIZE - 1}/{_FILE_SIZE}'


# ===========================================================================
# Integration tests: GET /api/v1/recordings/{id}/download
# ===========================================================================


@pytest.mark.asyncio
async def test_download_recording_not_found(client):
    resp = await client.get('/api/v1/recordings/9999/download')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_recording_not_completed(client, mem_db):
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, status='failed')

    resp = await client.get(f'/api/v1/recordings/{rec_id}/download')
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_download_recording_relative_path_rejected(client, mem_db):
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path='relative/path/video.mp4')

    resp = await client.get(f'/api/v1/recordings/{rec_id}/download')
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_download_recording_success(client, mem_db):
    """Download returns 200 with content-disposition header."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    fake_data = b'D' * _FILE_SIZE
    m = mock_open(read_data=fake_data)

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.stat') as mock_stat,
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
        patch('builtins.open', m),
    ):
        stat_result = MagicMock()
        stat_result.st_size = _FILE_SIZE
        mock_stat.return_value = stat_result
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(f'/api/v1/recordings/{rec_id}/download')

    assert resp.status_code == 200
    assert 'attachment' in resp.headers['content-disposition']
    assert 'test_video.mp4' in resp.headers['content-disposition']


@pytest.mark.asyncio
async def test_download_recording_file_not_on_disk(client, mem_db):
    """File not found on disk → 404."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db, file_path=_FILE_PATH)

    with (
        patch('pathlib.Path.exists', return_value=False),
        patch('pathlib.Path.is_absolute', return_value=True),
        patch('pathlib.Path.resolve') as mock_resolve,
        patch('pathlib.Path.is_relative_to', return_value=True),
    ):
        mock_resolve.return_value = MagicMock(is_relative_to=lambda *a, **kw: True)

        resp = await client.get(f'/api/v1/recordings/{rec_id}/download')

    assert resp.status_code == 404


# ===========================================================================
# Integration tests: POST /api/v1/recordings/{id}/open-folder
# ===========================================================================


@pytest.mark.asyncio
async def test_open_folder_not_found(client):
    resp = await client.post('/api/v1/recordings/9999/open-folder')
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_open_folder_file_not_exist(client, mem_db):
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db)

    with patch('app.api.recordings.Path') as mock_path_cls:
        p = MagicMock()
        p.exists.return_value = False
        mock_path_cls.return_value = p

        resp = await client.post(f'/api/v1/recordings/{rec_id}/open-folder')

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_open_folder_success(client, mem_db):
    """open-folder calls subprocess.Popen and returns 200."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db)

    with patch('app.api.recordings.Path') as mock_path_cls, patch('subprocess.Popen') as mock_popen:
        p = MagicMock()
        p.exists.return_value = True
        mock_path_cls.return_value = p
        mock_popen.return_value = MagicMock()

        resp = await client.post(f'/api/v1/recordings/{rec_id}/open-folder')

    assert resp.status_code == 200
    assert resp.json()['message'] == 'ok'
    mock_popen.assert_called_once()


@pytest.mark.asyncio
async def test_open_folder_popen_error(client, mem_db):
    """subprocess.Popen raises → 500."""
    await _seed_camera_and_device(mem_db)
    rec_id = await _seed_recording(mem_db)

    with patch('app.api.recordings.Path') as mock_path_cls, patch('subprocess.Popen') as mock_popen:
        p = MagicMock()
        p.exists.return_value = True
        mock_path_cls.return_value = p
        mock_popen.side_effect = RuntimeError('no explorer')

        resp = await client.post(f'/api/v1/recordings/{rec_id}/open-folder')

    assert resp.status_code == 500

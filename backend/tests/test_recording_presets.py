import pytest

from app.domain.models.camera import Camera, RecordingPreset


def test_recording_preset_to_dict():
    preset = RecordingPreset(
        id='test-123',
        name='室外-1080p',
        resolution='1920x1080',
        segment_duration=600,
        bitrate=2048,
        fps=25,
    )
    data = preset.to_dict()
    assert data['id'] == 'test-123'
    assert data['name'] == '室外-1080p'
    assert data['resolution'] == '1920x1080'
    assert data['bitrate'] == 2048
    assert data['fps'] == 25
    assert data['is_default'] is False

    data_default = preset.to_dict(is_default=True)
    assert data_default['is_default'] is True


def test_recording_preset_from_dict():
    data = {
        'id': 'abc-456',
        'name': '室内-720p',
        'resolution': '1280x720',
        'segment_duration': 1800,
        'bitrate': None,
        'fps': 20,
    }
    preset = RecordingPreset.from_dict(data)
    assert preset.id == 'abc-456'
    assert preset.resolution == '1280x720'
    assert preset.fps == 20


def test_camera_preset_management():
    cam = Camera(device_mac='AA:BB:CC:DD:EE:FF', onvif_host='192.168.1.100')
    assert cam.get_presets() == []

    preset = RecordingPreset(
        id='preset-1',
        name='测试预设',
        resolution='1920x1080',
        segment_duration=600,
    )
    cam.add_preset(preset)
    assert len(cam.get_presets()) == 1
    assert cam.get_presets()[0].name == '测试预设'

    cam.default_preset_id = 'preset-1'
    default = cam.get_default_preset()
    assert default is not None
    assert default.id == 'preset-1'

    cam.remove_preset('preset-1')
    assert len(cam.get_presets()) == 0
    assert cam.get_default_preset() is None


def test_camera_update_preset():
    cam = Camera(device_mac='AA:BB:CC:DD:EE:FF', onvif_host='192.168.1.100')
    preset = RecordingPreset(id='p1', name='原始名称', resolution='1920x1080', segment_duration=600)
    cam.add_preset(preset)

    cam.update_preset('p1', {'name': '新名称', 'segment_duration': 1200})
    updated = cam.get_presets()[0]
    assert updated.name == '新名称'
    assert updated.segment_duration == 1200
    assert updated.resolution == '1920x1080'  # 未改动的字段保持不变


# ── Schedule preset_id / overrides tests ──────────────────────────────────

from app.domain.models.schedule import Schedule


def test_schedule_preset_and_overrides_fields():
    """验证 Schedule preset_id 和 overrides 字段的存取"""
    schedule = Schedule(
        camera_mac='AA:BB:CC:DD:EE:FF',
        cron_expr='0 * * * *',
        segment_duration=1800,
    )
    assert schedule.preset_id is None
    assert schedule.overrides is None

    schedule.preset_id = 'preset-abc'
    schedule.set_overrides({'segment_duration': 900, 'bitrate': 4096})

    assert schedule.preset_id == 'preset-abc'
    assert schedule.get_overrides() == {'segment_duration': 900, 'bitrate': 4096}


def test_schedule_get_effective_segment_duration():
    """验证 get_effective_segment_duration 优先使用 overrides 中的值"""
    schedule = Schedule(
        camera_mac='AA:BB:CC:DD:EE:FF',
        cron_expr='0 * * * *',
        segment_duration=1800,
    )

    # 无 overrides 时返回 self.segment_duration
    assert schedule.get_effective_segment_duration() == 1800

    # 有 overrides 时优先用 overrides 中的值
    schedule.set_overrides({'segment_duration': 600})
    assert schedule.get_effective_segment_duration() == 600

    # overrides 中无 segment_duration 时仍回退到 self
    schedule.set_overrides({'bitrate': 2048})
    assert schedule.get_effective_segment_duration() == 1800


def test_schedule_overrides_invalid_json():
    """验证 get_overrides 对无效 JSON 返回 None"""
    schedule = Schedule(
        camera_mac='AA:BB:CC:DD:EE:FF',
        cron_expr='0 * * * *',
        segment_duration=1800,
    )
    schedule.overrides = 'not valid json'
    assert schedule.get_overrides() is None


def test_schedule_set_overrides_to_none():
    """验证 set_overrides(None) 清除 overrides"""
    schedule = Schedule(
        camera_mac='AA:BB:CC:DD:EE:FF',
        cron_expr='0 * * * *',
        segment_duration=1800,
    )
    schedule.set_overrides({'segment_duration': 600})
    assert schedule.overrides is not None
    schedule.set_overrides(None)
    assert schedule.overrides is None
    assert schedule.get_overrides() is None


# ── API tests ────────────────────────────────────────────────────

import uuid

from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache before and after each test to ensure monkeypatch env vars take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def unique_mac():
    """Generate unique MAC per test to avoid conflicts across test runs."""
    return f'11:22:33:{uuid.uuid4().hex[:2]}:{uuid.uuid4().hex[:2]}:{uuid.uuid4().hex[:2]}'


@pytest.fixture
def test_env(monkeypatch):
    """Set required env vars for tests and clear cache."""
    monkeypatch.setenv('JWT_SECRET_KEY', 'test_secret_key_that_is_at_least_32_characters_long')
    monkeypatch.setenv('ADMIN_PASSWORD', 'testpassword_for_ci_only')
    monkeypatch.setenv('CORS_ALLOW_ORIGINS', 'http://localhost:5173')
    get_settings.cache_clear()
    # Provide a basic mock recorder in app.state for schedule callbacks that run during requests
    mock_rec = MagicMock()
    mock_rec.start_recording = AsyncMock(return_value='/tmp/test.mp4')
    mock_rec.active = {}
    # stop_recording should return a path-like object
    mock_stop_result = MagicMock()
    mock_stop_result.exists.return_value = True
    mock_stop_result.stat.return_value.st_size = 1024 * 1024
    mock_rec.stop_recording = MagicMock(return_value=mock_stop_result)

    # Mock sync_file to return a proper path-like mock
    class FakeSyncResult:
        def __init__(self):
            self._st_size = 1024 * 1024

        def exists(self):
            return True

        def stat(self):
            return self

        @property
        def st_size(self):
            return self._st_size

        def __str__(self):
            return '/nas/recordings/test.mp4'

    fake_sync = FakeSyncResult()
    mock_rec.sync_file = MagicMock(return_value=fake_sync)
    app.state.recorder = mock_rec
    mock_ns = MagicMock()
    mock_ns.sync_file = MagicMock(return_value=fake_sync)
    mock_ns.check_writable.return_value = True
    app.state.nas_syncer = mock_ns


@pytest.mark.asyncio
async def test_crud_presets(test_env, unique_mac):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        # Login first to get auth token
        resp = await ac.post(
            '/api/v1/auth/login',
            data={'username': 'admin', 'password': 'testpassword_for_ci_only'},
        )
        assert resp.status_code == 200
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # 首先创建摄像机
        resp = await ac.post(
            '/api/v1/cameras',
            json={
                'device_mac': unique_mac,
                'onvif_host': '192.168.1.50',
            },
            headers=headers,
        )
        assert resp.status_code == 201

        mac = unique_mac

        # 创建预设
        resp = await ac.post(
            f'/api/v1/cameras/{mac}/presets',
            json={
                'name': '测试预设',
                'resolution': '1920x1080',
                'segment_duration': 600,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == '测试预设'
        preset_id = data['id']

        # 获取预设列表
        resp = await ac.get(f'/api/v1/cameras/{mac}/presets', headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # 更新预设
        resp = await ac.put(
            f'/api/v1/cameras/{mac}/presets/{preset_id}',
            json={
                'name': '已更新',
                'segment_duration': 1200,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()['name'] == '已更新'
        assert resp.json()['segment_duration'] == 1200

        # 设置默认
        resp = await ac.post(
            f'/api/v1/cameras/{mac}/presets/default', json={'preset_id': preset_id}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()['default_preset_id'] == preset_id

        # 删除预设
        resp = await ac.delete(f'/api/v1/cameras/{mac}/presets/{preset_id}', headers=headers)
        assert resp.status_code == 204

        resp = await ac.get(f'/api/v1/cameras/{mac}/presets', headers=headers)
        assert len(resp.json()) == 0


# ── End-to-end recording with preset tests ──────────────────────────────────

from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_end_to_end_recording_with_preset(test_env, unique_mac):
    """Test complete flow: create camera -> add preset -> start recording with preset -> verify -> stop"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        # Login
        resp = await ac.post(
            '/api/v1/auth/login',
            data={'username': 'admin', 'password': 'testpassword_for_ci_only'},
        )
        assert resp.status_code == 200
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        mac = unique_mac

        # Create camera
        resp = await ac.post(
            '/api/v1/cameras',
            json={
                'device_mac': mac,
                'onvif_host': '192.168.1.50',
                'rtsp_url': 'rtsp://192.168.1.50:554/stream',
            },
            headers=headers,
        )
        assert resp.status_code == 201

        # Add preset with specific params
        resp = await ac.post(
            f'/api/v1/cameras/{mac}/presets',
            json={
                'name': '室外-1080p',
                'resolution': '1920x1080',
                'segment_duration': 600,
                'bitrate': 2048,
                'fps': 25,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        preset_id = resp.json()['id']
        assert resp.json()['resolution'] == '1920x1080'
        assert resp.json()['segment_duration'] == 600
        assert resp.json()['bitrate'] == 2048

        # Mock the recorder so we can inspect params without running ffmpeg
        mock_recorder = MagicMock()
        # Mock the recorder so we can inspect params without running ffmpeg
        mock_recorder = MagicMock()
        mock_start = AsyncMock(return_value='/tmp/test.mp4')
        mock_recorder.start_recording = mock_start
        mock_recorder.active = {}

        # Patch get_recorder to return our mock, and update app.state.recorder to match
        with patch('app.deps.get_recorder', return_value=mock_recorder):
            # Also update app.state.recorder so that stop_recording can use our mock's sync_file
            app.state.recorder = mock_recorder

            # Start recording with preset_id
            resp = await ac.post(
                f'/api/v1/cameras/{mac}/record/start',
                json={'preset_id': preset_id},
                headers=headers,
            )
            assert resp.status_code == 202, (
                f'Expected 202 but got {resp.status_code}: {resp.text[:200]}'
            )

            # Verify start_recording was called with correct params from preset
            mock_recorder.start_recording.assert_called_once()
            call_args = mock_recorder.start_recording.call_args
            _, _, params = call_args[0]  # mac, rtsp_url, params
            assert params.resolution == '1920x1080'
            assert params.segment_seconds == 600
            assert params.bitrate == 2048
            assert params.fps == 25

            # Verify recording_id is returned
            assert 'recording_id' in resp.json()

            # Stop recording - provide a fake result with proper __str__
            class FakeStopResult:
                def __init__(self):
                    self._st_size = 1024 * 1024

                def exists(self):
                    return True

                def stat(self):
                    return self

                @property
                def st_size(self):
                    return self._st_size

                def __str__(self):
                    return '/tmp/test_output.mp4'

            mock_recorder.stop_recording = AsyncMock(return_value=FakeStopResult())
            mock_recorder.active = {mac: MagicMock(recording_id=resp.json()['recording_id'])}

            resp = await ac.post(f'/api/v1/cameras/{mac}/record/stop', headers=headers)
            assert resp.status_code == 202
            assert resp.json()['message'] == '录制已停止'


@pytest.mark.asyncio
async def test_start_recording_with_overrides(test_env, unique_mac):
    """Start recording with overrides only (no preset)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        resp = await ac.post(
            '/api/v1/auth/login',
            data={'username': 'admin', 'password': 'testpassword_for_ci_only'},
        )
        assert resp.status_code == 200
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        mac = unique_mac

        resp = await ac.post(
            '/api/v1/cameras',
            json={
                'device_mac': mac,
                'onvif_host': '192.168.1.50',
                'rtsp_url': 'rtsp://192.168.1.50:554/stream',
            },
            headers=headers,
        )
        assert resp.status_code == 201

        mock_recorder = MagicMock()
        mock_recorder.start_recording = AsyncMock(return_value='/tmp/test.mp4')
        mock_recorder.active = {}
        mock_recorder.stop_recording = AsyncMock(
            return_value=MagicMock(
                exists=MagicMock(return_value=True), stat=MagicMock(st_size=1024 * 1024)
            )
        )

        with patch('app.deps.get_recorder', return_value=mock_recorder):
            app.state.recorder = mock_recorder

            # Start recording with overrides only
            resp = await ac.post(
                f'/api/v1/cameras/{mac}/record/start',
                json={
                    'overrides': {'resolution': '1280x720', 'segment_seconds': 900, 'bitrate': 1024}
                },
                headers=headers,
            )
            assert resp.status_code == 202

            call_args = mock_recorder.start_recording.call_args
            _, _, params = call_args[0]
            assert params.resolution == '1280x720'
            assert params.segment_seconds == 900
            assert params.bitrate == 1024


@pytest.mark.asyncio
async def test_start_recording_preset_plus_overrides(test_env, unique_mac):
    """Start recording with preset + overrides merged correctly (overrides win)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        resp = await ac.post(
            '/api/v1/auth/login',
            data={'username': 'admin', 'password': 'testpassword_for_ci_only'},
        )
        assert resp.status_code == 200
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        mac = unique_mac

        resp = await ac.post(
            '/api/v1/cameras',
            json={
                'device_mac': mac,
                'onvif_host': '192.168.1.50',
                'rtsp_url': 'rtsp://192.168.1.50:554/stream',
            },
            headers=headers,
        )
        assert resp.status_code == 201

        # Add preset
        resp = await ac.post(
            f'/api/v1/cameras/{mac}/presets',
            json={
                'name': '预设-1080p',
                'resolution': '1920x1080',
                'segment_duration': 600,
                'bitrate': 2048,
                'fps': 25,
            },
            headers=headers,
        )
        preset_id = resp.json()['id']

        mock_recorder = MagicMock()
        mock_recorder.start_recording = AsyncMock(return_value='/tmp/test.mp4')
        mock_recorder.active = {}

        with patch('app.deps.get_recorder', return_value=mock_recorder):
            app.state.recorder = mock_recorder

            # Start recording with preset + overrides (override bitrate and fps)
            resp = await ac.post(
                f'/api/v1/cameras/{mac}/record/start',
                json={'preset_id': preset_id, 'overrides': {'bitrate': 4096, 'fps': 30}},
                headers=headers,
            )
            assert resp.status_code == 202

            call_args = mock_recorder.start_recording.call_args
            _, _, params = call_args[0]
            # Preset values for non-overridden fields
            assert params.resolution == '1920x1080'
            assert params.segment_seconds == 600
            # Override values
            assert params.bitrate == 4096
            assert params.fps == 30


@pytest.mark.asyncio
async def test_schedule_with_preset_and_overrides(test_env, unique_mac):
    """Schedule uses preset_id and overrides correctly"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        resp = await ac.post(
            '/api/v1/auth/login',
            data={'username': 'admin', 'password': 'testpassword_for_ci_only'},
        )
        assert resp.status_code == 200
        token = resp.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        mac = unique_mac

        resp = await ac.post(
            '/api/v1/cameras',
            json={
                'device_mac': mac,
                'onvif_host': '192.168.1.50',
                'rtsp_url': 'rtsp://192.168.1.50:554/stream',
            },
            headers=headers,
        )
        assert resp.status_code == 201

        # Add preset
        resp = await ac.post(
            f'/api/v1/cameras/{mac}/presets',
            json={
                'name': 'schedule-preset',
                'resolution': '1280x720',
                'segment_duration': 1800,
                'bitrate': 1024,
            },
            headers=headers,
        )
        preset_id = resp.json()['id']

        # Create schedule with preset_id and overrides
        resp = await ac.post(
            '/api/v1/schedules',
            json={
                'camera_mac': mac,
                'cron_expr': '0 * * * *',
                'preset_id': preset_id,
                'overrides': {'segment_duration': 900, 'bitrate': 2048},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        schedule_data = resp.json()
        assert schedule_data['preset_id'] == preset_id
        assert schedule_data['overrides'] == {'segment_duration': 900, 'bitrate': 2048}

        # Get schedule and verify
        schedule_id = schedule_data['id']
        resp = await ac.get(f'/api/v1/schedules/{schedule_id}', headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['preset_id'] == preset_id
        assert data['overrides'] == {'segment_duration': 900, 'bitrate': 2048}

        # Verify get_effective_segment_duration via schedule model
        from app.domain.models.schedule import Schedule

        schedule = Schedule(
            camera_mac=mac,
            cron_expr='0 * * * *',
            segment_duration=1800,
        )
        schedule.preset_id = preset_id
        schedule.set_overrides({'segment_duration': 900, 'bitrate': 2048})
        assert schedule.get_effective_segment_duration() == 900

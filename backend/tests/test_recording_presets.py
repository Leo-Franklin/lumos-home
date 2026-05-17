import pytest
from app.domain.models.camera import Camera, RecordingPreset


def test_recording_preset_to_dict():
    preset = RecordingPreset(
        id="test-123",
        name="室外-1080p",
        resolution="1920x1080",
        segment_duration=600,
        bitrate=2048,
        fps=25,
    )
    data = preset.to_dict()
    assert data["id"] == "test-123"
    assert data["name"] == "室外-1080p"
    assert data["resolution"] == "1920x1080"
    assert data["bitrate"] == 2048


def test_recording_preset_from_dict():
    data = {
        "id": "abc-456",
        "name": "室内-720p",
        "resolution": "1280x720",
        "segment_duration": 1800,
        "bitrate": None,
        "fps": 20,
    }
    preset = RecordingPreset.from_dict(data)
    assert preset.id == "abc-456"
    assert preset.resolution == "1280x720"
    assert preset.fps == 20


def test_camera_preset_management():
    cam = Camera(device_mac="AA:BB:CC:DD:EE:FF", onvif_host="192.168.1.100")
    assert cam.get_presets() == []

    preset = RecordingPreset(
        id="preset-1",
        name="测试预设",
        resolution="1920x1080",
        segment_duration=600,
    )
    cam.add_preset(preset)
    assert len(cam.get_presets()) == 1
    assert cam.get_presets()[0].name == "测试预设"

    cam.default_preset_id = "preset-1"
    default = cam.get_default_preset()
    assert default is not None
    assert default.id == "preset-1"

    cam.remove_preset("preset-1")
    assert len(cam.get_presets()) == 0
    assert cam.get_default_preset() is None


def test_camera_update_preset():
    cam = Camera(device_mac="AA:BB:CC:DD:EE:FF", onvif_host="192.168.1.100")
    preset = RecordingPreset(
        id="p1", name="原始名称", resolution="1920x1080", segment_duration=600
    )
    cam.add_preset(preset)

    cam.update_preset("p1", {"name": "新名称", "segment_duration": 1200})
    updated = cam.get_presets()[0]
    assert updated.name == "新名称"
    assert updated.segment_duration == 1200
    assert updated.resolution == "1920x1080"  # 未改动的字段保持不变


# ── Schedule preset_id / overrides tests ──────────────────────────────────

from app.domain.models.schedule import Schedule


def test_schedule_preset_and_overrides_fields():
    """验证 Schedule preset_id 和 overrides 字段的存取"""
    schedule = Schedule(
        camera_mac="AA:BB:CC:DD:EE:FF",
        cron_expr="0 * * * *",
        segment_duration=1800,
    )
    assert schedule.preset_id is None
    assert schedule.overrides is None

    schedule.preset_id = "preset-abc"
    schedule.set_overrides({"segment_duration": 900, "bitrate": 4096})

    assert schedule.preset_id == "preset-abc"
    assert schedule.get_overrides() == {"segment_duration": 900, "bitrate": 4096}


def test_schedule_get_effective_segment_duration():
    """验证 get_effective_segment_duration 优先使用 overrides 中的值"""
    schedule = Schedule(
        camera_mac="AA:BB:CC:DD:EE:FF",
        cron_expr="0 * * * *",
        segment_duration=1800,
    )

    # 无 overrides 时返回 self.segment_duration
    assert schedule.get_effective_segment_duration() == 1800

    # 有 overrides 时优先用 overrides 中的值
    schedule.set_overrides({"segment_duration": 600})
    assert schedule.get_effective_segment_duration() == 600

    # overrides 中无 segment_duration 时仍回退到 self
    schedule.set_overrides({"bitrate": 2048})
    assert schedule.get_effective_segment_duration() == 1800


def test_schedule_overrides_invalid_json():
    """验证 get_overrides 对无效 JSON 返回 None"""
    schedule = Schedule(
        camera_mac="AA:BB:CC:DD:EE:FF",
        cron_expr="0 * * * *",
        segment_duration=1800,
    )
    schedule.overrides = "not valid json"
    assert schedule.get_overrides() is None


def test_schedule_set_overrides_to_none():
    """验证 set_overrides(None) 清除 overrides"""
    schedule = Schedule(
        camera_mac="AA:BB:CC:DD:EE:FF",
        cron_expr="0 * * * *",
        segment_duration=1800,
    )
    schedule.set_overrides({"segment_duration": 600})
    assert schedule.overrides is not None
    schedule.set_overrides(None)
    assert schedule.overrides is None
    assert schedule.get_overrides() is None


# ── API tests ────────────────────────────────────────────────────

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache before and after each test to ensure monkeypatch env vars take effect."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_env(monkeypatch):
    """Set required env vars for tests and clear cache."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret_key_that_is_at_least_32_characters_long")
    monkeypatch.setenv("ADMIN_PASSWORD", "testpassword_for_ci_only")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")
    get_settings.cache_clear()


import uuid

# Generate unique MAC per test run to avoid conflicts across test runs
_TEST_MAC = f"11:22:33:{uuid.uuid4().hex[:2]}:{uuid.uuid4().hex[:2]}:{uuid.uuid4().hex[:2]}"


@pytest.mark.asyncio
async def test_crud_presets(test_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Login first to get auth token
        resp = await ac.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "testpassword_for_ci_only"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 首先创建摄像机
        resp = await ac.post("/api/v1/cameras", json={
            "device_mac": _TEST_MAC,
            "onvif_host": "192.168.1.50",
        }, headers=headers)
        assert resp.status_code == 201

        mac = _TEST_MAC

        # 创建预设
        resp = await ac.post(f"/api/v1/cameras/{mac}/presets", json={
            "name": "测试预设",
            "resolution": "1920x1080",
            "segment_duration": 600,
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "测试预设"
        preset_id = data["id"]

        # 获取预设列表
        resp = await ac.get(f"/api/v1/cameras/{mac}/presets", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # 更新预设
        resp = await ac.put(f"/api/v1/cameras/{mac}/presets/{preset_id}", json={
            "name": "已更新",
            "segment_duration": 1200,
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "已更新"
        assert resp.json()["segment_duration"] == 1200

        # 设置默认
        resp = await ac.post(f"/api/v1/cameras/{mac}/presets/default", json={"preset_id": preset_id}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["default_preset_id"] == preset_id

        # 删除预设
        resp = await ac.delete(f"/api/v1/cameras/{mac}/presets/{preset_id}", headers=headers)
        assert resp.status_code == 204

        resp = await ac.get(f"/api/v1/cameras/{mac}/presets", headers=headers)
        assert len(resp.json()) == 0
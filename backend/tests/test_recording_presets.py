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
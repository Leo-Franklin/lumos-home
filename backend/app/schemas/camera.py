import re
from datetime import datetime

from pydantic import BaseModel, field_validator

_MAC_RE = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')


class RecordingPresetCreate(BaseModel):
    name: str
    resolution: str = '1920x1080'
    segment_duration: int = 600
    bitrate: int | None = None
    fps: int | None = None

    @field_validator('segment_duration')
    @classmethod
    def segment_duration_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('segment_duration must be positive')
        return v


class RecordingPresetUpdate(BaseModel):
    name: str | None = None
    resolution: str | None = None
    segment_duration: int | None = None
    bitrate: int | None = None
    fps: int | None = None

    @field_validator('segment_duration')
    @classmethod
    def segment_duration_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError('segment_duration must be positive')
        return v


class RecordingPresetSchema(BaseModel):
    id: str
    name: str
    resolution: str = '1920x1080'
    segment_duration: int = 600
    bitrate: int | None = None
    fps: int | None = None


class StartRecordingRequest(BaseModel):
    preset_id: str | None = None
    overrides: dict | None = None


class LiveStreamOut(BaseModel):
    mode: str  # mse | mjpeg_fallback
    stream_name: str
    status: str  # ready | unavailable
    mse_ws_url: str | None = None
    webrtc_url: str | None = None
    mjpeg_url: str | None = None


class CameraCreate(BaseModel):
    device_mac: str
    onvif_host: str
    onvif_port: int = 2020

    @field_validator('device_mac')
    @classmethod
    def device_mac_valid(cls, v: str) -> str:
        if not _MAC_RE.match(v):
            raise ValueError('device_mac 不是有效的 MAC 地址格式 (例如 AA:BB:CC:DD:EE:FF)')
        return v.upper()

    @field_validator('onvif_host')
    @classmethod
    def onvif_host_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('onvif_host 不能为空')
        return v.strip()

    onvif_user: str | None = None
    onvif_password: str | None = None
    rtsp_port: int = 554
    rtsp_url: str | None = None
    stream_profile: str = 'mainStream'


class CameraUpdate(BaseModel):
    onvif_host: str | None = None
    onvif_port: int | None = None
    onvif_user: str | None = None
    onvif_password: str | None = None
    rtsp_port: int | None = None
    rtsp_url: str | None = None
    stream_profile: str | None = None
    auto_cast_dlna: str | None = None


class CameraOut(BaseModel):
    id: int
    device_mac: str
    onvif_host: str
    onvif_port: int
    onvif_user: str | None
    rtsp_port: int
    rtsp_url: str | None
    stream_profile: str
    is_recording: bool
    is_online: bool
    last_probe_at: datetime | None
    auto_cast_dlna: str | None
    created_at: datetime
    recording_presets: list[RecordingPresetSchema] = []
    default_preset_id: str | None = None

    model_config = {'from_attributes': True}

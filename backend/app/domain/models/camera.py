from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.database import Base


@dataclass
class RecordingPreset:
    id: str
    name: str
    resolution: str = '1920x1080'  # 宽x高
    segment_duration: int = 600  # 秒
    bitrate: int | None = None  # kbps，None=自动
    fps: int | None = None  # None=25

    def to_dict(self, is_default: bool = False) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'resolution': self.resolution,
            'segment_duration': self.segment_duration,
            'bitrate': self.bitrate,
            'fps': self.fps,
            'is_default': is_default,
        }

    @staticmethod
    def from_dict(data: dict) -> 'RecordingPreset':
        return RecordingPreset(
            id=data['id'],
            name=data['name'],
            resolution=data.get('resolution', '1920x1080'),
            segment_duration=data.get('segment_duration', 600),
            bitrate=data.get('bitrate'),
            fps=data.get('fps'),
        )


class Camera(Base):
    __tablename__ = 'cameras'

    id: Mapped[int] = mapped_column(primary_key=True)
    device_mac: Mapped[str] = mapped_column(
        String(17), ForeignKey('devices.mac'), unique=True, nullable=False
    )
    onvif_host: Mapped[str] = mapped_column(String(64), nullable=False)
    onvif_port: Mapped[int] = mapped_column(Integer, default=2020)
    onvif_user: Mapped[str | None] = mapped_column(String(64))
    onvif_password: Mapped[str | None] = mapped_column(String(256))  # AES-encrypted
    rtsp_port: Mapped[int] = mapped_column(Integer, default=554)
    rtsp_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    stream_profile: Mapped[str] = mapped_column(String(32), default='mainStream')
    is_recording: Mapped[bool] = mapped_column(Boolean, default=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_cast_dlna: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    recording_presets: Mapped[list] = mapped_column(JSON, default=list)  # JSON 存储
    default_preset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Frigate integration: bridge maps a Frigate camera_name to our MAC
    frigate_name: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    @validates('device_mac')
    def normalize_device_mac(self, key, device_mac: str) -> str:
        return device_mac.upper()

    def get_presets(self) -> list[RecordingPreset]:
        import json

        if not self.recording_presets:
            return []
        if isinstance(self.recording_presets, list):
            return [
                RecordingPreset.from_dict(p) if isinstance(p, dict) else p
                for p in self.recording_presets
            ]
        try:
            parsed = json.loads(str(self.recording_presets))
            return [RecordingPreset.from_dict(p) for p in parsed]
        except (ValueError, TypeError) as e:
            # Malformed legacy JSON in DB → treat as no presets rather than crashing callers
            logger.warning(f'[Camera {self.device_mac}] 解析 recording_presets 失败: {e}')
            return []

    def set_presets(self, presets: list[RecordingPreset]):
        self.recording_presets = [p.to_dict() for p in presets]

    def add_preset(self, preset: RecordingPreset):
        presets = self.get_presets()
        presets.append(preset)
        self.set_presets(presets)

    def remove_preset(self, preset_id: str):
        presets = self.get_presets()
        self.set_presets([p for p in presets if p.id != preset_id])
        if self.default_preset_id == preset_id:
            self.default_preset_id = None

    def update_preset(self, preset_id: str, data: dict):
        presets = self.get_presets()
        for i, p in enumerate(presets):
            if p.id == preset_id:
                for key in [
                    'name',
                    'resolution',
                    'segment_duration',
                    'bitrate',
                    'fps',
                ]:
                    if key in data:
                        setattr(p, key, data[key])
                presets[i] = p
                break
        self.set_presets(presets)

    def get_default_preset(self) -> RecordingPreset | None:
        if not self.default_preset_id:
            return None
        presets = self.get_presets()
        return next((p for p in presets if p.id == self.default_preset_id), None)

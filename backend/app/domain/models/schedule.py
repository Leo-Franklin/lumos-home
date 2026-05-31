from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Schedule(Base):
    __tablename__ = 'schedules'

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_mac: Mapped[str] = mapped_column(
        String(17), ForeignKey('cameras.device_mac'), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(128))
    cron_expr: Mapped[str] = mapped_column(String(64), nullable=False)
    segment_duration: Mapped[int] = mapped_column(Integer, default=1800)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    preset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    overrides: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON stored
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    def get_overrides(self) -> dict | None:
        import json

        if not self.overrides:
            return None
        try:
            return json.loads(self.overrides)
        except Exception:
            return None

    def set_overrides(self, data: dict | None):
        import json

        self.overrides = json.dumps(data) if data else None

    def get_effective_segment_duration(self) -> int:
        """Prefer overrides.segment_duration > self.segment_duration.

        Note: preset_id resolution requires the Camera object and must be
        done at the call site (e.g. _make_recording_callback) where the
        Camera is available.
        """
        overrides = self.get_overrides()
        if overrides and 'segment_duration' in overrides:
            return overrides['segment_duration']
        return self.segment_duration

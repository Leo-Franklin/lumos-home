"""CameraEvent — Frigate-inspired event layer on top of recordings.

A CameraEvent is a logical occurrence (manual recording, motion, external
detection, etc.) that may have multiple recording segments linked via
`recordings.event_id`. The plan calls for a single, unified event model
that the API, retention policy, timeline UI, and Frigate bridge can all
share.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EventType:
    MANUAL_RECORDING = 'manual_recording'
    SCHEDULED_RECORDING = 'scheduled_recording'
    PRESENCE_TRIGGERED = 'presence_triggered'
    MOTION = 'motion'
    EXTERNAL_FRIGATE = 'external_frigate'
    SYSTEM = 'system'


class EventSource:
    LUMOS = 'lumos'
    FRIGATE = 'frigate'
    USER = 'user'
    SCHEDULER = 'scheduler'
    PRESENCE = 'presence'


class EventSeverity:
    INFO = 'info'
    NOTICE = 'notice'
    WARNING = 'warning'
    ALERT = 'alert'


class EventStatus:
    ACTIVE = 'active'
    COMPLETED = 'completed'
    FAILED = 'failed'
    LOCKED = 'locked'  # user-pinned; retention policy must not delete


class CameraEvent(Base):
    __tablename__ = 'camera_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_mac: Mapped[str] = mapped_column(
        String(17), ForeignKey('cameras.device_mac'), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default=EventSource.LUMOS)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    severity: Mapped[str] = mapped_column(String(16), default=EventSeverity.INFO)
    status: Mapped[str] = mapped_column(String(16), default=EventStatus.ACTIVE, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    thumbnail_path: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

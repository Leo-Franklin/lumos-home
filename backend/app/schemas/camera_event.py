from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.camera_event import EventSeverity, EventSource, EventStatus, EventType


class CameraEventOut(BaseModel):
    id: int
    camera_mac: str
    event_type: str
    source: str
    started_at: datetime
    ended_at: datetime | None
    severity: str
    status: str
    summary: str | None
    thumbnail_path: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CameraEventPatch(BaseModel):
    status: str | None = Field(
        default=None,
        description=f'One of {", ".join([EventStatus.ACTIVE, EventStatus.COMPLETED, EventStatus.FAILED, EventStatus.LOCKED])}',
    )
    summary: str | None = None
    severity: str | None = Field(
        default=None,
        description=f'One of {", ".join([EventSeverity.INFO, EventSeverity.NOTICE, EventSeverity.WARNING, EventSeverity.ALERT])}',
    )
    thumbnail_path: str | None = None
    metadata_json: dict[str, Any] | None = None


# Re-export enum constants for callers that import from schemas
__all__ = [
    'CameraEventOut',
    'CameraEventPatch',
    'EventSeverity',
    'EventSource',
    'EventStatus',
    'EventType',
]

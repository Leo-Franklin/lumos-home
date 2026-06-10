from datetime import datetime

from pydantic import BaseModel, field_validator

from app.domain.services.webhook_validation import validate_webhook_url
from app.schemas.device import DeviceOut


def _check_webhook(v: str | None) -> str | None:
    if v:
        validate_webhook_url(v)
    return v


class MemberCreate(BaseModel):
    name: str
    avatar_url: str | None = None
    webhook_url: str | None = None
    auto_record_cameras: list[str] = []

    @field_validator('webhook_url')
    @classmethod
    def validate_webhook(cls, v: str | None) -> str | None:
        return _check_webhook(v)


class MemberUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    webhook_url: str | None = None
    auto_record_cameras: list[str] | None = None

    @field_validator('webhook_url')
    @classmethod
    def validate_webhook(cls, v: str | None) -> str | None:
        return _check_webhook(v)


class MemberOut(BaseModel):
    id: int
    name: str
    avatar_url: str | None
    webhook_url: str | None
    is_home: bool
    last_arrived_at: datetime | None
    last_left_at: datetime | None
    auto_record_cameras: list[str]
    created_at: datetime
    device_count: int = 0
    devices_online: int = 0


class MemberDeviceCreate(BaseModel):
    mac: str
    label: str | None = None


class MemberDeviceOut(BaseModel):
    id: int
    member_id: int
    mac: str
    label: str | None
    device_info: DeviceOut | None = None

    model_config = {'from_attributes': True}


class PresenceLogOut(BaseModel):
    id: int
    member_id: int
    event: str
    triggered_by_mac: str | None
    occurred_at: datetime

    model_config = {'from_attributes': True}


class DailyStats(BaseModel):
    date: str  # "YYYY-MM-DD"
    minutes: int


class MemberStatsOut(BaseModel):
    total_minutes: int
    daily: list[DailyStats]

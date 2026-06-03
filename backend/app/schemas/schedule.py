from datetime import datetime

from loguru import logger
from pydantic import BaseModel, field_validator


class ScheduleCreate(BaseModel):
    camera_mac: str
    name: str | None = None
    cron_expr: str
    segment_duration: int = 1800
    enabled: bool = True
    preset_id: str | None = None
    overrides: dict | None = None


class ScheduleUpdate(BaseModel):
    name: str | None = None
    cron_expr: str | None = None
    segment_duration: int | None = None
    enabled: bool | None = None
    preset_id: str | None = None
    overrides: dict | None = None


class ScheduleOut(BaseModel):
    id: int
    camera_mac: str
    name: str | None
    cron_expr: str
    segment_duration: int
    enabled: bool
    created_at: datetime
    updated_at: datetime | None
    preset_id: str | None = None
    overrides: dict | None = None

    model_config = {'from_attributes': True}

    @field_validator('overrides', mode='before')
    @classmethod
    def deserialize_overrides(cls, v):
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except (ValueError, TypeError) as e:
                # Malformed legacy overrides → expose as None to caller (no crash)
                logger.warning(f'[ScheduleOut] 解析 overrides 失败: {e}')
                return None
        return v

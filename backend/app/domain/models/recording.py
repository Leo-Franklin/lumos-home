from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Recording(Base):
    __tablename__ = 'recordings'

    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    camera_mac: Mapped[str] = mapped_column(
        String(17), ForeignKey('cameras.device_mac'), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default='recording')
    error_msg: Mapped[str | None] = mapped_column(Text)
    segment_index: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('camera_events.id'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

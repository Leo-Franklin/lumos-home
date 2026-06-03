"""FrigateBridgeService — consume Frigate MQTT events and map them to
CameraEvent rows in our unified event model.

Frigate's MQTT topic layout is `frigate/<camera_name>/<event_type>`. Each
message is a JSON object with `type` in {"new", "update", "end"} and a
payload under `after` (or `before` for transitions).

The plan's P1-2 calls for mapping these Frigate labels:
    person, car, package, animal, motion, custom label
to `CameraEvent` rows with `event_type=EXTERNAL_FRIGATE`,
`source=FRIGATE`, and the Frigate label/score preserved in metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from loguru import logger

SUPPORTED_LABELS = {'person', 'car', 'package', 'animal', 'motion'}


class MqttClientLike(Protocol):
    """The subset of paho-mqtt's Client we use."""

    def subscribe(self, topic: Any) -> Any: ...
    def unsubscribe(self, topic: Any) -> Any: ...
    def message_callback_add(self, sub: str, callback: Any) -> None: ...
    def loop_start(self) -> Any: ...
    def loop_stop(self) -> Any: ...
    def connect(self, host: str, port: int, keepalive: int = 60) -> Any: ...
    def disconnect(self) -> Any: ...


@dataclass
class FrigateBridgeConfig:
    enabled: bool = False
    host: str = 'localhost'
    port: int = 1883
    username: str = ''
    password: str = ''
    topic_prefix: str = 'frigate'
    # Custom labels are mapped to event_type=EXTERNAL_FRIGATE but kept in
    # the metadata; the user can configure which labels to ingest here.
    extra_labels: list[str] = field(default_factory=list)


class FrigateBridgeService:
    def __init__(
        self,
        mqtt_client: MqttClientLike,
        session_factory: Any,
        config: FrigateBridgeConfig | None = None,
    ):
        self._client = mqtt_client
        self._session_factory = session_factory
        self._config = config or FrigateBridgeConfig()
        self._running = False

    @property
    def config(self) -> FrigateBridgeConfig:
        return self._config

    def set_client(self, client: MqttClientLike) -> None:
        self._client = client

    def subscribe_topics(self) -> list[str]:
        """Return the topic patterns to subscribe to.

        Frigate publishes per-camera events under <prefix>/<camera>/<label>.
        Using a wildcard `+/+` after the prefix lets the bridge ingest
        events from all cameras without per-camera config.
        """
        prefix = self._config.topic_prefix.rstrip('/')
        return [f'{prefix}/+ /+'.replace(' ', '')]

    # --- lifecycle --------------------------------------------------------

    def start(self) -> None:
        if not self._config.enabled:
            logger.info('FrigateBridge disabled by config — not subscribing')
            return
        topics = self.subscribe_topics()
        for topic in topics:
            self._client.subscribe(topic)
        self._running = True
        logger.info(f'FrigateBridge started, subscribed to: {topics}')

    def stop(self) -> None:
        if not self._running:
            return
        for topic in self.subscribe_topics():
            self._client.unsubscribe(topic)
        self._running = False
        logger.info('FrigateBridge stopped')

    # --- message handler --------------------------------------------------

    @staticmethod
    def _supported_labels(config: FrigateBridgeConfig) -> set[str]:
        return SUPPORTED_LABELS | set(config.extra_labels)

    async def handle_message(self, topic: str, payload: dict[str, Any] | str) -> Any | None:
        """Process one Frigate MQTT message. Returns the affected CameraEvent
        (newly created or updated), or None if the message is ignored.

        `payload` may be a dict (already decoded) or a JSON string.
        """
        data: dict[str, Any]
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f'FrigateBridge dropping non-JSON payload on {topic}')
                return None
        else:
            data = payload

        # Frigate's "reviews" and stats topics also use the prefix; ignore
        # anything that doesn't look like an event message.
        if 'type' not in data:
            return None
        msg_type = data.get('type')
        if msg_type not in {'new', 'update', 'end'}:
            return None

        after = data.get('after') or {}
        label = after.get('label', '').lower()
        if label not in self._supported_labels(self._config):
            return None

        camera_name = after.get('camera') or self._camera_from_topic(topic)
        if not camera_name:
            return None
        # Frigate uses snake_case camera names; our DB stores uppercase MACs.
        # When no MAC match is found we still keep the original name so
        # operators can correlate.
        camera_mac = await self._resolve_camera_mac(camera_name)

        if msg_type == 'new':
            return await self._create_event(after, label, camera_mac)
        # 'update' or 'end' → mark the existing event completed
        return await self._complete_event(after, label, camera_mac)

    # --- internals --------------------------------------------------------

    @staticmethod
    def _camera_from_topic(topic: str) -> str | None:
        parts = topic.split('/')
        if len(parts) < 2:
            return None
        return parts[-2]  # second-to-last segment

    async def _resolve_camera_mac(self, camera_name: str) -> str:
        """Look up our Camera row by its Frigate name (or return name)."""
        try:
            from sqlalchemy import select

            from app.domain.models.camera import Camera

            async with self._session_factory() as db:
                result = await db.execute(select(Camera).where(Camera.frigate_name == camera_name))
                cam = result.scalar_one_or_none()
                if cam is not None:
                    return cam.device_mac
        except Exception as e:  # noqa: BLE001 - DB lookup must never break the bridge
            logger.debug(f'FrigateBridge _resolve_camera_mac failed: {e}')
        return camera_name.upper()

    async def _create_event(self, after: dict, label: str, camera_mac: str) -> Any:
        from app.domain.models.camera_event import (
            CameraEvent,
            EventSeverity,
            EventSource,
            EventStatus,
            EventType,
        )

        start_ts = self._ts(after.get('start_time'))
        score = after.get('top_score') or after.get('score')
        sub_label = after.get('sub_label')
        summary_parts = [label]
        if sub_label:
            summary_parts.append(f'({sub_label})')
        if score is not None:
            summary_parts.append(f'置信度 {float(score):.0%}')

        event = CameraEvent(
            camera_mac=camera_mac,
            event_type=EventType.EXTERNAL_FRIGATE,
            source=EventSource.FRIGATE,
            status=EventStatus.ACTIVE,
            started_at=start_ts,
            severity=EventSeverity.NOTICE
            if label in ('person', 'car', 'package')
            else EventSeverity.INFO,
            summary=' '.join(summary_parts),
            metadata_json={
                'label': label,
                'score': score,
                'sub_label': sub_label,
                'frigate_event_id': after.get('id'),
            },
        )
        async with self._session_factory() as db:
            db.add(event)
            await db.commit()
            await db.refresh(event)
        logger.info(f'FrigateBridge: 收到外部 {label} 事件 camera={camera_mac} score={score}')
        return event

    async def _complete_event(self, after: dict, label: str, camera_mac: str) -> Any:
        from sqlalchemy import select

        from app.domain.models.camera_event import (
            CameraEvent,
            EventStatus,
        )

        end_ts = self._ts(after.get('end_time') or after.get('start_time'))
        frigate_id = after.get('id')
        async with self._session_factory() as db:
            stmt = (
                select(CameraEvent).where(
                    CameraEvent.metadata_json['frigate_event_id'].as_string() == frigate_id
                )
                if frigate_id
                else select(CameraEvent).where(CameraEvent.id == -1)
            )
            result = await db.execute(stmt)
            event = result.scalar_one_or_none()
            if event is None:
                # Fallback: no event tracked, just create a completed one
                event = await self._create_event(after, label, camera_mac)
            if event.status != EventStatus.COMPLETED:
                event.status = EventStatus.COMPLETED
                event.ended_at = end_ts
            await db.commit()
            await db.refresh(event)
        return event

    @staticmethod
    def _ts(value: Any) -> datetime:
        if value is None:
            return datetime.now(UTC).replace(tzinfo=None)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, UTC).replace(tzinfo=None)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                pass
        return datetime.now(UTC).replace(tzinfo=None)

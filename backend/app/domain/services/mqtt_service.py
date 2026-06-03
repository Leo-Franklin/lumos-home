"""MqttService — publish internal Lumos Home events to an MQTT broker.

This is the bridge to the Home Assistant / Frigate ecosystem. It is a
thin publisher: it owns the client lifecycle and a set of typed publish
methods, but does not subscribe (subscribing is the Frigate bridge's job
in P1-2).

Design points:
- The MQTT client is injected so tests can use a MagicMock. In production
  we construct a paho-mqtt client in `start()`.
- `publish_*` methods never raise — a broken broker must not bring down
  the rest of the app.
- All topics are namespaced under the configured `topic_prefix`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from loguru import logger


class MqttClient(Protocol):
    """Minimal interface that MqttService depends on.

    paho-mqtt's `paho.mqtt.client.Client` satisfies this, but tests can
    substitute any object that exposes `publish`, `connect`, `disconnect`.
    """

    def publish(
        self, topic: str, payload: str | None = None, qos: int = 0, retain: bool = False
    ) -> Any: ...

    def connect(self, host: str, port: int, keepalive: int = 60) -> Any: ...

    def disconnect(self) -> Any: ...


@dataclass
class MqttConfig:
    host: str = 'localhost'
    port: int = 1883
    username: str = ''
    password: str = ''
    topic_prefix: str = 'lumos'
    tls: bool = False


class MqttService:
    def __init__(self, client: MqttClient | None = None, config: MqttConfig | None = None):
        self._client = client
        self._config = config or MqttConfig()
        self._enabled = True

    # --- lifecycle --------------------------------------------------------

    @property
    def config(self) -> MqttConfig:
        return self._config

    def set_client(self, client: MqttClient) -> None:
        self._client = client

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def connect(self) -> None:
        if self._client is not None:
            self._client.connect(self._config.host, self._config.port, keepalive=60)

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.disconnect()

    # --- publishers -------------------------------------------------------

    def _topic(self, *parts: str) -> str:
        prefix = self._config.topic_prefix.rstrip('/')
        return '/'.join([prefix, *parts])

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._enabled or self._client is None:
            return
        body = {
            'timestamp': datetime.now(UTC).isoformat(),
            **payload,
        }
        try:
            self._client.publish(topic, json.dumps(body, ensure_ascii=False), qos=0, retain=False)
        except Exception as e:  # noqa: BLE001 - broker failures must not break the app
            # Swallow; tests can verify with a side_effect=Exception mock.
            # Logged at debug because a flaky broker is normal in dev and
            # should not pollute the production log stream.
            logger.debug(f'MqttService publish failed for {topic}: {e}')

    def publish_device_online(self, mac: str, device_type: str, name: str | None = None) -> None:
        self._publish(
            self._topic('device', device_type, 'online'),
            {'mac': mac, 'device_type': device_type, 'name': name},
        )

    def publish_device_offline(self, mac: str, device_type: str) -> None:
        self._publish(
            self._topic('device', device_type, 'offline'),
            {'mac': mac, 'device_type': device_type},
        )

    def publish_camera_status(self, camera_mac: str, is_online: bool) -> None:
        self._publish(
            self._topic('camera', 'status'),
            {'camera_mac': camera_mac, 'is_online': is_online},
        )

    def publish_recording_started(self, camera_mac: str, event_id: int) -> None:
        self._publish(
            self._topic('recording', 'started'),
            {'camera_mac': camera_mac, 'event_id': event_id},
        )

    def publish_recording_completed(self, camera_mac: str, event_id: int, duration: int) -> None:
        self._publish(
            self._topic('recording', 'completed'),
            {'camera_mac': camera_mac, 'event_id': event_id, 'duration': duration},
        )

    def publish_recording_failed(self, camera_mac: str, event_id: int, error: str) -> None:
        self._publish(
            self._topic('recording', 'failed'),
            {'camera_mac': camera_mac, 'event_id': event_id, 'error': error},
        )

    def publish_member_arrived(self, member_id: int, name: str) -> None:
        self._publish(
            self._topic('member', 'arrived'),
            {'member_id': member_id, 'name': name},
        )

    def publish_member_left(self, member_id: int, name: str) -> None:
        self._publish(
            self._topic('member', 'left'),
            {'member_id': member_id, 'name': name},
        )

    def publish_unknown_device(self, mac: str, ip: str) -> None:
        self._publish(
            self._topic('device', 'unknown'),
            {'mac': mac, 'ip': ip},
        )

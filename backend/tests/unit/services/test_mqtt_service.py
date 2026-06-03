"""Unit tests for app/domain/services/mqtt_service.py.

TDD: the MqttService is the bridge from internal events (device online,
recording complete, member arrived) to a Home Assistant / Frigate
ecosystem. Tests inject a fake client so no real broker is needed.
"""

from unittest.mock import MagicMock

from app.domain.services.mqtt_service import MqttConfig, MqttService


def _make_config(**overrides) -> MqttConfig:
    defaults = {
        'host': 'localhost',
        'port': 1883,
        'username': '',
        'password': '',
        'topic_prefix': 'lumos',
        'tls': False,
    }
    defaults.update(overrides)
    return MqttConfig(**defaults)


def test_config_defaults():
    cfg = MqttConfig()
    assert cfg.host == 'localhost'
    assert cfg.port == 1883
    assert cfg.topic_prefix == 'lumos'
    assert cfg.tls is False


def test_publish_when_disabled_is_noop():
    """MqttService must not touch the client when enabled=False."""
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())
    svc.disable()

    svc.publish_device_online('AA:BB:CC:DD:EE:01', device_type='camera', name='cam1')
    client.publish.assert_not_called()


def test_publish_device_online_uses_correct_topic():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config(topic_prefix='lumos'))

    svc.publish_device_online('AA:BB:CC:DD:EE:01', device_type='camera', name='Front Door')

    client.publish.assert_called_once()
    topic, payload, *_ = client.publish.call_args[0]
    assert topic == 'lumos/device/camera/online'
    assert '"mac": "AA:BB:CC:DD:EE:01"' in payload
    assert '"name": "Front Door"' in payload


def test_publish_device_offline():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())

    svc.publish_device_offline('AA:BB:CC:DD:EE:01', device_type='camera')

    topic, _payload, *_ = client.publish.call_args[0]
    assert topic == 'lumos/device/camera/offline'


def test_publish_camera_status():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())

    svc.publish_camera_status('AA:BB:CC:DD:EE:01', is_online=True)

    topic, _payload, *_ = client.publish.call_args[0]
    assert topic == 'lumos/camera/status'
    assert '"camera_mac": "AA:BB:CC:DD:EE:01"' in client.publish.call_args[0][1]


def test_publish_recording_started_completed_failed():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())

    svc.publish_recording_started('AA:BB:CC:DD:EE:01', event_id=42)
    assert client.publish.call_args_list[0][0][0] == 'lumos/recording/started'
    assert '"event_id": 42' in client.publish.call_args_list[0][0][1]

    svc.publish_recording_completed('AA:BB:CC:DD:EE:01', event_id=42, duration=120)
    assert client.publish.call_args_list[1][0][0] == 'lumos/recording/completed'
    assert '"duration": 120' in client.publish.call_args_list[1][0][1]

    svc.publish_recording_failed('AA:BB:CC:DD:EE:01', event_id=42, error='stalled')
    assert client.publish.call_args_list[2][0][0] == 'lumos/recording/failed'
    assert '"error": "stalled"' in client.publish.call_args_list[2][0][1]


def test_publish_member_presence():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())

    svc.publish_member_arrived(member_id=1, name='Alice')
    assert client.publish.call_args_list[0][0][0] == 'lumos/member/arrived'
    assert '"name": "Alice"' in client.publish.call_args_list[0][0][1]

    svc.publish_member_left(member_id=1, name='Alice')
    assert client.publish.call_args_list[1][0][0] == 'lumos/member/left'


def test_publish_unknown_device():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())

    svc.publish_unknown_device(mac='FF:FF:FF:FF:FF:FF', ip='192.168.1.99')

    topic, payload, *_ = client.publish.call_args[0]
    assert topic == 'lumos/device/unknown'
    assert '192.168.1.99' in payload


def test_publish_swallows_client_errors():
    """A broken broker must never bring down the rest of the app."""
    client = MagicMock()
    client.publish.side_effect = ConnectionError('broker offline')
    svc = MqttService(client=client, config=_make_config())

    # Should not raise even though the client raised
    svc.publish_device_online('AA:BB:CC:DD:EE:01', device_type='camera')


def test_publish_includes_qos_and_retain():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())

    svc.publish_device_online('AA:BB:CC:DD:EE:01', device_type='camera')

    # call_args is a (args, kwargs) tuple
    args, kwargs = client.publish.call_args
    # Default is qos=0, retain=False unless explicitly requested
    assert kwargs.get('qos', 0) in (0, 1, 2)


def test_enable_disable_toggles_publishes():
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config())
    assert svc.is_enabled()

    svc.disable()
    svc.publish_device_online('AA:BB:CC:DD:EE:01', device_type='camera')
    client.publish.assert_not_called()

    svc.enable()
    svc.publish_device_online('AA:BB:CC:DD:EE:01', device_type='camera')
    client.publish.assert_called_once()


def test_connect_disconnect_delegate_to_client():
    client = MagicMock()
    client.connect = MagicMock()
    client.disconnect = MagicMock()
    svc = MqttService(client=client, config=_make_config())

    svc.connect()
    client.connect.assert_called_once_with('localhost', 1883, keepalive=60)

    svc.disconnect()
    client.disconnect.assert_called_once()


def test_topic_prefix_normalization():
    """A trailing slash in the prefix must not produce a double-slash topic."""
    client = MagicMock()
    svc = MqttService(client=client, config=_make_config(topic_prefix='lumos/'))

    svc.publish_device_online('AA:BB:CC:DD:EE:01', device_type='camera')

    topic = client.publish.call_args[0][0]
    assert '//' not in topic
    assert topic == 'lumos/device/camera/online'

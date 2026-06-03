"""Unit tests for app/domain/services/frigate_bridge.py.

TDD: the FrigateBridgeService consumes MQTT messages published by Frigate
and maps them to CameraEvent rows. We test the message handler in
isolation — the actual subscribe/loop is delegated to the injected
MqttClient.
"""

from unittest.mock import AsyncMock, MagicMock


def _make_bridge():
    from app.domain.services.frigate_bridge import (
        FrigateBridgeConfig,
        FrigateBridgeService,
    )

    session_factory = MagicMock()
    # session_factory() returns an async context manager whose enter returns an
    # AsyncMock session so the bridge's `async with ... as db` works.
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    session_factory.return_value = cm

    client = MagicMock()
    cfg = FrigateBridgeConfig(
        enabled=True,
        topic_prefix='frigate',
    )
    svc = FrigateBridgeService(mqtt_client=client, session_factory=session_factory, config=cfg)
    return svc, client, session


def test_subscribe_topics_returns_configured_camera_topics():
    svc, client, _ = _make_bridge()
    # Default Frigate publishes per-camera events under <prefix>/<camera>/<label>
    topics = svc.subscribe_topics()
    assert 'frigate/+/+' in topics  # wildcard camera, wildcard event type


def test_handle_message_person_label_creates_external_frigate_event():
    svc, _client, session = _make_bridge()
    payload = {
        'before': {'id': '1700000000.0001'},
        'after': {
            'id': '1700000000.0001',
            'camera': 'front_door',
            'label': 'person',
            'start_time': 1700000000.0,
            'end_time': None,
            'score': 0.92,
            'top_score': 0.92,
            'sub_label': None,
        },
        'type': 'new',
    }

    import asyncio

    event = asyncio.get_event_loop().run_until_complete(
        svc.handle_message('frigate/front_door/person', payload)
    )

    assert event is not None
    assert event.event_type == 'external_frigate'
    assert event.source == 'frigate'
    assert event.camera_mac == 'FRONT_DOOR' or event.camera_mac == 'front_door'
    assert event.metadata_json['label'] == 'person'
    assert event.metadata_json['score'] == 0.92
    # Should have written to the DB
    session.add.assert_called()
    session.commit.assert_called()


def test_handle_message_car_label_includes_score_in_summary():
    svc, _client, _session = _make_bridge()
    payload = {
        'type': 'new',
        'after': {
            'id': '1700000000.0002',
            'camera': 'driveway',
            'label': 'car',
            'score': 0.85,
            'start_time': 1700000010.0,
        },
    }
    import asyncio

    event = asyncio.get_event_loop().run_until_complete(
        svc.handle_message('frigate/driveway/car', payload)
    )
    assert event is not None
    assert 'car' in (event.summary or '').lower()


def test_handle_message_animal_and_package_and_motion():
    svc, _client, _session = _make_bridge()
    import asyncio

    for label in ('animal', 'package', 'motion'):
        payload = {
            'type': 'new',
            'after': {
                'id': f'1700000100.{label}',
                'camera': 'side_yard',
                'label': label,
                'start_time': 1700000100.0,
            },
        }
        event = asyncio.get_event_loop().run_until_complete(
            svc.handle_message(f'frigate/side_yard/{label}', payload)
        )
        assert event is not None, f'label {label!r} was rejected'
        assert event.event_type == 'external_frigate'


def test_handle_message_update_type_creates_completed_event():
    """Frigate publishes 'update' messages when an event ends. The bridge
    marks the corresponding event COMPLETED instead of inserting a new one."""
    svc, _client, session = _make_bridge()
    # First publish: 'new' with id '1700000000.x' creates event
    new_payload = {
        'type': 'new',
        'after': {
            'id': '1700000000.x',
            'camera': 'front_door',
            'label': 'person',
            'start_time': 1700000000.0,
        },
    }
    # Then publish: 'update' with same id marks event completed
    update_payload = {
        'type': 'update',
        'before': {'id': '1700000000.x', 'end_time': None},
        'after': {
            'id': '1700000000.x',
            'camera': 'front_door',
            'label': 'person',
            'start_time': 1700000000.0,
            'end_time': 1700000060.0,
        },
    }

    import asyncio

    loop = asyncio.new_event_loop()
    try:
        first = loop.run_until_complete(
            svc.handle_message('frigate/front_door/person', new_payload)
        )
        assert first is not None
        assert first.status == 'active'

        # Mark the session to return the previously-created event on select
        session.execute.return_value.scalar_one_or_none.return_value = first

        second = loop.run_until_complete(
            svc.handle_message('frigate/front_door/person', update_payload)
        )
        assert second is not None
        assert second.status == 'completed'
        assert second.ended_at is not None
    finally:
        loop.close()


def test_handle_message_unknown_label_is_ignored():
    """Labels outside the supported set are dropped (no DB write)."""
    svc, _client, session = _make_bridge()
    payload = {
        'type': 'new',
        'after': {
            'id': '1700000999.unsupported',
            'camera': 'side_yard',
            'label': 'unknown_thing',
            'start_time': 1700000999.0,
        },
    }
    import asyncio

    event = asyncio.get_event_loop().run_until_complete(
        svc.handle_message('frigate/side_yard/unknown_thing', payload)
    )

    assert event is None
    session.add.assert_not_called()


def test_handle_message_end_type_marks_event_completed():
    """Frigate's 'end' type carries end_time — bridge marks the event completed."""
    svc, _client, session = _make_bridge()
    # Seed: a previous 'new' created an active event
    new_payload = {
        'type': 'new',
        'after': {
            'id': '1700000200.q',
            'camera': 'front_door',
            'label': 'person',
            'start_time': 1700000200.0,
        },
    }
    end_payload = {
        'type': 'end',
        'before': {'id': '1700000200.q'},
        'after': {
            'id': '1700000200.q',
            'camera': 'front_door',
            'label': 'person',
            'end_time': 1700000260.0,
        },
    }

    import asyncio

    loop = asyncio.new_event_loop()
    try:
        first = loop.run_until_complete(
            svc.handle_message('frigate/front_door/person', new_payload)
        )
        assert first is not None
        session.execute.return_value.scalar_one_or_none.return_value = first

        second = loop.run_until_complete(
            svc.handle_message('frigate/front_door/person', end_payload)
        )
        assert second is not None
        assert second.status == 'completed'
        assert second.ended_at is not None
    finally:
        loop.close()


def test_start_subscribes_to_configured_topics():
    svc, client, _ = _make_bridge()
    svc.start()
    # subscribe was called with the configured wildcard
    assert client.subscribe.called
    topics_arg = client.subscribe.call_args[0][0]
    assert 'frigate/+/+' in topics_arg


def test_start_when_disabled_does_not_subscribe():
    from app.domain.services.frigate_bridge import (
        FrigateBridgeConfig,
        FrigateBridgeService,
    )

    session_factory = MagicMock()
    client = MagicMock()
    cfg = FrigateBridgeConfig(enabled=False, topic_prefix='frigate')
    svc = FrigateBridgeService(mqtt_client=client, session_factory=session_factory, config=cfg)
    svc.start()
    client.subscribe.assert_not_called()


def test_stop_unsubscribes():
    svc, client, _ = _make_bridge()
    svc.start()
    svc.stop()
    client.unsubscribe.assert_called()

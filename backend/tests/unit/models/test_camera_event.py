"""Unit tests for app/domain/models/camera_event.py.

TDD: tests describe the schema constants and ORM surface that the rest of
the code (event services, API, recording integration) will depend on.
"""


def test_event_type_constants_match_plan():
    from app.domain.models.camera_event import EventType

    assert EventType.MANUAL_RECORDING == 'manual_recording'
    assert EventType.SCHEDULED_RECORDING == 'scheduled_recording'
    assert EventType.PRESENCE_TRIGGERED == 'presence_triggered'
    assert EventType.MOTION == 'motion'
    assert EventType.EXTERNAL_FRIGATE == 'external_frigate'
    assert EventType.SYSTEM == 'system'


def test_event_source_constants_match_plan():
    from app.domain.models.camera_event import EventSource

    assert EventSource.LUMOS == 'lumos'
    assert EventSource.FRIGATE == 'frigate'
    assert EventSource.USER == 'user'
    assert EventSource.SCHEDULER == 'scheduler'
    assert EventSource.PRESENCE == 'presence'


def test_event_severity_constants():
    from app.domain.models.camera_event import EventSeverity

    assert EventSeverity.INFO == 'info'
    assert EventSeverity.NOTICE == 'notice'
    assert EventSeverity.WARNING == 'warning'
    assert EventSeverity.ALERT == 'alert'


def test_event_status_constants():
    from app.domain.models.camera_event import EventStatus

    assert EventStatus.ACTIVE == 'active'
    assert EventStatus.COMPLETED == 'completed'
    assert EventStatus.FAILED == 'failed'
    assert EventStatus.LOCKED == 'locked'  # user-pinned, never auto-cleaned


def test_camera_event_model_has_required_fields():
    from app.domain.models.camera_event import CameraEvent

    # Sanity check the ORM class exposes every column the plan calls for
    expected = {
        'id',
        'camera_mac',
        'event_type',
        'source',
        'started_at',
        'ended_at',
        'severity',
        'status',
        'summary',
        'thumbnail_path',
        'metadata_json',
        'created_at',
    }
    actual = set(CameraEvent.__table__.columns.keys())
    missing = expected - actual
    assert not missing, f'CameraEvent is missing columns: {missing}'


def test_recording_has_event_id_fk():
    """recordings.event_id links a segment to its parent event."""
    from app.domain.models.recording import Recording

    assert 'event_id' in Recording.__table__.columns
    fk_targets = [
        fk.column.table.name for fk in Recording.__table__.columns['event_id'].foreign_keys
    ]
    assert 'camera_events' in fk_targets

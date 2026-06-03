"""Domain services - re-exported from app.services for backward compatibility."""

from app.domain.services.camera_health import CameraHealthChecker
from app.domain.services.dlna_service import DLNAController
from app.domain.services.frigate_bridge import (
    FrigateBridgeConfig,
    FrigateBridgeService,
)
from app.domain.services.mqtt_service import MqttClient, MqttConfig, MqttService
from app.domain.services.nas_syncer import NasSyncer

# New domain services
from app.domain.services.onvif_client import OnvifClient
from app.domain.services.presence_domain import PresenceDomainService
from app.domain.services.presence_service import PresenceService, presence_service
from app.domain.services.recorder import Recorder, RecordingTask
from app.domain.services.recording_domain import RecordingDomainService
from app.domain.services.scanner import Scanner
from app.domain.services.scheduler_service import SchedulerService, scheduler_service
from app.domain.services.stream_manager import (
    StreamInfo,
    StreamLauncher,
    StreamManager,
    StreamState,
)
from app.domain.services.ws_manager import WebSocketManager, ws_manager

__all__ = [
    'CameraHealthChecker',
    'DLNAController',
    'FrigateBridgeConfig',
    'FrigateBridgeService',
    'MqttClient',
    'MqttConfig',
    'MqttService',
    'NasSyncer',
    'OnvifClient',
    'PresenceDomainService',
    'PresenceService',
    'presence_service',
    'Recorder',
    'RecordingTask',
    'RecordingDomainService',
    'Scanner',
    'SchedulerService',
    'scheduler_service',
    'StreamInfo',
    'StreamLauncher',
    'StreamManager',
    'StreamState',
    'ws_manager',
    'WebSocketManager',
]

"""Backward compatibility shim — canonical CameraHealthChecker lives in domain.services."""

from app.domain.services.camera_health import CameraHealthChecker

__all__ = ['CameraHealthChecker']

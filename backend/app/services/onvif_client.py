"""Backward compatibility shim — canonical OnvifClient lives in domain.services."""

from app.domain.services.onvif_client import OnvifClient

__all__ = ['OnvifClient']

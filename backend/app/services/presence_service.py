"""Backward compatibility shim — canonical PresenceService lives in domain.services."""

from app.domain.services.presence_service import PresenceService, presence_service

__all__ = ['PresenceService', 'presence_service']

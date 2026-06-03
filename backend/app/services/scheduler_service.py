"""Backward compatibility shim — canonical SchedulerService lives in domain.services."""

from app.domain.services.scheduler_service import SchedulerService, scheduler_service

__all__ = ['SchedulerService', 'scheduler_service']

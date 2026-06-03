"""Verify app/services/ legacy modules are deduped against app/domain/services/.

Goal: `app/domain/services/` should be the single source of truth. Each
legacy module under `app/services/` that has a domain counterpart must
re-export the domain class/singleton so `is` comparison succeeds.

Modules excluded from `is` checks (with reason):

- ``app.services.nas_syncer``: the legacy version has a Windows file-lock
  retry helper (`_copy_with_retry`) that the domain version lacks. Shimming
  legacy to domain would regress production behavior.
- ``app.services.email``: no `app/domain/services/email.py` counterpart;
  the legacy module is the canonical source.
- ``app.services.ws_manager``: the canonical implementation lives in
  ``app.services.ws_manager`` and ``app.domain.services.ws_manager`` is the
  shim re-exporting it. The shared ``ws_manager`` singleton is asserted
  below (legacy → domain direction).
"""

from __future__ import annotations


def test_onvif_client_class_is_shared() -> None:
    from app.domain.services.onvif_client import OnvifClient as domain_cls
    from app.services.onvif_client import OnvifClient as legacy_cls

    assert legacy_cls is domain_cls


def test_scheduler_service_class_and_singleton_are_shared() -> None:
    from app.domain.services.scheduler_service import (
        SchedulerService as domain_cls,
    )
    from app.domain.services.scheduler_service import (
        scheduler_service as domain_singleton,
    )
    from app.services.scheduler_service import SchedulerService as legacy_cls
    from app.services.scheduler_service import (
        scheduler_service as legacy_singleton,
    )

    assert legacy_cls is domain_cls
    assert legacy_singleton is domain_singleton


def test_ws_manager_singleton_is_shared() -> None:
    """ws_manager: domain shims legacy (reverse direction); singleton still shared."""
    from app.domain.services.ws_manager import ws_manager as domain_ws
    from app.services.ws_manager import ws_manager as legacy_ws

    assert legacy_ws is domain_ws


def test_camera_health_checker_is_shared() -> None:
    """Once app/services/camera_health.py is a shim, the class identity matches."""
    from app.domain.services.camera_health import (
        CameraHealthChecker as domain_cls,
    )
    from app.services.camera_health import CameraHealthChecker as legacy_cls

    assert legacy_cls is domain_cls


def test_presence_service_class_is_shared() -> None:
    """Once app/services/presence_service.py is a shim, the class identity matches."""
    from app.domain.services.presence_service import (
        PresenceService as domain_cls,
    )
    from app.services.presence_service import PresenceService as legacy_cls

    assert legacy_cls is domain_cls

"""Direction contract: ``app/domain/services/`` must be the canonical home.

For modules that were flipped from ``app/services/`` → ``app/domain/services/``
the legacy shim under ``app/services/`` must re-export the domain symbol so
identity (``is``) comparison succeeds both ways. This locks the canonical
direction in place so a future refactor that accidentally re-introduces a
copy in the legacy module is caught immediately.
"""

from __future__ import annotations


def test_nas_syncer_canonical_is_domain() -> None:
    from app.domain.services.nas_syncer import NasSyncer as domain_cls
    from app.services.nas_syncer import NasSyncer as legacy_cls

    # Canonical direction: domain defines it, legacy shim re-exports.
    assert legacy_cls is domain_cls


def test_ws_manager_canonical_is_domain() -> None:
    from app.domain.services.ws_manager import ws_manager as domain_singleton
    from app.services.ws_manager import ws_manager as legacy_singleton

    # The canonical implementation now lives in app/domain/services/ws_manager.py;
    # app/services/ws_manager.py is a thin shim that re-exports the singleton.
    assert legacy_singleton is domain_singleton


def test_ws_manager_class_also_identity_shared() -> None:
    """The WebSocketManager class itself (used by callers that don't import
    the singleton) must also be the same object across the two locations."""
    from app.domain.services.ws_manager import WebSocketManager as domain_cls
    from app.services.ws_manager import WebSocketManager as legacy_cls

    assert legacy_cls is domain_cls

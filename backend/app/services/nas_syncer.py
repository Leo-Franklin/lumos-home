"""Backward compatibility shim — canonical NasSyncer lives in domain.services."""

from app.domain.services.nas_syncer import *  # noqa: F401,F403
from app.domain.services.nas_syncer import NasSyncer  # noqa: F401

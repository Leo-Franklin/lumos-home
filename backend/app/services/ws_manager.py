"""Backward compatibility shim — canonical ws_manager lives in domain.services."""

from app.domain.services.ws_manager import *  # noqa: F401,F403
from app.domain.services.ws_manager import WebSocketManager, ws_manager  # noqa: F401

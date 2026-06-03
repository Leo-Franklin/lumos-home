import asyncio
import json
from datetime import UTC, datetime

from fastapi import WebSocket
from loguru import logger


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info(f'WebSocket connected: {ws.client}, total={len(self._connections)}')

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._connections.discard(ws)
        logger.info(f'WebSocket disconnected: {ws.client}, total={len(self._connections)}')

    async def broadcast(self, event: str, data: dict):
        message = json.dumps(
            {
                'event': event,
                'timestamp': datetime.now(UTC).isoformat(),
                'data': data,
            },
            ensure_ascii=False,
        )
        async with self._lock:
            connections = self._connections.copy()

        stale: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception as e:  # noqa: BLE001 — starlette/websocket 任意错误都视为 stale 连接
                logger.warning(f'WebSocket send failed, marking as stale: {e}')
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.discard(ws)


ws_manager = WebSocketManager()

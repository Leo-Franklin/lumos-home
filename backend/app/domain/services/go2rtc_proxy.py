"""WebSocket proxy helper for go2rtc live streaming."""

from __future__ import annotations

import asyncio

import websockets
from fastapi import WebSocket
from loguru import logger


async def proxy_go2rtc_websocket(client_ws: WebSocket, upstream_url: str) -> None:
    await client_ws.accept()
    try:
        async with websockets.connect(upstream_url) as upstream:

            async def client_to_upstream() -> None:
                while True:
                    message = await client_ws.receive()
                    if message['type'] == 'websocket.disconnect':
                        break
                    if message.get('bytes') is not None:
                        await upstream.send(message['bytes'])
                    elif message.get('text') is not None:
                        await upstream.send(message['text'])

            async def upstream_to_client() -> None:
                async for payload in upstream:
                    if isinstance(payload, bytes):
                        await client_ws.send_bytes(payload)
                    else:
                        await client_ws.send_text(payload)

            client_task = asyncio.create_task(client_to_upstream())
            upstream_task = asyncio.create_task(upstream_to_client())
            done, pending = await asyncio.wait(
                {client_task, upstream_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                if exc := task.exception():
                    if not isinstance(exc, asyncio.CancelledError):
                        raise exc
    except Exception as e:  # noqa: BLE001 — proxy must not crash the ASGI worker
        logger.debug(f'go2rtc WebSocket 代理结束: {e}')
    finally:
        if client_ws.client_state.name != 'DISCONNECTED':
            await client_ws.close()

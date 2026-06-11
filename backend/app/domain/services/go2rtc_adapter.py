"""Go2RtcAdapter — sync camera RTSP sources with go2rtc and build live URLs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from loguru import logger


def mac_to_stream_name(mac: str) -> str:
    return mac.replace(':', '-').upper()


@dataclass
class Go2RtcConfig:
    enabled: bool = False
    api_base: str = 'http://127.0.0.1:1984'
    rtsp_base: str = 'rtsp://127.0.0.1:8554'
    api_username: str = ''
    api_password: str = ''


@dataclass
class LiveStreamInfo:
    mode: str  # mse | mjpeg_fallback
    stream_name: str
    status: str  # ready | unavailable
    mse_ws_url: str | None = None
    webrtc_url: str | None = None
    mjpeg_url: str | None = None


class Go2RtcHttpClient(Protocol):
    # Use *args, **kwargs to structurally match httpx.AsyncClient, whose
    # method signatures are keyword-only and don't align with the previous
    # narrower `**kwargs`-only Protocol definition.
    async def get(self, *args: Any, **kwargs: Any) -> httpx.Response: ...
    async def put(self, *args: Any, **kwargs: Any) -> httpx.Response: ...
    async def patch(self, *args: Any, **kwargs: Any) -> httpx.Response: ...
    async def delete(self, *args: Any, **kwargs: Any) -> httpx.Response: ...
    async def post(self, *args: Any, **kwargs: Any) -> httpx.Response: ...


class Go2RtcAdapter:
    def __init__(
        self,
        config: Go2RtcConfig | None = None,
        http_client: Go2RtcHttpClient | None = None,
    ):
        self._config = config or Go2RtcConfig()
        self._http = http_client

    @property
    def config(self) -> Go2RtcConfig:
        return self._config

    def restream_url(self, stream_name: str) -> str:
        base = self._config.rtsp_base.rstrip('/')
        return f'{base}/{stream_name}'

    def build_live_info(self, camera_mac: str) -> LiveStreamInfo:
        mac = camera_mac.upper()
        stream_name = mac_to_stream_name(mac)
        mjpeg = f'/api/v1/cameras/{mac}/stream/mjpeg'
        if not self._config.enabled:
            return LiveStreamInfo(
                mode='mjpeg_fallback',
                stream_name=stream_name,
                status='ready',
                mjpeg_url=mjpeg,
            )
        return LiveStreamInfo(
            mode='mse',
            stream_name=stream_name,
            status='ready',
            mse_ws_url=f'/api/v1/cameras/{mac}/live/ws',
            webrtc_url=f'/api/v1/cameras/{mac}/live/webrtc',
            mjpeg_url=mjpeg,
        )

    async def ping(self) -> bool:
        if not self._config.enabled or self._http is None:
            return False
        try:
            resp = await self._http.get(
                f'{self._config.api_base.rstrip("/")}/api/streams',
                timeout=3.0,
            )
            return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def ensure_stream(self, stream_name: str, rtsp_url: str) -> None:
        if not self._config.enabled:
            return
        if self._http is None:
            raise RuntimeError('Go2RtcAdapter HTTP client not configured')
        base = self._config.api_base.rstrip('/')
        streams_url = f'{base}/api/streams'
        try:
            list_resp = await self._http.get(streams_url, timeout=10.0)
            list_resp.raise_for_status()
            existing = list_resp.json()
            params = {'src': rtsp_url, 'name': stream_name}
            if stream_name in existing:
                resp = await self._http.patch(streams_url, params=params, timeout=10.0)
            else:
                resp = await self._http.put(streams_url, params=params, timeout=10.0)
            resp.raise_for_status()
        except (httpx.HTTPError, OSError) as e:
            # go2rtc is enabled but unreachable (process down, port refused,
            # DNS error). The /cameras/{mac}/live route's subsequent ping()
            # will detect this and return the mjpeg_fallback payload — we
            # must not 500 here.
            logger.warning(f'go2rtc 同步流 {stream_name} 失败（go2rtc 不可达）: {e}')

    async def remove_stream(self, stream_name: str) -> None:
        if not self._config.enabled or self._http is None:
            return
        base = self._config.api_base.rstrip('/')
        try:
            resp = await self._http.delete(
                f'{base}/api/streams',
                params={'src': stream_name},
                timeout=10.0,
            )
            resp.raise_for_status()
        except (httpx.HTTPError, OSError) as e:
            logger.warning(f'go2rtc 移除流 {stream_name} 失败（go2rtc 不可达）: {e}')

    def go2rtc_ws_url(self, stream_name: str) -> str:
        base = self._config.api_base.rstrip('/')
        ws_base = base.replace('https://', 'wss://').replace('http://', 'ws://')
        return f'{ws_base}/api/ws?src={stream_name}'

    def go2rtc_webrtc_url(self, stream_name: str) -> str:
        base = self._config.api_base.rstrip('/')
        return f'{base}/api/webrtc?src={stream_name}'

    async def post_webrtc(self, stream_name: str, body: bytes, content_type: str) -> httpx.Response:
        if self._http is None:
            raise RuntimeError('Go2RtcAdapter HTTP client not configured')
        return await self._http.post(
            self.go2rtc_webrtc_url(stream_name),
            content=body,
            headers={'Content-Type': content_type},
            timeout=30.0,
        )

"""Shared scanner configuration and optional third-party dependencies."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

# Dedicated executor for blocking I/O (hostname resolution + ping).
# 128 workers = 64 semaphore × 2 concurrent blocking ops per device, no queuing.
IO_EXECUTOR = ThreadPoolExecutor(max_workers=128, thread_name_prefix='scanner_io')

ARP: Any = None
Ether: Any = None
srp: Any = None
SCAPY_AVAILABLE = False

AsyncMacLookup: Any = None
MAC_LOOKUP_AVAILABLE = False

try:
    from scapy.all import ARP as _ARP  # type: ignore[attr-defined]
    from scapy.all import Ether as _Ether  # type: ignore[attr-defined]
    from scapy.all import srp as _srp

    ARP, Ether, srp = _ARP, _Ether, _srp
    SCAPY_AVAILABLE = True
except ImportError:
    pass

try:
    from mac_vendor_lookup import AsyncMacLookup as _AsyncMacLookup

    AsyncMacLookup = _AsyncMacLookup
    MAC_LOOKUP_AVAILABLE = True
except ImportError:
    pass

# Well-known TCP ports probed on the local LAN (home-admin scope only).
PORT_SERVICES: dict[int, str] = {
    22: 'ssh',
    80: 'http',
    443: 'https',
    445: 'smb',
    548: 'afp',
    554: 'rtsp',
    8554: 'rtsp_alt',
    10554: 'rtsp_alt2',
    631: 'ipp',
    1883: 'mqtt',
    2020: 'onvif',
    37777: 'dahua',
    34567: 'camera_sdk',
    8899: 'camera_web',
    9000: 'camera_web_alt',
    3389: 'rdp',
    5000: 'synology',
    5001: 'synology_https',
    8000: 'http_alt',
    8008: 'chromecast',
    8009: 'chromecast_tls',
    8080: 'http_proxy',
    8443: 'https_alt',
    9100: 'jetdirect',
    32400: 'plex',
    515: 'lpd',
}

# Backward-compatible aliases for tests and legacy imports.
_IO_EXECUTOR = IO_EXECUTOR
_SCAPY_AVAILABLE = SCAPY_AVAILABLE
_MAC_LOOKUP_AVAILABLE = MAC_LOOKUP_AVAILABLE
_PORT_SERVICES = PORT_SERVICES

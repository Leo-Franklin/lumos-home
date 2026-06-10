"""Scan metadata builders and Device field persistence helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.domain.models.device import Device

from .constants import PORT_SERVICES


def extract_mac_oui(mac: str) -> str:
    normalized = mac.replace('-', ':').upper()
    parts = normalized.split(':')
    return ':'.join(parts[:3]) if len(parts) >= 3 else normalized


def map_ports_to_services(open_ports: list[int]) -> list[dict[str, int | str]]:
    return [
        {'port': port, 'name': PORT_SERVICES[port]}
        for port in sorted(open_ports)
        if port in PORT_SERVICES
    ]


def guess_os_from_ttl(ttl: int | None) -> str | None:
    if ttl is None:
        return None
    if ttl >= 250:
        return 'network_device'
    if ttl >= 120:
        return 'windows'
    if ttl >= 60:
        return 'unix'
    if ttl >= 30:
        return 'embedded'
    return None


def build_scan_metadata(
    *,
    mac: str,
    open_ports: list[int],
    latency: float | None,
    ttl: int | None,
    netbios_name: str | None,
    http_banners: dict[int, dict[str, str | None]],
    upnp: dict[str, Any] | None,
    type_confidence: float,
    type_signals: list[dict[str, str]],
    discovery_source: str,
) -> dict[str, Any]:
    return {
        'scanned_at': datetime.now().isoformat(),  # noqa: DTZ005 - stored as naive local time
        'mac_oui': extract_mac_oui(mac),
        'discovery_source': discovery_source,
        'ttl': ttl,
        'os_hint': guess_os_from_ttl(ttl),
        'latency_ms': latency,
        'netbios_name': netbios_name,
        'services': map_ports_to_services(open_ports),
        'http_banners': {str(port): banner for port, banner in http_banners.items()},
        'upnp': upnp,
        'type_confidence': round(type_confidence, 2),
        'type_signals': type_signals,
    }


def persist_scan_fields(device: Device, data: dict[str, Any]) -> None:
    """Apply scan enrichment fields onto a Device ORM row."""
    device.ip = data['ip']
    device.vendor = data['vendor']
    device.hostname = data['hostname']
    device.response_time_ms = data['latency']
    ports = data.get('open_ports')
    if ports is not None:
        device.open_ports = json.dumps(sorted(ports))
    meta = data.get('scan_metadata')
    if meta is not None:
        device.scan_metadata = json.dumps(meta, ensure_ascii=False)


# Backward-compatible private aliases.
_extract_mac_oui = extract_mac_oui
_map_ports_to_services = map_ports_to_services
_guess_os_from_ttl = guess_os_from_ttl
_build_scan_metadata = build_scan_metadata
_persist_scan_fields = persist_scan_fields

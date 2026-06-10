"""Per-device scan enrichment (vendor, ports, type inference)."""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from app.domain.services.device_type_inference import (
    guess_device_type_detailed,
    infer_display_vendor,
    resolve_persisted_device_type,
)

from .metadata import build_scan_metadata
from .probe import Scanner


async def fetch_upnp_for_ip(
    ip: str, upnp_cache: dict[str, dict[str, Any]] | None
) -> dict[str, Any] | None:
    if not upnp_cache:
        return None
    return upnp_cache.get(ip)


async def build_upnp_cache(timeout: float = 2.0) -> dict[str, dict[str, Any]]:
    from app.domain.services.dlna_service import fetch_upnp_basic_info, ssdp_search

    cache: dict[str, dict[str, Any]] = {}
    try:
        locations = await ssdp_search(timeout)
        for location in locations:
            info = await fetch_upnp_basic_info(location)
            if info and info.get('ip') and info['ip'] not in cache:
                cache[info['ip']] = info
    except Exception as e:  # noqa: BLE001 - SSDP/UPnP is best-effort enrichment
        logger.debug(f'UPnP 缓存构建失败: {e}')
    return cache


async def enrich_device(
    scanner: Scanner,
    d: dict,
    upnp_cache: dict[str, dict[str, Any]] | None = None,
    gateway_ips: frozenset[str] | None = None,
) -> dict:
    """Concurrently resolve vendor/hostname/latency/open_ports/fingerprints for one device."""
    discovery_source = d.get('discovery_source', 'arp')
    if d.get('is_local'):
        discovery_source = 'local'
        vendor, hostname, latency_ttl = await asyncio.gather(
            scanner.lookup_vendor(d['mac']),
            scanner.resolve_hostname(d['ip']),
            scanner.measure_latency_with_ttl(d['ip']),
        )
        latency, ttl = latency_ttl
        scan_metadata = build_scan_metadata(
            mac=d['mac'],
            open_ports=[],
            latency=latency,
            ttl=ttl,
            netbios_name=None,
            http_banners={},
            upnp=None,
            type_confidence=1.0,
            type_signals=[{'source': 'local', 'type': 'computer', 'reason': 'local machine'}],
            discovery_source=discovery_source,
        )
        return {
            'mac': d['mac'],
            'ip': d['ip'],
            'vendor': vendor or 'Unknown',
            'hostname': hostname,
            'latency': latency,
            'open_ports': [],
            'scan_metadata': scan_metadata,
            'device_type': 'computer',
        }

    vendor, hostname, latency_ttl, open_ports, netbios_name, upnp = await asyncio.gather(
        scanner.lookup_vendor(d['mac']),
        scanner.resolve_hostname(d['ip']),
        scanner.measure_latency_with_ttl(d['ip']),
        scanner.probe_ports_async(d['ip']),
        scanner.probe_netbios_name(d['ip']),
        fetch_upnp_for_ip(d['ip'], upnp_cache),
    )
    latency, ttl = latency_ttl
    http_banners = await scanner.probe_http_banners(d['ip'], open_ports)
    is_gateway = d['ip'] in (gateway_ips or frozenset())
    device_type, type_confidence, type_signals = guess_device_type_detailed(
        vendor or '',
        open_ports,
        hostname,
        is_gateway=is_gateway,
        mac=d['mac'],
        upnp=upnp,
        netbios_name=netbios_name,
        http_banners=http_banners,
        ttl=ttl,
    )
    display_vendor = infer_display_vendor(
        vendor or 'Unknown',
        upnp=upnp,
        http_banners=http_banners,
        hostname=hostname,
    )
    scan_metadata = build_scan_metadata(
        mac=d['mac'],
        open_ports=open_ports,
        latency=latency,
        ttl=ttl,
        netbios_name=netbios_name,
        http_banners=http_banners,
        upnp=upnp,
        type_confidence=type_confidence,
        type_signals=type_signals,
        discovery_source=discovery_source,
    )
    enriched = {
        'mac': d['mac'],
        'ip': d['ip'],
        'vendor': display_vendor,
        'hostname': hostname,
        'latency': latency,
        'open_ports': open_ports,
        'scan_metadata': scan_metadata,
        'device_type': device_type,
    }
    enriched['device_type'] = resolve_persisted_device_type(enriched)
    return enriched


# Backward-compatible private aliases.
_fetch_upnp_for_ip = fetch_upnp_for_ip
_build_upnp_cache = build_upnp_cache
_enrich_device = enrich_device

"""Tests for enhanced device scan enrichment."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.services.device_type_inference import guess_device_type_detailed
from app.domain.services.scanner import (
    Scanner,
    _build_scan_metadata,
    _enrich_device,
    _extract_mac_oui,
    _guess_os_from_ttl,
    _map_ports_to_services,
    _persist_scan_fields,
)


class TestExtractMacOui:
    def test_extracts_first_three_octets(self):
        assert _extract_mac_oui('AA:BB:CC:DD:EE:FF') == 'AA:BB:CC'

    def test_normalizes_dashes(self):
        assert _extract_mac_oui('aa-bb-cc-dd-ee-ff') == 'AA:BB:CC'


class TestMapPortsToServices:
    def test_maps_known_ports(self):
        services = _map_ports_to_services([80, 443, 554, 99999])
        names = {s['port']: s['name'] for s in services}
        assert names[80] == 'http'
        assert names[443] == 'https'
        assert names[554] == 'rtsp'
        assert 99999 not in names


class TestGuessOsFromTtl:
    def test_windows_ttl(self):
        assert _guess_os_from_ttl(128) == 'windows'

    def test_unix_ttl(self):
        assert _guess_os_from_ttl(64) == 'unix'

    def test_network_device_ttl(self):
        assert _guess_os_from_ttl(255) == 'network_device'

    def test_unknown_ttl(self):
        assert _guess_os_from_ttl(None) is None


class TestGuessDeviceTypeDetailed:
    def test_port_signal_highest_confidence(self):
        device_type, confidence, signals = guess_device_type_detailed(
            vendor='Unknown',
            open_ports=[554],
            hostname=None,
        )
        assert device_type == 'camera'
        assert confidence >= 0.85
        assert any(s['source'] == 'ports' for s in signals)

    def test_upnp_media_renderer_suggests_tv(self):
        device_type, confidence, signals = guess_device_type_detailed(
            vendor='Unknown',
            open_ports=[],
            hostname=None,
            upnp={'device_type': 'urn:schemas-upnp-org:device:MediaRenderer:1'},
        )
        assert device_type == 'tv'
        assert confidence >= 0.8
        assert any(s['source'] == 'upnp' for s in signals)

    def test_netbios_name_signal(self):
        device_type, _, signals = guess_device_type_detailed(
            vendor='Unknown',
            open_ports=[],
            hostname=None,
            netbios_name='DESKTOP-WORK',
        )
        assert device_type == 'computer'
        assert any(s['source'] == 'netbios' for s in signals)

    def test_agreeing_signals_boost_confidence(self):
        device_type, confidence, signals = guess_device_type_detailed(
            vendor='Synology Incorporated',
            open_ports=[5000, 5001],
            hostname='nas-home',
            http_banners={5000: {'server': 'Synology', 'title': 'DiskStation'}},
        )
        assert device_type == 'nas'
        assert confidence >= 0.85
        sources = {s['source'] for s in signals}
        assert 'ports' in sources
        assert 'http' in sources

    def test_http_banner_detects_router(self):
        device_type, confidence, signals = guess_device_type_detailed(
            vendor='Unknown',
            open_ports=[80, 443],
            hostname=None,
            http_banners={80: {'server': 'httpd', 'title': 'TP-LINK Wireless Router'}},
        )
        assert device_type == 'router'
        assert confidence >= 0.75
        assert any(s['source'] == 'http' for s in signals)

    def test_synology_ports_detect_nas(self):
        device_type, confidence, _ = guess_device_type_detailed(
            vendor='Unknown',
            open_ports=[5000, 5001],
            hostname=None,
        )
        assert device_type == 'nas'
        assert confidence >= 0.8

    def test_conflicting_signals_reduce_confidence(self):
        device_type, confidence, signals = guess_device_type_detailed(
            vendor='Apple, Inc.',
            open_ports=[554],
            hostname='iphone-12',
        )
        assert device_type in ('camera', 'phone')
        assert confidence < 0.95
        assert len(signals) >= 2


class TestBuildScanMetadata:
    def test_includes_core_fields(self):
        meta = _build_scan_metadata(
            mac='AA:BB:CC:DD:EE:FF',
            open_ports=[80],
            latency=12.5,
            ttl=64,
            netbios_name='NAS01',
            http_banners={80: {'server': 'nginx', 'title': 'Login'}},
            upnp={'friendly_name': 'Living Room TV'},
            type_confidence=0.9,
            type_signals=[{'source': 'ports', 'type': 'camera', 'reason': 'rtsp'}],
            discovery_source='arp',
        )
        assert meta['mac_oui'] == 'AA:BB:CC'
        assert meta['ttl'] == 64
        assert meta['os_hint'] == 'unix'
        assert meta['netbios_name'] == 'NAS01'
        assert meta['services'] == [{'port': 80, 'name': 'http'}]
        assert meta['http_banners']['80']['server'] == 'nginx'
        assert meta['upnp']['friendly_name'] == 'Living Room TV'
        assert meta['type_confidence'] == 0.9
        assert meta['discovery_source'] == 'arp'
        assert 'scanned_at' in meta


class TestPersistScanFields:
    def test_persists_open_ports_and_metadata(self):
        from app.domain.models.device import Device

        device = Device(mac='AA:BB:CC:DD:EE:FF')
        data = {
            'ip': '192.168.1.10',
            'vendor': 'TP-LINK',
            'hostname': 'router',
            'latency': 3.5,
            'open_ports': [80, 443],
            'scan_metadata': {'ttl': 64},
        }
        _persist_scan_fields(device, data)
        assert device.open_ports == '[80, 443]'
        assert json.loads(device.scan_metadata)['ttl'] == 64
        assert device.response_time_ms == 3.5


@pytest.mark.asyncio
async def test_enrich_device_returns_open_ports_and_metadata():
    scanner = Scanner('192.168.1.0/24')
    scanner.lookup_vendor = AsyncMock(return_value='TP-LINK')
    scanner.resolve_hostname = AsyncMock(return_value='router.local')
    scanner.measure_latency_with_ttl = AsyncMock(return_value=(5.0, 64))
    scanner.probe_ports_async = AsyncMock(return_value=[80, 443])
    scanner.probe_netbios_name = AsyncMock(return_value=None)
    scanner.probe_http_banners = AsyncMock(return_value={80: {'server': 'httpd', 'title': 'Admin'}})

    with patch(
        'app.domain.services.scanner.enrichment.fetch_upnp_for_ip',
        new=AsyncMock(return_value=None),
    ):
        result = await _enrich_device(scanner, {'ip': '192.168.1.1', 'mac': 'AA:BB:CC:DD:EE:01'})

    assert result['open_ports'] == [80, 443]
    assert result['scan_metadata']['mac_oui'] == 'AA:BB:CC'
    assert result['scan_metadata']['ttl'] == 64
    assert result['scan_metadata']['http_banners']['80']['server'] == 'httpd'
    assert result['device_type'] in ('router', 'unknown', 'camera')

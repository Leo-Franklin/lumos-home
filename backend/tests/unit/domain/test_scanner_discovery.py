"""Tests for LAN device discovery reliability (missed hosts on the same subnet)."""

import ipaddress
from unittest.mock import MagicMock, patch

import pytest

from app.domain.services.scanner import (
    Scanner,
    _detect_prefix_length,
    _ip_in_scan_networks,
    detect_default_gateway_ips,
    detect_local_networks,
)


class TestDetectPrefixLengthByNetwork:
    def test_matches_route_when_ip_in_subnet_not_only_src(self):
        """Prefix must be resolved when local IP belongs to route subnet."""
        fake_routes = [
            (0, 0x0, 0x0, 'eth0', '0.0.0.0', 100),
            (0x0000A8C0, 0xFFFFFF00, 0x0, 'eth0', '0.0.0.0', 100),  # 192.168.0.0/24
        ]

        with patch('app.domain.services.scanner._SCAPY_AVAILABLE', True):
            with patch('scapy.all.conf') as mock_conf:
                mock_conf.route.routes = fake_routes
                prefix = _detect_prefix_length('192.168.0.100')

        assert prefix == 24


class TestDetectLocalNetworks:
    def test_includes_192_168_0_subnet(self):
        with patch(
            'app.domain.services.scanner._local_ipv4_addresses',
            return_value=['192.168.0.100', '192.168.1.50'],
        ):
            with patch('app.domain.services.scanner._detect_prefix_length', return_value=24):
                networks = detect_local_networks()

        assert '192.168.0.0/24' in networks
        assert '192.168.1.0/24' in networks


class TestIpInScanNetworks:
    def test_192_168_0_5_in_192_168_0_network(self):
        nets = [ipaddress.ip_network('192.168.0.0/24')]
        assert _ip_in_scan_networks('192.168.0.5', nets) is True

    def test_192_168_0_5_not_in_192_168_1_network(self):
        nets = [ipaddress.ip_network('192.168.1.0/24')]
        assert _ip_in_scan_networks('192.168.0.5', nets) is False


class TestDetectDefaultGatewayIps:
    def test_reads_default_route_from_scapy(self):
        fake_routes = [
            (0, 0x0, 0x0A000001, 'eth0', '0.0.0.0', 100),  # gw 10.0.0.1
            (0x0000A8C0, 0xFFFFFF00, 0x0, 'eth0', '0.0.0.0', 100),
        ]

        with patch('app.domain.services.scanner._SCAPY_AVAILABLE', True):
            with patch('scapy.all.conf') as mock_conf:
                mock_conf.route.routes = fake_routes
                gateways = detect_default_gateway_ips()

        assert gateways == frozenset({'10.0.0.1'})

    def test_non_default_routes_are_ignored(self):
        fake_routes = [
            (0x0000A8C0, 0xFFFFFF00, 0x0A000001, 'eth0', '0.0.0.0', 100),
        ]

        with patch('app.domain.services.scanner._SCAPY_AVAILABLE', True):
            with patch('scapy.all.conf') as mock_conf:
                mock_conf.route.routes = fake_routes
                gateways = detect_default_gateway_ips()

        assert gateways == frozenset()


class TestArpScanDiscovery:
    @pytest.mark.asyncio
    async def test_always_runs_ping_sweep_even_when_arp_finds_devices(self):
        """Hosts that only respond to ICMP must still be discovered via ping+ARP cache."""
        scanner = Scanner('192.168.0.0/24')
        scanner._arp_scan_sync = MagicMock(
            return_value=[{'ip': '192.168.0.1', 'mac': 'AA:BB:CC:DD:EE:01'}]
        )
        scanner._ping_sweep_sync = MagicMock()
        scanner._arp_table_scan_sync = MagicMock(
            return_value=[{'ip': '192.168.0.5', 'mac': '11:22:33:44:55:66'}]
        )
        scanner._get_local_machine_entry = MagicMock(return_value=None)

        with patch('app.domain.services.scanner._SCAPY_AVAILABLE', True):
            result = await scanner.arp_scan()

        scanner._ping_sweep_sync.assert_called_once()
        ips = {d['ip'] for d in result}
        assert '192.168.0.5' in ips

    @pytest.mark.asyncio
    async def test_auto_mode_scans_all_detected_subnets(self):
        with patch(
            'app.domain.services.scanner.detect_local_networks',
            return_value=['192.168.0.0/24', '192.168.1.0/24'],
        ):
            scanner = Scanner('auto')

        assert scanner.networks == ['192.168.0.0/24', '192.168.1.0/24']

    def test_manual_comma_separated_networks(self):
        scanner = Scanner('192.168.0.0/24, 192.168.1.0/24')
        assert scanner.networks == ['192.168.0.0/24', '192.168.1.0/24']

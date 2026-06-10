"""Test for network detection bug: default route (mask=0x0) must be excluded.

Bug: Hisense TV at 192.168.5.44 was not detected because:
1. scapy routing table returned default-route entry with mask_int=0x0
2. _detect_prefix_length() filtered out 0xFFFFFFFF and 0x00000000 but NOT 0x0
3. Resulting network was 0.0.0.0/0, which does not contain 192.168.5.44
4. ARP scan found the TV but filtering by network range dropped it

Fix: Add 0x0 to the exclusion list so default route is skipped and the
correct LAN interface (192.168.5.45 -> /24) is used instead.
"""

import inspect
from unittest.mock import MagicMock, patch

import app.domain.services.scanner as scanner_module
from app.domain.services.scanner import Scanner


class TestDetectPrefixLengthDefaultRoute:
    """Tests for _detect_prefix_length handling of default route (0x0 mask)."""

    def test_excludes_default_route_mask_0x0(self):
        """Default route entry (mask_int=0x0) must be excluded from prefix detection.

        Without this fix, the default route would produce network 0.0.0.0/0 which
        does not contain any LAN devices (e.g. 192.168.5.x), causing them to be
        filtered out of scan results.
        """
        from app.domain.services.scanner import _detect_prefix_length

        # Simulate scapy route table: default route (mask=0x0) and LAN route (mask=/24)
        fake_routes = [
            # (net_int, mask_int, gw, iface, src_ip, metric)
            (0, 0x0, 0x0, 'eth0', '192.168.5.45', 100),  # default route - MUST be excluded
            (0x2D05A8C0, 0xFFFFFF00, 0x0, 'eth0', '192.168.5.45', 100),  # 192.168.5.0/24
        ]

        mock_iface = MagicMock()
        mock_iface.ip = '192.168.5.45'
        mock_ifaces = MagicMock()
        mock_ifaces.items.return_value = [('eth0', mock_iface)]

        with patch('app.domain.services.scanner.constants.SCAPY_AVAILABLE', True):
            with patch('scapy.all.conf') as mock_conf:
                mock_conf.route.routes = fake_routes
                mock_conf.ifaces = mock_ifaces

                prefix = _detect_prefix_length('192.168.5.45')

        assert prefix == 24, (
            f'Expected prefix=24 from LAN interface, got {prefix}. '
            'Default route mask=0x0 was not excluded, producing wrong network.'
        )

    def test_excludes_all_zero_mask(self):
        """mask_int=0x00000000 is a special case and must also be excluded."""
        from app.domain.services.scanner import _detect_prefix_length

        fake_routes = [
            (0, 0x00000000, 0x0, 'eth0', '192.168.5.45', 100),
            (0x2D05A8C0, 0xFFFFFF00, 0x0, 'eth0', '192.168.5.45', 100),
        ]

        mock_iface = MagicMock()
        mock_iface.ip = '192.168.5.45'
        mock_ifaces = MagicMock()
        mock_ifaces.items.return_value = [('eth0', mock_iface)]

        with patch('app.domain.services.scanner.constants.SCAPY_AVAILABLE', True):
            with patch('scapy.all.conf') as mock_conf:
                mock_conf.route.routes = fake_routes
                mock_conf.ifaces = mock_ifaces

                prefix = _detect_prefix_length('192.168.5.45')

        assert prefix == 24


# ---------------------------------------------------------------------------
# Legacy guess_device_type tests (already existed before this bug fix)
# ---------------------------------------------------------------------------


def test_guess_device_type_camera():
    assert Scanner.guess_device_type('TP-LINK', [554]) == 'camera'


def test_guess_device_type_phone():
    assert Scanner.guess_device_type('Apple', []) == 'phone'


def test_guess_device_type_unknown():
    assert Scanner.guess_device_type('SomeUnknown', []) == 'unknown'


class TestScannerGuessDeviceTypeDelegation:
    """Scanner.guess_device_type must delegate to device_type_inference, not legacy heuristics."""

    def test_delegates_to_guess_device_type_detailed(self):
        with patch(
            'app.domain.services.scanner.probe.guess_device_type_detailed',
            return_value=('router', 0.9, [{'source': 'gateway', 'type': 'router'}]),
        ) as mock_detailed:
            result = Scanner.guess_device_type(
                'ZTE',
                [80, 443],
                'gateway',
                upnp={'device_type': 'InternetGatewayDevice'},
                netbios_name='GW',
            )

        assert result == 'router'
        mock_detailed.assert_called_once_with(
            'ZTE',
            [80, 443],
            'gateway',
            upnp={'device_type': 'InternetGatewayDevice'},
            netbios_name='GW',
        )


class TestScannerLegacyDetectionRemoved:
    """Legacy inline type detection was superseded by device_type_inference."""

    def test_scanner_has_no_legacy_detect_helpers(self):
        legacy = (
            '_detect_by_ports',
            '_detect_by_hostname',
            '_detect_by_vendor',
            '_has_router_service_ports',
        )
        for name in legacy:
            assert not hasattr(Scanner, name), f'Scanner.{name} should be removed'

    def test_module_has_no_legacy_upnp_netbios_helpers(self):
        for name in ('_detect_by_upnp', '_detect_by_netbios'):
            assert name not in vars(scanner_module), f'scanner.{name} should be removed'

    def test_scanner_has_no_type_keyword_constants(self):
        type_constants = [
            name
            for name, value in vars(Scanner).items()
            if name.startswith('_')
            and isinstance(value, (tuple, frozenset))
            and name.endswith('_KW')
        ]
        assert type_constants == [], f'remove legacy keyword constants: {type_constants}'

    def test_scanner_class_is_compact(self):
        """After cleanup Scanner should only contain network probing, not type dictionaries."""
        source_lines = len(inspect.getsourcelines(Scanner)[0])
        assert source_lines < 700, f'Scanner class still too large ({source_lines} lines)'

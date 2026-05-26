"""Test for network detection bug: default route (mask=0x0) must be excluded.

Bug: Hisense TV at 192.168.5.44 was not detected because:
1. scapy routing table returned default-route entry with mask_int=0x0
2. _detect_prefix_length() filtered out 0xFFFFFFFF and 0x00000000 but NOT 0x0
3. Resulting network was 0.0.0.0/0, which does not contain 192.168.5.44
4. ARP scan found the TV but filtering by network range dropped it

Fix: Add 0x0 to the exclusion list so default route is skipped and the
correct LAN interface (192.168.5.45 -> /24) is used instead.
"""

from unittest.mock import MagicMock, patch


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

        with patch('app.domain.services.scanner._SCAPY_AVAILABLE', True):
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

        with patch('app.domain.services.scanner._SCAPY_AVAILABLE', True):
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


from app.domain.services.scanner import Scanner

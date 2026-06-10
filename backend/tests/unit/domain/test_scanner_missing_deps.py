"""Tests for scanner optional-dependency guards.

Optional symbols (scapy, mac_vendor_lookup) live in ``scanner.constants``.
Runtime call sites read ``constants.SCAPY_AVAILABLE`` / ``constants.AsyncMacLookup``;
tests must patch that module, not the package re-exports.
"""

import pytest

import app.domain.services.scanner.constants as scanner_constants
from app.domain.services.scanner import Scanner


@pytest.mark.asyncio
async def test_scanner_construction_when_mac_vendor_lookup_missing(monkeypatch):
    """Scanner.__init__ must not crash when AsyncMacLookup is unavailable."""
    monkeypatch.setattr(scanner_constants, 'MAC_LOOKUP_AVAILABLE', False)
    monkeypatch.setattr(scanner_constants, 'AsyncMacLookup', None)

    scanner = Scanner('192.168.1.0/24')

    assert scanner._mac_lookup is None
    assert await scanner.lookup_vendor('AA:BB:CC:DD:EE:FF') == 'Unknown'


def test_arp_scan_sync_raises_cleanly_when_scapy_missing(monkeypatch):
    """Direct _arp_scan_sync calls must fail clearly when scapy is missing."""
    monkeypatch.setattr(scanner_constants, 'SCAPY_AVAILABLE', False)
    monkeypatch.setattr(scanner_constants, 'Ether', None)
    monkeypatch.setattr(scanner_constants, 'ARP', None)
    monkeypatch.setattr(scanner_constants, 'srp', None)

    scanner = Scanner('192.168.1.0/24')

    with pytest.raises(Exception) as exc:
        scanner._arp_scan_sync()

    assert not isinstance(exc.value, NameError), (
        f'Bare NameError leaked out — _arp_scan_sync must guard the missing '
        f'scapy import explicitly. Got: {exc.value!r}'
    )
    assert not (isinstance(exc.value, TypeError) and 'NoneType' in str(exc.value)), (
        f'Bare TypeError(NoneType is not callable) leaked out — explicit '
        f'check needed. Got: {exc.value!r}'
    )


@pytest.mark.asyncio
async def test_arp_scan_falls_back_to_ping_sweep_when_scapy_missing(monkeypatch):
    """arp_scan() must not crash on missing scapy — ping sweep still runs."""
    monkeypatch.setattr(scanner_constants, 'SCAPY_AVAILABLE', False)
    monkeypatch.setattr(scanner_constants, 'Ether', None)
    monkeypatch.setattr(scanner_constants, 'ARP', None)
    monkeypatch.setattr(scanner_constants, 'srp', None)

    scanner = Scanner('192.168.1.0/24')

    monkeypatch.setattr(scanner, '_ping_sweep_sync', lambda: None)
    monkeypatch.setattr(scanner, '_arp_table_scan_sync', lambda: [])
    monkeypatch.setattr(scanner, '_get_local_machine_entry', lambda: None)

    result = await scanner.arp_scan()
    assert isinstance(result, list)

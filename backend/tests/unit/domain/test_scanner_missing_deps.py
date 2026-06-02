"""Tests for scanner.py optional-dependency guards.

pyright reports 4 errors in scanner.py:
  reportPossiblyUnboundVariable for AsyncMacLookup (line 341),
  Ether/ARP (line 378), srp (line 379).

These symbols are imported in a try/except ImportError block. The
RUNTIME calls are already gated by `_SCAPY_AVAILABLE` / `_MAC_LOOKUP_AVAILABLE`
flags at the call sites, but:

  1. pyright can't follow the cross-function `if _SCAPY_AVAILABLE:` guard
     in arp_scan() → _arp_scan_sync().
  2. If a future caller invokes `_arp_scan_sync` directly without going
     through arp_scan(), the guard is bypassed and the code crashes with
     a bare NameError (or, worse, an unhandled call against None).

Contract pinned by these tests:
  - When the optional dependency is missing, Scanner.__init__ must succeed.
  - _arp_scan_sync() must raise a clear, named exception (NOT NameError /
    bare AttributeError) so the call stack is debuggable.
  - arp_scan() must still complete (falling back to ping sweep) when scapy
    is missing — no regression.
"""

import pytest

import app.domain.services.scanner as scanner_module
from app.domain.services.scanner import Scanner

# ─────────────────────────────────────────────────────────────────────────────
# mac_vendor_lookup missing → Scanner still constructs, lookup returns 'Unknown'
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scanner_construction_when_mac_vendor_lookup_missing(monkeypatch):
    """Scanner.__init__ must not crash when AsyncMacLookup is unavailable."""
    monkeypatch.setattr(scanner_module, '_MAC_LOOKUP_AVAILABLE', False)
    monkeypatch.setattr(scanner_module, 'AsyncMacLookup', None)

    scanner = Scanner('192.168.1.0/24')

    assert scanner._mac_lookup is None
    assert await scanner.lookup_vendor('AA:BB:CC:DD:EE:FF') == 'Unknown'


# ─────────────────────────────────────────────────────────────────────────────
# scapy missing → _arp_scan_sync raises clearly, NOT bare NameError
# ─────────────────────────────────────────────────────────────────────────────


def test_arp_scan_sync_raises_cleanly_when_scapy_missing(monkeypatch):
    """If anyone calls _arp_scan_sync directly without scapy installed,
    they must get a clear RuntimeError (or ImportError-flavored exception),
    not a bare NameError."""
    monkeypatch.setattr(scanner_module, '_SCAPY_AVAILABLE', False)
    monkeypatch.setattr(scanner_module, 'Ether', None)
    monkeypatch.setattr(scanner_module, 'ARP', None)
    monkeypatch.setattr(scanner_module, 'srp', None)

    scanner = Scanner('192.168.1.0/24')

    with pytest.raises(Exception) as exc:
        scanner._arp_scan_sync()

    # The bug: bare NameError because the symbol was never bound.
    # The fix: an explicit, descriptive raise.
    assert not isinstance(exc.value, NameError), (
        f'Bare NameError leaked out — _arp_scan_sync must guard the missing '
        f'scapy import explicitly. Got: {exc.value!r}'
    )
    # Also: must not be a misleading TypeError like "None is not callable"
    assert not (isinstance(exc.value, TypeError) and 'NoneType' in str(exc.value)), (
        f'Bare TypeError(NoneType is not callable) leaked out — explicit '
        f'check needed. Got: {exc.value!r}'
    )


# ─────────────────────────────────────────────────────────────────────────────
# arp_scan() (high-level) — when scapy missing, must fall back to ping sweep,
# NOT raise.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_arp_scan_falls_back_to_ping_sweep_when_scapy_missing(monkeypatch):
    """High-level arp_scan() must not crash on missing scapy — it has a
    ping-sweep fallback path."""
    monkeypatch.setattr(scanner_module, '_SCAPY_AVAILABLE', False)
    monkeypatch.setattr(scanner_module, 'Ether', None)
    monkeypatch.setattr(scanner_module, 'ARP', None)
    monkeypatch.setattr(scanner_module, 'srp', None)

    scanner = Scanner('192.168.1.0/24')

    # Stub out the heavy ping/ARP-table work — we only care that arp_scan()
    # itself doesn't blow up on the missing scapy import.
    monkeypatch.setattr(scanner, '_ping_sweep_sync', lambda: None)
    monkeypatch.setattr(scanner, '_arp_table_scan_sync', lambda: [])
    monkeypatch.setattr(scanner, '_get_local_machine_entry', lambda: None)

    result = await scanner.arp_scan()
    # Empty is fine — the important thing is no exception escaped.
    assert isinstance(result, list)

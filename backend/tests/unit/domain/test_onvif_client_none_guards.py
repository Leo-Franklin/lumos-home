"""Tests for OnvifClient None/empty SOAP response handling.

pyright reports 10 errors in domain/services/onvif_client.py:
  reportOptionalMemberAccess / reportOptionalSubscript / reportArgumentType.

The underlying real bugs (which pyright surfaced) are:

  1. _get_device_info_sync: info.Manufacturer when info is None → AttributeError
  2. _get_stream_uri_sync / _get_snapshot_uri_sync: profiles[0] when profiles
     is [] or None → IndexError / TypeError
  3. _get_stream_uri_sync: uri.Uri when uri is None → AttributeError

The contract these tests pin down: on a malformed/empty SOAP response the
client must raise a clear, catchable exception — NOT crash with
AttributeError / IndexError that propagate as opaque 500s in the API.

There are TWO copies of this file (domain/services and services) — the
test exercises BOTH so the parallel-double-fix doesn't drift.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Both copies must pass the same contract.
from app.domain.services.onvif_client import OnvifClient as DomainOnvifClient
from app.services.onvif_client import OnvifClient as LegacyOnvifClient

ONVIF_CLIENTS = [
    pytest.param(DomainOnvifClient, id='domain'),
    pytest.param(LegacyOnvifClient, id='legacy'),
]


def _make_camera_mock(
    device_info=SimpleNamespace(
        Manufacturer='X', Model='Y', FirmwareVersion='1.0', SerialNumber='SN1'
    ),
    profiles=None,
    stream_uri=SimpleNamespace(Uri='rtsp://x/stream'),
    snapshot_uri=SimpleNamespace(Uri='http://x/snap.jpg'),
):
    """Build a mock ONVIFCamera with configurable SOAP responses."""
    devicemgmt = MagicMock()
    devicemgmt.GetDeviceInformation = MagicMock(return_value=device_info)

    media = MagicMock()
    media.GetProfiles = MagicMock(return_value=profiles)
    media.GetStreamUri = MagicMock(return_value=stream_uri)
    media.GetSnapshotUri = MagicMock(return_value=snapshot_uri)

    cam = MagicMock()
    cam.create_devicemgmt_service = MagicMock(return_value=devicemgmt)
    cam.create_media_service = MagicMock(return_value=media)
    return cam


def _make_client(cls, **camera_kwargs):
    """Build an OnvifClient with its ONVIFCamera pre-mocked."""
    client = cls(host='192.0.2.1', port=80, user='u', password='p', timeout=1)
    client._camera = _make_camera_mock(**camera_kwargs)
    return client


# ─────────────────────────────────────────────────────────────────────────────
# Sanity: happy path still works
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_get_device_info_happy_path(cls):
    client = _make_client(cls)
    info = await client.get_device_info()
    assert info == {
        'manufacturer': 'X',
        'model': 'Y',
        'firmware': '1.0',
        'serial': 'SN1',
    }


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_get_stream_uri_happy_path(cls):
    profile = SimpleNamespace(Name='main', token='tk0')
    client = _make_client(cls, profiles=[profile])
    uri = await client.get_stream_uri()
    assert uri == 'rtsp://x/stream'


# ─────────────────────────────────────────────────────────────────────────────
# Bug-driver tests: None / empty SOAP responses must NOT crash with
# AttributeError / IndexError / TypeError. They must raise a clear,
# named exception that upstream `except Exception` already handles.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_get_device_info_raises_clean_error_when_response_is_none(cls):
    """RED (current): raises AttributeError ('Manufacturer' of 'None').
    GREEN: raises a recognisable RuntimeError/ValueError with a useful message.
    """
    client = _make_client(cls, device_info=None)
    with pytest.raises(Exception) as exc:
        await client.get_device_info()
    # The bug surfaces as AttributeError. The fix should raise something more
    # specific that doesn't expose Python attribute internals.
    assert not isinstance(exc.value, AttributeError), (
        f'Bare AttributeError leaked out — None response must be guarded with '
        f'an explicit, descriptive raise. Got: {exc.value!r}'
    )


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_get_stream_uri_raises_clean_error_when_no_profiles(cls):
    """Profiles list is empty (some cameras with no media configured)."""
    client = _make_client(cls, profiles=[])
    with pytest.raises(Exception) as exc:
        await client.get_stream_uri()
    assert not isinstance(exc.value, IndexError | TypeError), (
        f'Bare IndexError/TypeError leaked out — empty profiles must be '
        f'guarded with an explicit raise. Got: {exc.value!r}'
    )


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_get_snapshot_uri_raises_clean_error_when_no_profiles(cls):
    client = _make_client(cls, profiles=[])
    with pytest.raises(Exception) as exc:
        await client.get_snapshot_uri()
    assert not isinstance(exc.value, IndexError | TypeError), (
        f'Bare IndexError/TypeError leaked out — empty profiles must be guarded. Got: {exc.value!r}'
    )


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_get_stream_uri_raises_clean_error_when_uri_response_none(cls):
    """GetStreamUri can return None on some firmware bugs."""
    profile = SimpleNamespace(Name='main', token='tk0')
    client = _make_client(cls, profiles=[profile], stream_uri=None)
    with pytest.raises(Exception) as exc:
        await client.get_stream_uri()
    assert not isinstance(exc.value, AttributeError), (
        f'Bare AttributeError leaked out — None stream URI response must be '
        f'guarded. Got: {exc.value!r}'
    )


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_get_profiles_returns_empty_list_when_no_profiles(cls):
    """Empty profile list is a valid (if unhelpful) response — should NOT raise.

    Notably, get_profiles list-comprehension over [] is already safe; this is
    a regression guard so the fix doesn't accidentally tighten this too.
    """
    client = _make_client(cls, profiles=[])
    profiles = await client.get_profiles()
    assert profiles == []


# ─────────────────────────────────────────────────────────────────────────────
# is_reachable must still swallow the new clean exceptions and return False
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize('cls', ONVIF_CLIENTS)
@pytest.mark.asyncio
async def test_is_reachable_returns_false_on_empty_device_info(cls):
    client = _make_client(cls, device_info=None)
    assert await client.is_reachable() is False

"""XXE / entity-expansion regression test for dlna_service XML parsing.

Background: dlna_service.py parses XML payloads returned by remote DLNA
devices on the local network. A malicious device (or someone on the LAN
spoofing one) can return a SOAP/UPnP description containing custom DTD
entities. Python's stdlib ``xml.etree.ElementTree.fromstring`` expands
internal entities by default, enabling:

  - Entity-substitution payload smuggling (entity body lands in a field).
  - Billion-laugh-style entity expansion → DoS.

ruff S314 flags both call sites. The fix is ``defusedxml.ElementTree``,
which refuses DTDs/entities entirely.

These tests fail under stdlib (entity is expanded into the UDN field) and
pass once dlna_service switches to defusedxml.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.services.dlna_service import DLNAController, fetch_device_info

# UPnP device description that *would* be valid except for the injected
# custom entity. Under a non-defused parser, &xxe; expands to the literal
# string 'MALICIOUS_PAYLOAD' and lands in the UDN field. A safe parser
# rejects the DTD outright.
_XXE_DEVICE_XML = """<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY xxe "MALICIOUS_PAYLOAD">
]>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <device>
    <UDN>uuid:&xxe;</UDN>
    <friendlyName>spoofed-device</friendlyName>
    <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
    <manufacturer>x</manufacturer>
    <modelName>x</modelName>
    <serviceList>
      <service>
        <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
        <controlURL>/AVTransport/ctrl</controlURL>
      </service>
    </serviceList>
  </device>
</root>
"""


# Billion-laugh — small fan-out, but stdlib would still expand. defusedxml
# refuses to even parse the DTD.
_BILLION_LAUGH_XML = """<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY a "AAAA">
  <!ENTITY b "&a;&a;&a;&a;&a;">
  <!ENTITY c "&b;&b;&b;&b;&b;">
]>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <device>
    <UDN>&c;</UDN>
  </device>
</root>
"""


def _fake_httpx_response(text: str):
    """Build a minimal mock that quacks like an httpx Response."""
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def _patch_httpx_get(text: str):
    """Patch httpx.AsyncClient so .get() returns our crafted XML."""
    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get = AsyncMock(return_value=_fake_httpx_response(text))
    return patch('app.domain.services.dlna_service.httpx.AsyncClient', return_value=fake_client)


def _patch_httpx_post(text: str):
    """Patch httpx.AsyncClient so .post() returns our crafted SOAP response."""
    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.post = AsyncMock(return_value=_fake_httpx_response(text))
    return patch('app.domain.services.dlna_service.httpx.AsyncClient', return_value=fake_client)


@pytest.mark.asyncio
async def test_fetch_device_info_rejects_entity_substitution():
    """fetch_device_info must NOT expand custom entities into device fields.

    RED (stdlib ET): info['udn'] contains 'MALICIOUS_PAYLOAD'.
    GREEN (defusedxml): function returns None — DTD rejected at parse time.
    """
    with _patch_httpx_get(_XXE_DEVICE_XML):
        result = await fetch_device_info('http://192.168.1.99:55555/desc.xml')

    # If the parser is defused, it raises on the DTD and the outer except
    # logs+returns None. The strong safety property:
    assert result is None or 'MALICIOUS' not in result.get('udn', ''), (
        f'Custom entity was expanded into device info — XML parser is '
        f'vulnerable to XXE-style entity substitution. Got: {result!r}'
    )


@pytest.mark.asyncio
async def test_fetch_device_info_rejects_billion_laugh():
    """fetch_device_info must NOT recursively expand nested entities."""
    with _patch_httpx_get(_BILLION_LAUGH_XML):
        result = await fetch_device_info('http://192.168.1.99:55555/desc.xml')

    # Either the parse fails (preferred) and we get None, or the UDN does
    # not contain the expanded entity result.
    if result is not None:
        udn = result.get('udn', '')
        assert 'A' * 50 not in udn, (
            'Nested entities were expanded — parser is vulnerable to billion-laugh DoS.'
        )


@pytest.mark.asyncio
async def test_get_transport_info_rejects_entity_substitution():
    """DLNAController.get_transport_info must not expand entities either."""
    soap_xml_with_entity = """<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY pwn "PWNED">
]>
<root>
  <CurrentTransportState>&pwn;</CurrentTransportState>
  <CurrentTransportStatus>OK</CurrentTransportStatus>
  <CurrentSpeed>1</CurrentSpeed>
</root>
"""
    with _patch_httpx_post(soap_xml_with_entity):
        ctrl = DLNAController('http://192.168.1.99:55555/AVTransport/ctrl')
        info = await ctrl.get_transport_info()

    # On parse failure the function returns the all-UNKNOWN fallback dict,
    # which is also safe. The non-negotiable property:
    assert 'PWN' not in info['current_transport_state'], (
        f'SOAP entity was expanded into transport state — parser is '
        f'vulnerable to XXE-style entity substitution. Got: {info!r}'
    )

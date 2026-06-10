"""Evidence collection, fusion, and public inference API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import (
    _AGREEMENT_BOOST,
    _AMBIGUITY_RATIO,
    _CAMERA_HOSTNAME_KW,
    _CAMERA_HTTP_KW,
    _CAMERA_HTTP_VENDOR_LABELS,
    _CAMERA_PERSIST_MIN_CONFIDENCE,
    _CAMERA_PORTS_STRONG,
    _CAMERA_SIGNAL_SOURCES,
    _CAMERA_VENDOR_KW,
    _COMPUTER_HOSTNAME_KW,
    _COMPUTER_PORTS,
    _COMPUTER_VENDOR_KW,
    _CONFLICT_RUNNER_UP_MIN,
    _GAME_CONSOLE_HOSTNAME_KW,
    _IOT_PORTS,
    _IOT_VENDOR_KW,
    _MAC_VENDOR_DISPLAY_LABELS,
    _MIN_CONFIDENCE,
    _NAS_PORTS,
    _NAS_VENDOR_KW,
    _PHONE_HOSTNAME_KW,
    _PHONE_VENDOR_KW,
    _PRINTER_HOSTNAME_KW,
    _PRINTER_PORTS,
    _PRINTER_VENDOR_KW,
    _ROUTER_HOSTNAME_KW,
    _ROUTER_HTTP_KW,
    _ROUTER_SERVICE_PORTS,
    _ROUTER_VENDOR_KW,
    _SMART_SPEAKER_HOSTNAME_KW,
    _TABLET_HOSTNAME_KW,
    _TP_LINK_KW,
    _TV_HOSTNAME_KW,
    _TV_PORTS,
    _TV_VENDOR_KW,
    _WEIGHT_GATEWAY_IP,
    _WEIGHT_HOSTNAME,
    _WEIGHT_HOSTNAME_STRONG,
    _WEIGHT_HTTP_BANNER,
    _WEIGHT_NETBIOS,
    _WEIGHT_PORT_MEDIUM,
    _WEIGHT_PORT_STRONG,
    _WEIGHT_PORT_WEAK,
    _WEIGHT_RANDOM_MAC,
    _WEIGHT_TTL_OTHER,
    _WEIGHT_TTL_PHONE,
    _WEIGHT_UPNP_NAME,
    _WEIGHT_UPNP_TYPE,
    _WEIGHT_VENDOR,
    _WEIGHT_VENDOR_STRONG,
)


@dataclass(frozen=True)
class TypeEvidence:
    source: str
    device_type: str
    weight: float
    reason: str


def _is_randomized_mac(mac: str | None) -> bool:
    """Locally-administered MAC — common on Android/iOS privacy Wi-Fi."""
    if not mac:
        return False
    normalized = mac.replace('-', ':').strip()
    parts = normalized.split(':')
    if not parts:
        return False
    try:
        first_octet = int(parts[0], 16)
    except ValueError:
        return False
    return bool(first_octet & 0x02)


def _has_router_service_ports(open_ports: list[int]) -> bool:
    return bool(frozenset(open_ports) & _ROUTER_SERVICE_PORTS)


def _hostname_hits(hostname: str | None, keywords: tuple[str, ...]) -> bool:
    if not hostname:
        return False
    h = hostname.lower()
    return any(kw in h for kw in keywords)


def _is_tplink_vendor(vendor: str) -> bool:
    v = vendor.lower().strip()
    return any(kw in v for kw in _TP_LINK_KW)


def _http_identity(http_banners: dict[int, dict[str, str | None]] | None) -> str:
    if not http_banners:
        return ''
    parts: list[str] = []
    for banner in http_banners.values():
        parts.append(banner.get('server') or '')
        parts.append(banner.get('title') or '')
    return ' '.join(parts).lower()


def _upnp_identity(upnp: dict[str, Any] | None) -> str:
    if not upnp:
        return ''
    return ' '.join(
        (
            upnp.get('friendly_name') or '',
            upnp.get('manufacturer') or '',
            upnp.get('model_name') or '',
            upnp.get('device_type') or '',
        )
    ).lower()


def _has_camera_context(
    *,
    vendor: str = '',
    is_gateway: bool = False,
    open_ports: list[int],
    hostname: str | None,
    http_banners: dict[int, dict[str, str | None]] | None = None,
    upnp: dict[str, Any] | None = None,
) -> bool:
    if frozenset(open_ports) & _CAMERA_PORTS_STRONG:
        return True
    if _hostname_hits(hostname, _CAMERA_HOSTNAME_KW):
        return True

    upnp_text = _upnp_identity(upnp)
    if upnp_text and any(
        kw in upnp_text
        for kw in (
            'digitalsecuritycamera',
            'networkvideotransmitter',
            'videocamera',
            'ipc',
            *_CAMERA_VENDOR_KW,
            *_CAMERA_HTTP_KW,
        )
    ):
        return True

    http_text = _http_identity(http_banners)
    if http_text and any(kw in http_text for kw in _CAMERA_HTTP_KW):
        return True

    # TP-Link IPC/Tapo: disambiguate from routers via service/HTTP/hostname — not by IP address.
    if _is_tplink_vendor(vendor) and not is_gateway:
        if http_text and any(kw in http_text for kw in _ROUTER_HTTP_KW):
            return False
        ports = frozenset(open_ports)
        if ports & _CAMERA_PORTS_STRONG:
            return True
        if http_text and any(
            kw in http_text
            for kw in ('camera', 'ipc', 'onvif', 'surveillance', 'login', 'tapo', 'kasa')
        ):
            return True
        if ports == {80} and http_text and not any(kw in http_text for kw in _ROUTER_HTTP_KW):
            return True

    if (
        http_text
        and _is_tplink_vendor(http_text)
        and not any(kw in http_text for kw in _ROUTER_HTTP_KW)
    ):
        return True
    return False


def _detect_gateway_evidence(*, is_gateway: bool) -> list[TypeEvidence]:
    if not is_gateway:
        return []
    return [
        TypeEvidence(
            'gateway',
            'router',
            _WEIGHT_GATEWAY_IP,
            'default gateway (routing table)',
        )
    ]


def _detect_mac_evidence(
    mac: str | None,
    *,
    is_gateway: bool,
    hostname: str | None = None,
    open_ports: list[int] | None = None,
) -> list[TypeEvidence]:
    if is_gateway or not _is_randomized_mac(mac):
        return []
    router_context = _has_router_service_ports(open_ports or []) or _hostname_hits(
        hostname, _ROUTER_HOSTNAME_KW
    )
    if router_context:
        return []
    return [
        TypeEvidence(
            'mac',
            'phone',
            _WEIGHT_RANDOM_MAC,
            f'randomized MAC: {mac}',
        )
    ]


def _detect_port_evidence(open_ports: list[int], *, is_gateway: bool) -> list[TypeEvidence]:
    ports = frozenset(open_ports)
    evidence: list[TypeEvidence] = []

    if hits := sorted(ports & _CAMERA_PORTS_STRONG):
        evidence.append(
            TypeEvidence('ports', 'camera', _WEIGHT_PORT_STRONG, f'camera service ports: {hits}')
        )
    if hits := sorted(ports & _PRINTER_PORTS):
        evidence.append(
            TypeEvidence('ports', 'printer', _WEIGHT_PORT_MEDIUM, f'printer ports: {hits}')
        )
    if hits := sorted(ports & _NAS_PORTS):
        evidence.append(TypeEvidence('ports', 'nas', _WEIGHT_PORT_MEDIUM, f'nas ports: {hits}'))
    if hits := sorted(ports & _TV_PORTS):
        evidence.append(TypeEvidence('ports', 'tv', _WEIGHT_PORT_MEDIUM, f'cast/tv ports: {hits}'))
    if hits := sorted(ports & _IOT_PORTS):
        evidence.append(TypeEvidence('ports', 'iot', _WEIGHT_HOSTNAME, f'iot ports: {hits}'))
    if hits := sorted(ports & _COMPUTER_PORTS):
        evidence.append(
            TypeEvidence('ports', 'computer', _WEIGHT_PORT_WEAK, f'workstation ports: {hits}')
        )
    if hits := sorted(ports & _ROUTER_SERVICE_PORTS):
        if not (ports & _CAMERA_PORTS_STRONG):
            weight = _WEIGHT_PORT_MEDIUM if is_gateway else _WEIGHT_PORT_WEAK
            evidence.append(TypeEvidence('ports', 'router', weight, f'web admin ports: {hits}'))
    return evidence


def _detect_hostname_evidence(hostname: str | None) -> list[TypeEvidence]:
    if not hostname:
        return []
    checks: list[tuple[str, tuple[str, ...], float]] = [
        ('router', _ROUTER_HOSTNAME_KW, _WEIGHT_HOSTNAME_STRONG),
        ('phone', _PHONE_HOSTNAME_KW, _WEIGHT_HOSTNAME),
        ('computer', _COMPUTER_HOSTNAME_KW, _WEIGHT_HOSTNAME),
        ('printer', _PRINTER_HOSTNAME_KW, _WEIGHT_HOSTNAME),
        ('tv', _TV_HOSTNAME_KW, _WEIGHT_HOSTNAME),
        ('smart_speaker', _SMART_SPEAKER_HOSTNAME_KW, _WEIGHT_HOSTNAME),
        ('game_console', _GAME_CONSOLE_HOSTNAME_KW, _WEIGHT_HOSTNAME),
        ('tablet', _TABLET_HOSTNAME_KW, _WEIGHT_HOSTNAME),
        ('camera', _CAMERA_HOSTNAME_KW, _WEIGHT_HOSTNAME),
    ]
    evidence: list[TypeEvidence] = []
    for device_type, keywords, weight in checks:
        if _hostname_hits(hostname, keywords):
            evidence.append(
                TypeEvidence(
                    'hostname',
                    device_type,
                    weight,
                    f'hostname: {hostname}',
                )
            )
    return evidence


def _detect_vendor_evidence(
    vendor: str,
    *,
    is_gateway: bool,
    hostname: str | None,
    open_ports: list[int],
    http_banners: dict[int, dict[str, str | None]] | None = None,
    upnp: dict[str, Any] | None = None,
) -> list[TypeEvidence]:
    v = vendor.lower().strip()
    if not v or v == 'unknown':
        return []

    has_router_ports = _has_router_service_ports(open_ports)
    router_hostname = _hostname_hits(hostname, _ROUTER_HOSTNAME_KW)
    phone_hostname = _hostname_hits(hostname, _PHONE_HOSTNAME_KW)
    router_context = is_gateway or has_router_ports or router_hostname
    camera_context = _has_camera_context(
        vendor=vendor,
        is_gateway=is_gateway,
        open_ports=open_ports,
        hostname=hostname,
        http_banners=http_banners,
        upnp=upnp,
    )

    if any(kw in v for kw in _NAS_VENDOR_KW):
        return [TypeEvidence('vendor', 'nas', _WEIGHT_VENDOR, f'vendor: {vendor}')]

    # Dual-use OEMs: ZTE / Huawei make both CPE routers and phones.
    if any(kw in v for kw in ('zte', 'zte corporation', '中兴')):
        if router_context or not phone_hostname:
            return [
                TypeEvidence(
                    'vendor',
                    'router',
                    _WEIGHT_VENDOR_STRONG,
                    f'vendor: {vendor} (network equipment)',
                )
            ]
        return [TypeEvidence('vendor', 'phone', _WEIGHT_VENDOR, f'vendor: {vendor}')]

    if any(kw in v for kw in ('honor', 'honor device', 'hinova')):
        return [TypeEvidence('vendor', 'phone', _WEIGHT_VENDOR_STRONG, f'vendor: {vendor}')]

    if 'huawei' in v:
        if router_context:
            return [
                TypeEvidence(
                    'vendor',
                    'router',
                    _WEIGHT_VENDOR_STRONG,
                    f'vendor: {vendor} (network equipment)',
                )
            ]
        return [TypeEvidence('vendor', 'phone', _WEIGHT_VENDOR, f'vendor: {vendor}')]

    # TP-Link makes routers and IP cameras (Tapo/Kasa/IPC) — disambiguate by context.
    if _is_tplink_vendor(v):
        tplink_router_context = (
            is_gateway
            or router_hostname
            or any(kw in _http_identity(http_banners) for kw in _ROUTER_HTTP_KW)
        )
        if tplink_router_context:
            return [
                TypeEvidence(
                    'vendor',
                    'router',
                    _WEIGHT_VENDOR_STRONG,
                    f'vendor: {vendor} (network equipment)',
                )
            ]
        if camera_context:
            return [
                TypeEvidence(
                    'vendor',
                    'camera',
                    _WEIGHT_VENDOR_STRONG,
                    f'vendor: {vendor} (camera product line)',
                )
            ]
        return []

    if any(kw in v for kw in _ROUTER_VENDOR_KW):
        return [TypeEvidence('vendor', 'router', _WEIGHT_VENDOR, f'vendor: {vendor}')]

    if any(kw in v for kw in _PHONE_VENDOR_KW):
        if router_context:
            return []
        return [TypeEvidence('vendor', 'phone', _WEIGHT_VENDOR, f'vendor: {vendor}')]

    if any(kw in v for kw in _COMPUTER_VENDOR_KW):
        return [TypeEvidence('vendor', 'computer', _WEIGHT_VENDOR, f'vendor: {vendor}')]
    if any(kw in v for kw in _TV_VENDOR_KW):
        return [TypeEvidence('vendor', 'tv', _WEIGHT_VENDOR, f'vendor: {vendor}')]
    if any(kw in v for kw in _PRINTER_VENDOR_KW):
        return [TypeEvidence('vendor', 'printer', _WEIGHT_VENDOR, f'vendor: {vendor}')]
    if any(kw in v for kw in _CAMERA_VENDOR_KW):
        return [
            TypeEvidence(
                'vendor',
                'camera',
                _WEIGHT_VENDOR_STRONG,
                f'vendor: {vendor} (camera manufacturer)',
            )
        ]

    if any(kw in v for kw in _IOT_VENDOR_KW):
        return [TypeEvidence('vendor', 'iot', _WEIGHT_VENDOR, f'vendor: {vendor}')]

    return []


def _detect_upnp_evidence(upnp: dict[str, Any] | None) -> list[TypeEvidence]:
    if not upnp:
        return []
    evidence: list[TypeEvidence] = []
    device_type = (upnp.get('device_type') or '').lower()
    if 'mediarenderer' in device_type or 'dial' in device_type:
        evidence.append(TypeEvidence('upnp', 'tv', _WEIGHT_UPNP_TYPE, 'upnp MediaRenderer'))
    elif 'mediaserver' in device_type:
        evidence.append(TypeEvidence('upnp', 'nas', _WEIGHT_UPNP_TYPE, 'upnp MediaServer'))
    elif 'internetgatewaydevice' in device_type or 'wandevice' in device_type:
        evidence.append(
            TypeEvidence('upnp', 'router', _WEIGHT_UPNP_TYPE, 'upnp InternetGatewayDevice')
        )
    elif any(
        kw in device_type
        for kw in ('digitalsecuritycamera', 'networkvideotransmitter', 'videocamera', 'ipc')
    ):
        evidence.append(
            TypeEvidence('upnp', 'camera', _WEIGHT_UPNP_TYPE, f'upnp device: {device_type}')
        )
    friendly = (upnp.get('friendly_name') or '').lower()
    manufacturer = (upnp.get('manufacturer') or '').lower()
    model = (upnp.get('model_name') or '').lower()
    upnp_identity = f'{friendly} {manufacturer} {model}'
    if any(kw in upnp_identity for kw in _CAMERA_VENDOR_KW + _CAMERA_HTTP_KW):
        evidence.append(
            TypeEvidence(
                'upnp',
                'camera',
                _WEIGHT_UPNP_NAME,
                f'upnp identity: {upnp.get("manufacturer")} {upnp.get("model_name")}'.strip(),
            )
        )
    if any(kw in friendly for kw in ('tv', 'roku', 'fire', 'chromecast', 'apple tv')):
        evidence.append(
            TypeEvidence(
                'upnp',
                'tv',
                _WEIGHT_UPNP_NAME,
                f'upnp friendlyName: {upnp.get("friendly_name")}',
            )
        )
    if any(kw in friendly for kw in ('router', 'gateway', 'wifi', 'zte', 'suishen', '中兴')):
        evidence.append(
            TypeEvidence(
                'upnp',
                'router',
                _WEIGHT_UPNP_NAME,
                f'upnp friendlyName: {upnp.get("friendly_name")}',
            )
        )
    return evidence


def _detect_netbios_evidence(netbios_name: str | None) -> list[TypeEvidence]:
    if not netbios_name:
        return []
    name = netbios_name.lower()
    if name.startswith(('desktop-', 'laptop-', 'pc-', 'workstation')):
        return [
            TypeEvidence('netbios', 'computer', _WEIGHT_NETBIOS, f'netbios name: {netbios_name}')
        ]
    if name.startswith(('brw', 'printer', 'print')) or 'printer' in name:
        return [
            TypeEvidence('netbios', 'printer', _WEIGHT_NETBIOS, f'netbios name: {netbios_name}')
        ]
    if name.startswith('nas') or 'synology' in name or 'qnap' in name:
        return [TypeEvidence('netbios', 'nas', _WEIGHT_NETBIOS, f'netbios name: {netbios_name}')]
    return []


def _detect_http_banner_evidence(
    http_banners: dict[int, dict[str, str | None]] | None,
) -> list[TypeEvidence]:
    if not http_banners:
        return []

    evidence: list[TypeEvidence] = []
    for port, banner in http_banners.items():
        server = (banner.get('server') or '').lower()
        title = (banner.get('title') or '').lower()
        combined = f'{server} {title}'

        if any(kw in combined for kw in ('synology', 'diskstation', 'dsm')):
            evidence.append(
                TypeEvidence('http', 'nas', _WEIGHT_HTTP_BANNER, f'http port {port}: synology')
            )
        elif any(kw in combined for kw in _TP_LINK_KW):
            if any(kw in combined for kw in _ROUTER_HTTP_KW):
                evidence.append(
                    TypeEvidence('http', 'router', _WEIGHT_HTTP_BANNER, f'http port {port}: router')
                )
            else:
                evidence.append(
                    TypeEvidence('http', 'camera', _WEIGHT_HTTP_BANNER, f'http port {port}: camera')
                )
        elif any(kw in combined for kw in _CAMERA_HTTP_KW):
            evidence.append(
                TypeEvidence('http', 'camera', _WEIGHT_HTTP_BANNER, f'http port {port}: camera')
            )
        elif any(
            kw in combined
            for kw in (
                'router',
                'gateway',
                'wireless',
                'openwrt',
                'mikrotik',
                'zte',
                'suishen',
                '中兴',
                'cpe',
            )
        ):
            evidence.append(
                TypeEvidence('http', 'router', _WEIGHT_HTTP_BANNER, f'http port {port}: router')
            )
        elif any(kw in combined for kw in ('printer', 'cups', 'epson', 'canon', 'brother')):
            evidence.append(
                TypeEvidence('http', 'printer', _WEIGHT_HTTP_BANNER, f'http port {port}: printer')
            )
    return evidence


def _detect_ttl_evidence(
    ttl: int | None,
    *,
    is_gateway: bool,
    mac: str | None,
    vendor: str,
    hostname: str | None,
    open_ports: list[int] | None = None,
) -> list[TypeEvidence]:
    if ttl is None:
        return []

    if ttl >= 250:
        return [TypeEvidence('ttl', 'router', _WEIGHT_TTL_OTHER, f'ttl={ttl} network device')]
    if ttl >= 120:
        return [TypeEvidence('ttl', 'computer', _WEIGHT_TTL_OTHER, f'ttl={ttl} windows hint')]

    if ttl >= 60 and not is_gateway:
        v = vendor.lower()
        router_context = (
            _has_router_service_ports(open_ports or [])
            or _hostname_hits(hostname, _ROUTER_HOSTNAME_KW)
            or _is_tplink_vendor(vendor)
        )
        phone_vendor = any(kw in v for kw in _PHONE_VENDOR_KW) or 'huawei' in v or 'honor' in v
        phone_hostname = _hostname_hits(hostname, _PHONE_HOSTNAME_KW)
        randomized = _is_randomized_mac(mac)
        if not router_context and (phone_vendor or phone_hostname or randomized):
            return [
                TypeEvidence(
                    'ttl',
                    'phone',
                    _WEIGHT_TTL_PHONE,
                    f'ttl={ttl} android/unix hint',
                )
            ]
    return []


def _apply_gateway_phone_penalty(
    scores: dict[str, float],
    evidence: list[TypeEvidence],
) -> None:
    """Gateway IPs should not win as phones without overwhelming contrary evidence."""
    has_gateway = any(ev.source == 'gateway' and ev.device_type == 'router' for ev in evidence)
    if has_gateway and 'phone' in scores:
        scores['phone'] *= 0.25


def _fuse_evidence(evidence: list[TypeEvidence]) -> tuple[str, float, list[dict[str, str]]]:
    if not evidence:
        return (
            'unknown',
            0.0,
            [{'source': 'none', 'type': 'unknown', 'reason': 'no matching signals'}],
        )

    scores: dict[str, float] = {}
    sources_by_type: dict[str, set[str]] = {}
    signals: list[dict[str, str]] = []

    for ev in evidence:
        scores[ev.device_type] = scores.get(ev.device_type, 0.0) + ev.weight
        sources_by_type.setdefault(ev.device_type, set()).add(ev.source)
        signals.append({'source': ev.source, 'type': ev.device_type, 'reason': ev.reason})

    _apply_gateway_phone_penalty(scores, evidence)

    for dtype, sources in sources_by_type.items():
        if len(sources) >= 2:
            scores[dtype] *= _AGREEMENT_BOOST

    winner = max(scores, key=lambda k: scores[k])
    winner_score = scores[winner]
    sorted_scores = sorted(scores.values(), reverse=True)

    confidence = min(1.0, winner_score)
    if len(sorted_scores) >= 2:
        runner_up = sorted_scores[1]
        close_competition = runner_up / sorted_scores[0] >= _AMBIGUITY_RATIO
        strong_conflict = runner_up >= _CONFLICT_RUNNER_UP_MIN
        if close_competition or strong_conflict:
            confidence *= 0.7

    confidence = round(confidence, 2)
    if confidence < _MIN_CONFIDENCE:
        return 'unknown', confidence, signals

    return winner, confidence, signals


def guess_device_type_detailed(
    vendor: str,
    open_ports: list[int],
    hostname: str | None = None,
    *,
    is_gateway: bool = False,
    mac: str | None = None,
    upnp: dict[str, Any] | None = None,
    netbios_name: str | None = None,
    http_banners: dict[int, dict[str, str | None]] | None = None,
    ttl: int | None = None,
) -> tuple[str, float, list[dict[str, str]]]:
    """Infer device type via weighted multi-evidence fusion.

    Gateway status must be supplied by the scanner (routing table lookup).
    Device type is never inferred from IP address patterns such as x.x.x.1.
    """
    evidence: list[TypeEvidence] = []
    evidence.extend(_detect_gateway_evidence(is_gateway=is_gateway))
    evidence.extend(
        _detect_mac_evidence(mac, is_gateway=is_gateway, hostname=hostname, open_ports=open_ports)
    )
    evidence.extend(_detect_port_evidence(open_ports, is_gateway=is_gateway))
    evidence.extend(_detect_hostname_evidence(hostname))
    evidence.extend(_detect_upnp_evidence(upnp))
    evidence.extend(_detect_netbios_evidence(netbios_name))
    evidence.extend(_detect_http_banner_evidence(http_banners))
    evidence.extend(
        _detect_vendor_evidence(
            vendor,
            is_gateway=is_gateway,
            hostname=hostname,
            open_ports=open_ports,
            http_banners=http_banners,
            upnp=upnp,
        )
    )
    evidence.extend(
        _detect_ttl_evidence(
            ttl,
            is_gateway=is_gateway,
            mac=mac,
            vendor=vendor,
            hostname=hostname,
            open_ports=open_ports,
        )
    )
    return _fuse_evidence(evidence)


def infer_display_vendor(
    mac_vendor: str,
    *,
    upnp: dict[str, Any] | None = None,
    http_banners: dict[int, dict[str, str | None]] | None = None,
    hostname: str | None = None,
) -> str:
    """Best-effort vendor label for non-technical users (MAC OUI → UPnP → HTTP → hostname)."""
    for banner in (http_banners or {}).values():
        combined = f'{banner.get("server") or ""} {banner.get("title") or ""}'.lower()
        for kw, label in _CAMERA_HTTP_VENDOR_LABELS.items():
            if kw in combined:
                return label

    if hostname:
        h = hostname.lower()
        for kw, label in _CAMERA_HTTP_VENDOR_LABELS.items():
            if kw in h:
                return label

    if upnp:
        manufacturer = (upnp.get('manufacturer') or '').strip()
        model = (upnp.get('model_name') or '').strip()
        if manufacturer:
            return f'{manufacturer} {model}'.strip() if model else manufacturer

    if mac_vendor and mac_vendor.strip().lower() not in ('', 'unknown'):
        normalized = mac_vendor.strip()
        v = normalized.lower()
        for kw, label in _MAC_VENDOR_DISPLAY_LABELS.items():
            if kw in v:
                return label
        return normalized

    return 'Unknown'


def should_persist_camera_type(
    device_type: str,
    confidence: float,
    type_signals: list[dict[str, str]],
) -> bool:
    """Allow camera label in device list when inference is confident (not Camera API registration)."""
    if device_type != 'camera':
        return False
    if confidence < _CAMERA_PERSIST_MIN_CONFIDENCE:
        return False
    return any(
        s.get('type') == 'camera' and s.get('source') in _CAMERA_SIGNAL_SOURCES
        for s in type_signals
    )


def resolve_persisted_device_type(data: dict[str, Any]) -> str:
    """Map inferred type to the value stored on Device.device_type."""
    device_type = data.get('device_type') or 'unknown'
    meta = data.get('scan_metadata') or {}
    confidence = float(meta.get('type_confidence') or 0)
    signals = meta.get('type_signals') or []
    if device_type == 'camera' and not should_persist_camera_type(device_type, confidence, signals):
        return 'unknown'
    return device_type

import asyncio
import ipaddress
import json
import re
import socket
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.camera import Camera
from app.domain.models.device import Device
from app.domain.services.device_type_inference import (
    guess_device_type_detailed,
    infer_display_vendor,
    resolve_persisted_device_type,
)

# Dedicated executor for blocking I/O (hostname resolution + ping).
# 128 workers = 64 semaphore × 2 concurrent blocking ops per device, no queuing.
_IO_EXECUTOR = ThreadPoolExecutor(max_workers=128, thread_name_prefix='scanner_io')

try:
    from scapy.all import ARP, Ether, srp  # type: ignore[attr-defined]

    _SCAPY_AVAILABLE = True
except ImportError:
    ARP = Ether = srp = None  # type: ignore[assignment]
    _SCAPY_AVAILABLE = False

try:
    from mac_vendor_lookup import AsyncMacLookup

    _MAC_LOOKUP_AVAILABLE = True
except ImportError:
    AsyncMacLookup = None
    _MAC_LOOKUP_AVAILABLE = False

# Well-known TCP ports probed on the local LAN (home-admin scope only).
_PORT_SERVICES: dict[int, str] = {
    22: 'ssh',
    80: 'http',
    443: 'https',
    445: 'smb',
    548: 'afp',
    554: 'rtsp',
    8554: 'rtsp_alt',
    10554: 'rtsp_alt2',
    631: 'ipp',
    1883: 'mqtt',
    2020: 'onvif',
    37777: 'dahua',
    34567: 'camera_sdk',
    8899: 'camera_web',
    9000: 'camera_web_alt',
    3389: 'rdp',
    5000: 'synology',
    5001: 'synology_https',
    8000: 'http_alt',
    8008: 'chromecast',
    8009: 'chromecast_tls',
    8080: 'http_proxy',
    8443: 'https_alt',
    9100: 'jetdirect',
    32400: 'plex',
    515: 'lpd',
}


def _extract_mac_oui(mac: str) -> str:
    normalized = mac.replace('-', ':').upper()
    parts = normalized.split(':')
    return ':'.join(parts[:3]) if len(parts) >= 3 else normalized


def _map_ports_to_services(open_ports: list[int]) -> list[dict[str, int | str]]:
    return [
        {'port': port, 'name': _PORT_SERVICES[port]}
        for port in sorted(open_ports)
        if port in _PORT_SERVICES
    ]


def _guess_os_from_ttl(ttl: int | None) -> str | None:
    if ttl is None:
        return None
    if ttl >= 250:
        return 'network_device'
    if ttl >= 120:
        return 'windows'
    if ttl >= 60:
        return 'unix'
    if ttl >= 30:
        return 'embedded'
    return None


def _detect_by_upnp(upnp: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not upnp:
        return None, None
    device_type = (upnp.get('device_type') or '').lower()
    if 'mediarenderer' in device_type or 'dial' in device_type:
        return 'tv', 'upnp MediaRenderer'
    if 'mediaserver' in device_type:
        return 'nas', 'upnp MediaServer'
    if 'internetgatewaydevice' in device_type or 'wandevice' in device_type:
        return 'router', 'upnp InternetGatewayDevice'
    friendly = (upnp.get('friendly_name') or '').lower()
    if any(kw in friendly for kw in ('tv', 'roku', 'fire', 'chromecast', 'apple tv')):
        return 'tv', f'upnp friendlyName: {upnp.get("friendly_name")}'
    return None, None


def _detect_by_netbios(netbios_name: str | None) -> tuple[str | None, str | None]:
    if not netbios_name:
        return None, None
    name = netbios_name.lower()
    if name.startswith(('desktop-', 'laptop-', 'pc-', 'workstation')):
        return 'computer', f'netbios name: {netbios_name}'
    if name.startswith(('brw', 'printer', 'print')) or 'printer' in name:
        return 'printer', f'netbios name: {netbios_name}'
    if name.startswith('nas') or 'synology' in name or 'qnap' in name:
        return 'nas', f'netbios name: {netbios_name}'
    return None, None


def _build_scan_metadata(
    *,
    mac: str,
    open_ports: list[int],
    latency: float | None,
    ttl: int | None,
    netbios_name: str | None,
    http_banners: dict[int, dict[str, str | None]],
    upnp: dict[str, Any] | None,
    type_confidence: float,
    type_signals: list[dict[str, str]],
    discovery_source: str,
) -> dict[str, Any]:
    return {
        'scanned_at': datetime.now().isoformat(),  # noqa: DTZ005 - stored as naive local time
        'mac_oui': _extract_mac_oui(mac),
        'discovery_source': discovery_source,
        'ttl': ttl,
        'os_hint': _guess_os_from_ttl(ttl),
        'latency_ms': latency,
        'netbios_name': netbios_name,
        'services': _map_ports_to_services(open_ports),
        'http_banners': {str(port): banner for port, banner in http_banners.items()},
        'upnp': upnp,
        'type_confidence': round(type_confidence, 2),
        'type_signals': type_signals,
    }


def _persist_scan_fields(device: Device, data: dict[str, Any]) -> None:
    """Apply scan enrichment fields onto a Device ORM row."""
    device.ip = data['ip']
    device.vendor = data['vendor']
    device.hostname = data['hostname']
    device.response_time_ms = data['latency']
    ports = data.get('open_ports')
    if ports is not None:
        device.open_ports = json.dumps(sorted(ports))
    meta = data.get('scan_metadata')
    if meta is not None:
        device.scan_metadata = json.dumps(meta, ensure_ascii=False)


_PRIVATE_NETWORKS = (
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
)
_INVALID_ROUTE_MASKS = (0xFFFFFFFF, 0x00000000, 0x0)


def _is_private_ipv4(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _PRIVATE_NETWORKS)


def _local_ipv4_addresses() -> list[str]:
    """Collect private IPv4 addresses from all active interfaces."""
    found: list[str] = []
    seen: set[str] = set()

    def _add(ip: str) -> None:
        if ip and ip not in seen and _is_private_ipv4(ip):
            seen.add(ip)
            found.append(ip)

    if _SCAPY_AVAILABLE:
        try:
            from scapy.all import conf, get_if_addr

            for iface_name in conf.ifaces:
                _add(get_if_addr(iface_name))
        except Exception as e:  # noqa: BLE001 - scapy third-party boundary
            logger.debug(f'scapy 接口枚举失败: {e}')

    try:
        if sys.platform == 'win32':
            raw = subprocess.check_output(['ipconfig'], timeout=5)
            out = raw.decode('gbk', errors='replace')
            for match in re.finditer(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b', out):
                _add(match.group(1))
        else:
            out = subprocess.check_output(['ip', '-4', 'addr'], text=True, timeout=5)
            for match in re.finditer(r'\binet\s+(\d{1,3}(?:\.\d{1,3}){3})\b', out):
                _add(match.group(1))
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug(f'平台命令枚举本机 IP 失败: {e}')

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            _add(s.getsockname()[0])
    except OSError as e:
        logger.debug(f'默认路由本机 IP 探测失败: {e}')

    return found


def _detect_prefix_length(local_ip: str) -> int:
    """Detect the real prefix length for the interface that holds local_ip."""
    addr = ipaddress.ip_address(local_ip)

    # Method 1: scapy routing table — match by subnet membership, not only src IP
    if _SCAPY_AVAILABLE:
        try:
            from scapy.all import conf

            # routes: (net_int, mask_int, gw, iface, src_ip, metric)
            for entry in conf.route.routes:
                net_int, mask_int, _gw, _iface, src, _metric = entry
                if mask_int in _INVALID_ROUTE_MASKS:
                    continue
                if src == local_ip:
                    netmask_str = socket.inet_ntoa(struct.pack('>I', mask_int))
                    return ipaddress.IPv4Network(f'0.0.0.0/{netmask_str}').prefixlen
                try:
                    route_net = ipaddress.IPv4Network((net_int, mask_int))
                except ValueError:
                    continue
                if addr in route_net:
                    return route_net.prefixlen
        except Exception as e:  # noqa: BLE001 - scapy third-party boundary
            logger.debug(f'scapy 路由表前缀解析失败 {local_ip}: {e}')

    # Method 2: platform commands
    try:
        if sys.platform == 'win32':
            raw = subprocess.check_output(['ipconfig', '/all'], timeout=5)
            out = raw.decode('gbk', errors='replace')
            blocks = re.split(r'\n(?=\S)', out)
            for block in blocks:
                if local_ip not in block:
                    continue
                mask_match = re.search(
                    r'(?:Subnet Mask|子网掩码)\s*[:.．]*\s*(255\.\d+\.\d+\.\d+)',
                    block,
                    re.IGNORECASE,
                )
                if mask_match:
                    return ipaddress.IPv4Network(f'0.0.0.0/{mask_match.group(1)}').prefixlen
        else:
            out = subprocess.check_output(['ip', 'addr'], text=True, timeout=5)
            for line in out.splitlines():
                match = re.search(rf'\b{re.escape(local_ip)}/(\d+)\b', line)
                if match:
                    return int(match.group(1))
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug(f'平台命令解析前缀长度失败 {local_ip}: {e}')

    return 24  # safe fallback for typical home /24 LANs


def detect_local_networks() -> list[str]:
    """Derive all private IPv4 subnets from active interfaces."""
    networks: list[str] = []
    seen: set[str] = set()
    for local_ip in _local_ipv4_addresses():
        prefix_len = _detect_prefix_length(local_ip)
        network = ipaddress.ip_network(f'{local_ip}/{prefix_len}', strict=False)
        net_str = str(network)
        if net_str not in seen:
            seen.add(net_str)
            networks.append(net_str)
    if networks:
        logger.info(f'自动检测网段: {networks}')
        return networks
    logger.warning('网段自动检测失败，回退到 192.168.1.0/24')
    return ['192.168.1.0/24']


def detect_local_network() -> str:
    """Primary subnet for backward compatibility."""
    return detect_local_networks()[0]


def detect_default_gateway_ips() -> frozenset[str]:
    """Collect default gateway IPs from the OS routing table (not x.x.x.1 heuristics)."""
    gateways: set[str] = set()
    scapy_ran = False

    if _SCAPY_AVAILABLE:
        try:
            from scapy.all import conf

            scapy_ran = True
            for net_int, mask_int, gw_int, _iface, _src, _metric in conf.route.routes:
                if gw_int in (0,):
                    continue
                # Default route: destination 0.0.0.0/0 (mask 0 is valid here).
                if net_int == 0 and mask_int in (0, 0x00000000):
                    gw = socket.inet_ntoa(struct.pack('>I', gw_int))
                else:
                    if mask_int in _INVALID_ROUTE_MASKS:
                        continue
                    if (net_int & mask_int) != 0:
                        continue
                    gw = socket.inet_ntoa(struct.pack('>I', gw_int))
                try:
                    if ipaddress.ip_address(gw).is_private:
                        gateways.add(gw)
                except ValueError:
                    continue
        except Exception as e:  # noqa: BLE001 - scapy third-party boundary
            logger.debug(f'scapy 默认网关解析失败: {e}')

    if scapy_ran:
        if gateways:
            logger.debug(f'检测到默认网关: {sorted(gateways)}')
        return frozenset(gateways)

    try:
        if sys.platform == 'win32':
            raw = subprocess.check_output(['route', 'print', '0.0.0.0'], timeout=5)
            out = raw.decode('gbk', errors='replace')
            for line in out.splitlines():
                if '0.0.0.0' not in line:
                    continue
                parts = line.split()
                if len(parts) >= 3 and parts[0] == '0.0.0.0' and parts[1] == '0.0.0.0':
                    gw = parts[2]
                    try:
                        if ipaddress.ip_address(gw).is_private:
                            gateways.add(gw)
                    except ValueError:
                        continue
        else:
            out = subprocess.check_output(['ip', '-4', 'route', 'show', 'default'], timeout=5)
            for line in out.splitlines():
                parts = line.split()
                if 'via' in parts:
                    gw = parts[parts.index('via') + 1]
                    try:
                        if ipaddress.ip_address(gw).is_private:
                            gateways.add(gw)
                    except ValueError:
                        continue
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        logger.debug(f'平台命令解析默认网关失败: {e}')

    if gateways:
        logger.debug(f'检测到默认网关: {sorted(gateways)}')
    return frozenset(gateways)


def _ip_in_scan_networks(
    ip: str,
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


class Scanner:
    # ---------------------------------------------------------------------------
    # Device-type detection keyword constants
    # ---------------------------------------------------------------------------

    # Port-based detection (used by device_type_inference weighted fusion)
    _CAMERA_PORTS: frozenset[int] = frozenset({554, 2020})
    _PRINTER_PORTS: frozenset[int] = frozenset({631, 9100, 515})
    _NAS_PORTS: frozenset[int] = frozenset({5000, 5001, 548, 32400})
    _TV_PORTS: frozenset[int] = frozenset({8008, 8009})
    _IOT_PORTS: frozenset[int] = frozenset({1883})
    _COMPUTER_PORTS: frozenset[int] = frozenset({3389, 445})

    # Hostname-based detection keywords
    _PHONE_HOSTNAME_KW: tuple[str, ...] = (
        'iphone',
        'ipad',
        'android',
        'galaxy',
        'redmi',
        'pixel',
        'honor',
        'magic',
        'hinova',
        'huawei',
        'oppo',
        'vivo',
        'oneplus',
        'realme',
    )
    _COMPUTER_HOSTNAME_KW: tuple[str, ...] = (
        'macbook',
        'imac',
        'desktop',
        'laptop',
        'pc-',
        'workstation',
    )
    _PRINTER_HOSTNAME_KW: tuple[str, ...] = (
        'printer',
        'canon',
        'epson',
        'brother',
    )
    _TV_HOSTNAME_KW: tuple[str, ...] = (
        '-tv',
        'smarttv',
        'lgwebos',
        'tizen',
        'roku',
        'fire-tv',
        'appletv',
        'apple-tv',
    )
    _SMART_SPEAKER_HOSTNAME_KW: tuple[str, ...] = (
        'echo',
        'home-mini',
        'nest-',
        'homepod',
        'xiaoai',
    )
    _GAME_CONSOLE_HOSTNAME_KW: tuple[str, ...] = (
        'switch',
        'playstation',
        'xbox',
        'ps5',
        'ps4',
    )
    _TABLET_HOSTNAME_KW: tuple[str, ...] = (
        'ipad',
        'tab-',
        'tablet',
        'galaxy-tab',
    )
    _CAMERA_HOSTNAME_KW: tuple[str, ...] = (
        'cam',
        'ipc',
        'nvr',
        'dvr',
    )

    # Vendor-based detection keywords
    _ROUTER_VENDOR_KW: tuple[str, ...] = (
        'tp-link',
        'tplink',
        'tp link',
        'netgear',
        'd-link',
        'dlink',
        'cisco',
        'linksys',
        'ubiquiti',
        'mikrotik',
        'zyxel',
        'tenda',
        'ruijie',
        'h3c',
        'huawei technologies',
        'aruba',
        'juniper',
        'netcore',
        'mercury',
        'fast(迅捷)',
        'fast ',
        'comfast',
        'wavlink',
        'eero',
        'zte',
        'zte corporation',
        '中兴',
    )
    _NAS_VENDOR_KW: tuple[str, ...] = ('synology', 'qnap', 'buffalo')
    _PHONE_VENDOR_KW: tuple[str, ...] = (
        'apple',
        'samsung',
        'xiaomi',
        'huawei',
        'honor',
        'honor device',
        'hinova',
        'oppo',
        'vivo',
        'oneplus',
        'realme',
        'motorola',
        'nokia',
        'sony mobile',
        'google',
        'meizu',
        'transsion',
        'tecno',
        'infinix',
        'nothing',
        'fairphone',
    )
    _ROUTER_SERVICE_PORTS: frozenset[int] = frozenset({80, 443, 8080, 8443})
    _COMPUTER_VENDOR_KW: tuple[str, ...] = (
        'intel',
        'realtek',
        'dell',
        'lenovo',
        'hewlett',
        'hp inc',
        'acer',
        'msi',
        'gigabyte',
        'asustek',
        'microsoft',
        'razer',
        'framework',
        'system76',
        'mini pc',
        'vmware',
        'parallels',
        'virtualbox',
    )
    _TV_VENDOR_KW: tuple[str, ...] = (
        'lg electronics',
        'tcl',
        'hisense',
        'skyworth',
        'changhong',
        'konka',
        'haier',
        'sharp',
        'philips',
        'panasonic',
        'roku',
        'amazon technologies',
        'chromecast',
        'vizio',
        'toshiba',
        'funai',
    )
    _SMART_SPEAKER_VENDOR_KW: tuple[str, ...] = (
        'sonos',
        'harman',
        'bose',
        'bang & olufsen',
        'amazon.com',
        'google llc',
        'apple inc',
        'baidu',
        'alibaba',
    )
    _PRINTER_VENDOR_KW: tuple[str, ...] = (
        'canon',
        'epson',
        'brother',
        'ricoh',
        'xerox',
        'kyocera',
        'lexmark',
        'konica',
        'sharp manufacturing',
    )
    _CAMERA_VENDOR_KW: tuple[str, ...] = (
        'hikvision',
        'dahua',
        'axis',
        'reolink',
        'amcrest',
        'wyze',
        'ring',
        'arlo',
        'eufy',
        'imou',
        'uniview',
        'tiandy',
        'kedacom',
        'sunell',
        'yushi',
    )
    _IOT_VENDOR_KW: tuple[str, ...] = (
        'espressif',
        'tuya',
        'shenzhen',
        'hangzhou',
        'yeelight',
        'aqara',
        'broadlink',
        'orvibo',
        'sonoff',
        'tasmota',
        'switchbot',
        'ikea of sweden',
        'signify',
        'philips hue',
        'lifx',
        'wemo',
        'meross',
        'gosund',
        'zigbee',
        'smartthings',
        'nest',
        'ecobee',
        'honeywell',
        'midea',
        'gree',
        'aux',
        'roborock',
        'dreame',
        'ecovacs',
        'irobot',
        'tineco',
    )
    _GAME_CONSOLE_VENDOR_KW: tuple[str, ...] = (
        'nintendo',
        'sony interactive',
        'microsoft xbox',
        'valve',
        'steam',
    )
    _WEARABLE_VENDOR_KW: tuple[str, ...] = (
        'fitbit',
        'garmin',
        'amazfit',
        'zepp',
        'whoop',
    )

    def __init__(self, network: str):
        normalized = network.strip()
        if normalized.lower() == 'auto':
            self.networks = detect_local_networks()
        elif ',' in normalized:
            self.networks = [part.strip() for part in normalized.split(',') if part.strip()]
        else:
            self.networks = [normalized]
        self.network = self.networks[0]
        self._mac_lookup = AsyncMacLookup() if AsyncMacLookup is not None else None

    async def arp_scan(self) -> list[dict]:
        loop = asyncio.get_running_loop()
        seen: dict[str, dict] = {}  # mac -> entry
        scan_nets = [ipaddress.ip_network(net, strict=False) for net in self.networks]

        logger.info(f'开始网络扫描: {self.networks}')

        for net_str in self.networks:
            self.network = net_str
            if _SCAPY_AVAILABLE:
                try:
                    for d in await loop.run_in_executor(None, self._arp_scan_sync):
                        seen[d['mac']] = d
                    logger.info(f'Scapy ARP broadcast ({net_str}) 累计 {len(seen)} 台设备')
                except Exception as e:  # noqa: BLE001 - scapy third-party boundary
                    logger.warning(f'Scapy ARP 失败 ({net_str}): {e}')

            # Always ping sweep: some hosts reply to ICMP but not ARP broadcast.
            await loop.run_in_executor(None, self._ping_sweep_sync)

        self.network = self.networks[0]

        # Supplement from OS ARP cache (hosts reached via ping sweep above).
        for d in await loop.run_in_executor(None, self._arp_table_scan_sync):
            seen.setdefault(d['mac'], d)
        logger.debug(f'ARP 缓存补充后共 {len(seen)} 台设备')

        local_entry = await loop.run_in_executor(None, self._get_local_machine_entry)
        if local_entry:
            seen.setdefault(local_entry['mac'], local_entry)

        result = [d for d in seen.values() if _ip_in_scan_networks(d['ip'], scan_nets)]
        dropped = [d['ip'] for d in seen.values() if not _ip_in_scan_networks(d['ip'], scan_nets)]
        if dropped:
            logger.info(f'网段过滤排除 {len(dropped)} 台设备: {dropped}')
        logger.info(f'网络扫描完成，发现 {len(result)} 台设备')
        return result

    def _arp_scan_sync(self) -> list[dict]:
        if Ether is None or ARP is None or srp is None:
            raise RuntimeError('scapy 不可用，无法执行 ARP broadcast 扫描')
        pkt = Ether(dst='ff:ff:ff:ff:ff:ff') / ARP(pdst=self.network)
        answered, _ = srp(pkt, timeout=2, verbose=0)
        return [{'ip': rcv.psrc, 'mac': rcv.hwsrc.upper()} for _, rcv in answered]

    def _ping_sweep_sync(self) -> None:
        """Ping all subnet hosts to populate the OS ARP cache. Batched for large subnets."""
        net = ipaddress.ip_network(self.network, strict=False)
        hosts = list(net.hosts())
        # Safety cap: skip subnets larger than /21 (>2046 hosts)
        if len(hosts) > 2046:
            logger.warning(f'网段 {net} 超过 2046 个主机，跳过 ping sweep')
            return
        if sys.platform == 'win32':
            ping_args = lambda ip: ['ping', '-n', '1', '-w', '500', str(ip)]
        else:
            ping_args = lambda ip: ['ping', '-c', '1', '-W', '1', str(ip)]

        # Batch into groups of 128 to avoid overwhelming the OS with too many processes
        batch_size = 128
        for i in range(0, len(hosts), batch_size):
            batch = hosts[i : i + batch_size]
            procs = [
                subprocess.Popen(
                    ping_args(ip), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                for ip in batch
            ]
            for p in procs:
                p.wait()

    def _arp_table_scan_sync(self) -> list[dict]:
        """Parse the OS ARP cache via `arp -a`."""
        try:
            out = subprocess.check_output(['arp', '-a'], text=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning(f'arp -a 失败: {e}')
            return []
        results: list[dict] = []
        # Windows: "  192.168.5.1    2c-6d-c1-9c-e3-7a    动态"
        # Linux:   "? (192.168.5.1) at 2c:6d:c1:9c:e3:7a [ether] on eth0"
        for line in out.splitlines():
            ip_match = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', line)
            mac_match = re.search(
                r'([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})',
                line,
            )
            if not ip_match or not mac_match:
                continue
            mac = mac_match.group(1).replace('-', ':').upper()
            if mac in ('FF:FF:FF:FF:FF:FF',) or mac.startswith('01:'):
                continue
            results.append({'ip': ip_match.group(1), 'mac': mac})
        return results

    def _get_local_machine_entry(self) -> dict | None:
        """Return this machine's own IP+MAC — it never appears in its own ARP table."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            mac = self._get_local_mac(local_ip)
            if mac:
                return {'ip': local_ip, 'mac': mac, 'is_local': True}
        except Exception as e:  # noqa: BLE001 - mix of socket IO + scapy third-party
            logger.debug(f'获取本机 IP/MAC 失败: {e}')
        return None

    def _get_local_mac(self, local_ip: str) -> str | None:
        """Get the MAC of the interface that holds local_ip."""
        if _SCAPY_AVAILABLE:
            try:
                from scapy.all import conf, get_if_hwaddr

                for iface_name, iface in conf.ifaces.items():
                    if getattr(iface, 'ip', None) == local_ip:
                        mac = get_if_hwaddr(iface_name)
                        if mac and mac != '00:00:00:00:00:00':
                            return mac.upper()
            except Exception as e:  # noqa: BLE001 - scapy third-party boundary
                logger.debug(f'scapy 接口 MAC 查询失败 {local_ip}: {e}')

        try:
            if sys.platform == 'win32':
                # ipconfig /all pairs IP and MAC in the same interface block
                raw = subprocess.check_output(['ipconfig', '/all'], timeout=5)
                out = raw.decode('gbk', errors='replace')
                blocks = re.split(r'\n(?=\S)', out)  # split on non-indented lines
                for block in blocks:
                    if local_ip in block:
                        m = re.search(
                            r'([0-9A-Fa-f]{2}[-][0-9A-Fa-f]{2}[-][0-9A-Fa-f]{2}[-][0-9A-Fa-f]{2}[-][0-9A-Fa-f]{2}[-][0-9A-Fa-f]{2})',
                            block,
                        )
                        if m:
                            return m.group(1).replace('-', ':').upper()
            else:
                out = subprocess.check_output(['ip', 'link'], text=True, timeout=5)
                # Pair link/ether entries with interface names, then match via 'ip addr'
                addr_out = subprocess.check_output(['ip', 'addr'], text=True, timeout=5)
                iface_match = re.search(rf'(\w+).*\n.*{re.escape(local_ip)}', addr_out)
                if iface_match:
                    matched_iface = iface_match.group(1)
                    mac_match = re.search(
                        rf'{re.escape(matched_iface)}.*\n.*link/ether\s+([0-9a-f:]+)', out
                    )
                    if mac_match:
                        return mac_match.group(1).upper()
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug(f'命令解析本机 MAC 失败 {local_ip}: {e}')
        return None

    async def resolve_hostname(self, ip: str) -> str | None:
        return await asyncio.get_running_loop().run_in_executor(
            _IO_EXECUTOR, self._resolve_hostname_sync, ip
        )

    def _resolve_hostname_sync(self, ip: str) -> str | None:
        try:
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(1.0)
            try:
                hostname, _, _ = socket.gethostbyaddr(ip)
                return hostname
            finally:
                socket.setdefaulttimeout(old_timeout)
        except OSError:
            return None

    async def measure_latency(self, ip: str) -> float | None:
        latency, _ = await self.measure_latency_with_ttl(ip)
        return latency

    async def measure_latency_with_ttl(self, ip: str) -> tuple[float | None, int | None]:
        return await asyncio.get_running_loop().run_in_executor(
            _IO_EXECUTOR, self._measure_latency_with_ttl_sync, ip
        )

    def _measure_latency_with_ttl_sync(self, ip: str) -> tuple[float | None, int | None]:
        try:
            if sys.platform == 'win32':
                cmd = ['ping', '-n', '1', '-w', '300', str(ip)]
                latency_pattern = r'(?:平均|Average)\s*[=<]\s*(\d+)\s*ms'
                ttl_pattern = r'\bTTL[=<](\d+)'
            else:
                cmd = ['ping', '-c', '1', '-W', '1', str(ip)]
                latency_pattern = r'time=(\d+\.?\d*) ms'
                ttl_pattern = r'\bttl=(\d+)'
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
            latency = None
            ttl = None
            latency_match = re.search(latency_pattern, result.stdout, re.IGNORECASE)
            if latency_match:
                latency = float(latency_match.group(1))
            ttl_match = re.search(ttl_pattern, result.stdout, re.IGNORECASE)
            if ttl_match:
                ttl = int(ttl_match.group(1))
            return latency, ttl
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug(f'ping 延迟测量失败 {ip}: {e}')
        return None, None

    async def probe_netbios_name(self, ip: str) -> str | None:
        return await asyncio.get_running_loop().run_in_executor(
            _IO_EXECUTOR, self._probe_netbios_name_sync, ip
        )

    def _probe_netbios_name_sync(self, ip: str) -> str | None:
        if sys.platform == 'win32':
            try:
                out = subprocess.check_output(
                    ['nbtstat', '-A', ip],
                    text=True,
                    timeout=3,
                    errors='replace',
                )
                for line in out.splitlines():
                    match = re.search(r'^\s+(\S+)\s+<00>\s+UNIQUE', line, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
            except (OSError, subprocess.SubprocessError) as e:
                logger.debug(f'nbtstat 查询失败 {ip}: {e}')
            return None

        try:
            payload = self._build_netbios_status_packet()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(1.5)
                sock.sendto(payload, (ip, 137))
                data, _ = sock.recvfrom(4096)
            return self._parse_netbios_status_response(data)
        except OSError as e:
            logger.debug(f'NetBIOS UDP 查询失败 {ip}: {e}')
            return None

    @staticmethod
    def _build_netbios_status_packet() -> bytes:
        name = b'\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00\x00\x21\x00\x01'
        return b'\x12\x34\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00' + name

    @staticmethod
    def _parse_netbios_status_response(data: bytes) -> str | None:
        if len(data) < 57:
            return None
        name_count = data[56]
        offset = 57
        for _ in range(name_count):
            if offset + 18 > len(data):
                break
            raw_name = data[offset : offset + 15]
            suffix = data[offset + 15]
            offset += 18
            if suffix != 0:
                continue
            name = raw_name.decode('ascii', errors='ignore').strip().rstrip('\x00').strip()
            if name and name != '*':
                return name
        return None

    async def probe_http_banners(
        self, ip: str, open_ports: list[int]
    ) -> dict[int, dict[str, str | None]]:
        import httpx

        ports = [p for p in open_ports if p in self._HTTP_BANNER_PORTS]
        if not ports:
            return {}

        async def _fetch(port: int) -> tuple[int, dict[str, str | None] | None]:
            scheme = 'https' if port in (443, 8443, 8009) else 'http'
            url = f'{scheme}://{ip}:{port}/'
            try:
                async with httpx.AsyncClient(
                    timeout=2.0, verify=False, follow_redirects=True
                ) as client:
                    resp = await client.get(url)
                title_match = re.search(
                    r'<title[^>]*>([^<]+)</title>',
                    resp.text[:4096],
                    re.IGNORECASE,
                )
                return port, {
                    'server': resp.headers.get('Server'),
                    'title': title_match.group(1).strip() if title_match else None,
                }
            except Exception as e:  # noqa: BLE001 - httpx boundary per port
                logger.debug(f'HTTP 指纹采集失败 {url}: {e}')
                return port, None

        results = await asyncio.gather(*[_fetch(port) for port in ports])
        return {port: banner for port, banner in results if banner}

    async def lookup_vendor(self, mac: str) -> str:
        if self._mac_lookup is None:
            return 'Unknown'
        try:
            return await self._mac_lookup.lookup(mac)
        except Exception:  # noqa: BLE001 - mac_vendor_lookup third-party boundary
            return 'Unknown'

    # Home-LAN service ports: cameras, printers, NAS, casting, remote access, IoT.
    _PROBE_PORTS = [
        22,
        80,
        443,
        445,
        548,
        554,
        8554,
        10554,
        631,
        1883,
        2020,
        3389,
        34567,
        37777,
        5000,
        5001,
        8000,
        8008,
        8009,
        8080,
        8443,
        8899,
        9000,
        9100,
        32400,
    ]
    _HTTP_BANNER_PORTS = (80, 8080, 8000, 443, 8443, 8008, 8009)

    async def probe_ports_async(self, ip: str, timeout: float = 0.8) -> list[int]:
        """Fast async socket-based port probe. No subprocess overhead."""

        async def _check(port: int) -> int | None:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port), timeout=timeout
                )
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError as e:
                    logger.debug(f'asyncio writer 关闭异常 {ip}:{port}: {e}')
                return port
            except OSError:
                return None

        results = await asyncio.gather(*[_check(p) for p in self._PROBE_PORTS])
        return [p for p in results if p is not None]

    async def probe_ports(self, ip: str) -> list[int]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._probe_ports_sync, ip)

    def _probe_ports_sync(self, ip: str) -> list[int]:
        try:
            import nmap

            nm = nmap.PortScanner()
            nm.scan(ip, '80,443,554,2020,8000,8080,8443', arguments='-T4 --open')
            ports: list[int] = []
            if ip in nm.all_hosts():
                for proto in nm[ip].all_protocols():
                    ports.extend(nm[ip][proto].keys())
            return ports
        except Exception as e:  # noqa: BLE001 - nmap third-party boundary
            logger.debug(f'nmap 探测失败 {ip}: {e}')
            return []

    @staticmethod
    def _detect_by_ports(open_ports: list[int]) -> str | None:
        """Detect device type by open ports. Returns None if no match."""
        ports = frozenset(open_ports)
        if ports & Scanner._CAMERA_PORTS:
            return 'camera'
        if ports & Scanner._PRINTER_PORTS:
            return 'printer'
        return None

    @staticmethod
    def _detect_by_hostname(hostname: str | None) -> str | None:
        """Detect device type by hostname keywords. Returns None if no match."""
        if not hostname:
            return None
        h = hostname.lower()
        if any(kw in h for kw in Scanner._PHONE_HOSTNAME_KW):
            return 'phone'
        if any(kw in h for kw in Scanner._COMPUTER_HOSTNAME_KW):
            return 'computer'
        if any(kw in h for kw in Scanner._PRINTER_HOSTNAME_KW):
            return 'printer'
        if any(kw in h for kw in Scanner._TV_HOSTNAME_KW):
            return 'tv'
        if any(kw in h for kw in Scanner._SMART_SPEAKER_HOSTNAME_KW):
            return 'smart_speaker'
        if any(kw in h for kw in Scanner._GAME_CONSOLE_HOSTNAME_KW):
            return 'game_console'
        if any(kw in h for kw in Scanner._TABLET_HOSTNAME_KW):
            return 'tablet'
        if any(kw in h for kw in Scanner._CAMERA_HOSTNAME_KW):
            return 'camera'
        return None

    @staticmethod
    def _has_router_service_ports(open_ports: list[int] | None) -> bool:
        return bool(frozenset(open_ports or []) & Scanner._ROUTER_SERVICE_PORTS)

    @staticmethod
    def _detect_by_vendor(
        vendor: str,
        hostname: str | None = None,
        *,
        open_ports: list[int] | None = None,
    ) -> str | None:
        """Detect device type by vendor OUI name. Returns None if no match."""
        v = vendor.lower()
        h = (hostname or '').lower()

        # NAS (before router, since some NAS vendors appear in router list)
        if any(kw in v for kw in Scanner._NAS_VENDOR_KW):
            return 'nas'
        # Phone OEM before router — Honor/Huawei phone OUIs overlap with router ICT division
        if any(kw in v for kw in ('honor', 'honor device', 'hinova')):
            return 'phone'
        if 'huawei' in v and not Scanner._has_router_service_ports(open_ports):
            return 'phone'
        # Router / Network equipment
        if any(kw in v for kw in Scanner._ROUTER_VENDOR_KW):
            return 'router'
        # Phones / Tablets
        if any(kw in v for kw in Scanner._PHONE_VENDOR_KW):
            return 'phone'
        # Computers
        if any(kw in v for kw in Scanner._COMPUTER_VENDOR_KW):
            return 'computer'
        # Smart TVs / Streaming
        if any(kw in v for kw in Scanner._TV_VENDOR_KW):
            return 'tv'
        # Smart speakers / Voice assistants (ambiguous vendors need hostname disambiguation)
        if any(kw in v for kw in Scanner._SMART_SPEAKER_VENDOR_KW):
            if any(kw in h for kw in ('echo', 'home', 'nest', 'homepod', 'xiaoai', 'tmall')):
                return 'smart_speaker'
            if 'apple' in v:
                return 'phone'
            return 'smart_speaker'
        # Printers / Scanners
        if any(kw in v for kw in Scanner._PRINTER_VENDOR_KW):
            return 'printer'
        # Cameras / Security — detect only by port or hostname.
        # NOT by vendor OUI: many non-camera devices (routers, NVRs, workstations)
        # share OUI prefixes with camera vendors, causing false 'camera' classifications.
        # Actual cameras must be added manually via the camera management API.
        # IoT / Smart home
        if any(kw in v for kw in Scanner._IOT_VENDOR_KW):
            return 'iot'
        # Game consoles
        if any(kw in v for kw in Scanner._GAME_CONSOLE_VENDOR_KW):
            return 'game_console'
        # Wearables
        if any(kw in v for kw in Scanner._WEARABLE_VENDOR_KW):
            return 'wearable'

        return None

    @staticmethod
    def guess_device_type(
        vendor: str,
        open_ports: list[int],
        hostname: str | None = None,
        *,
        upnp: dict[str, Any] | None = None,
        netbios_name: str | None = None,
    ) -> str:
        """Infer device type from vendor OUI name, open ports, and hostname."""
        device_type, _, _ = guess_device_type_detailed(
            vendor,
            open_ports,
            hostname,
            upnp=upnp,
            netbios_name=netbios_name,
        )
        return device_type


# ---------------------------------------------------------------------------
# Standalone scan helpers (originally in app/routers/devices.py)
# ---------------------------------------------------------------------------


async def _fetch_upnp_for_ip(ip: str, upnp_cache: dict[str, dict[str, Any]] | None) -> dict | None:
    if not upnp_cache:
        return None
    return upnp_cache.get(ip)


async def _build_upnp_cache(timeout: float = 2.0) -> dict[str, dict[str, Any]]:
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


async def _enrich_device(
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
        scan_metadata = _build_scan_metadata(
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
        _fetch_upnp_for_ip(d['ip'], upnp_cache),
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
    scan_metadata = _build_scan_metadata(
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


def _find_unknown_devices(
    enriched: list[dict],
    original_last_seen: dict[str, 'datetime | None'],
    bound_macs: set[str],
    now: datetime,
    staleness_hours: int = 24,
) -> list[dict]:
    """Return devices not bound to any member that are new or stale (not seen recently)."""
    result = []
    for data in enriched:
        mac = data['mac']
        if mac in bound_macs:
            continue
        is_new = mac not in original_last_seen
        last_seen = original_last_seen.get(mac)
        is_stale = (
            not is_new
            and last_seen is not None
            and (now - last_seen).total_seconds() > staleness_hours * 3600
        )
        if is_new or is_stale:
            result.append(data)
    return result


async def _log_scan_result(
    db: 'AsyncSession',
    enriched: list[dict],
    bucket_hour: 'datetime',
) -> None:
    """Upsert per-device presence into DeviceOnlineLog for the given hour bucket."""
    from sqlalchemy import select
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    from app.domain.models.device_online_log import DeviceOnlineLog

    online_macs = {d['mac'] for d in enriched}
    all_result = await db.execute(select(Device.mac, Device.device_type))
    all_devices = all_result.all()
    if not all_devices:
        return

    rows = [
        {
            'mac': d.mac,
            'bucket_hour': bucket_hour,
            'device_type': d.device_type or 'unknown',
            'online_count': 1 if d.mac in online_macs else 0,
            'scan_count': 1,
        }
        for d in all_devices
    ]
    stmt = sqlite_insert(DeviceOnlineLog).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=['mac', 'bucket_hour'],
        set_={
            'online_count': DeviceOnlineLog.online_count + stmt.excluded.online_count,
            'scan_count': DeviceOnlineLog.scan_count + stmt.excluded.scan_count,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def _run_scan(network_range: str):
    """Run device scan: arp scan → enrich → upsert → mark offline → analytics."""
    from datetime import datetime

    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.domain.models.member import MemberDevice
    from app.domain.services.ws_manager import ws_manager

    loop = asyncio.get_running_loop()
    scanner = await loop.run_in_executor(None, Scanner, network_range)
    await ws_manager.broadcast('scan_started', {'subnet': ', '.join(scanner.networks)})
    try:
        devices = await scanner.arp_scan()
        upnp_cache = await _build_upnp_cache()
        gateway_ips = await loop.run_in_executor(None, detect_default_gateway_ips)
        results = {'found': len(devices), 'new': 0, 'offline': 0}

        sem = asyncio.Semaphore(64)

        async def enrich_with_sem(d: dict) -> dict:
            async with sem:
                return await _enrich_device(scanner, d, upnp_cache, gateway_ips)

        enriched = await asyncio.gather(*[enrich_with_sem(d) for d in devices])

        async with AsyncSessionLocal() as db:
            macs = [d['mac'] for d in enriched]
            # Fetch all devices that have an associated Camera record.
            # These are managed by the camera API and should NOT be upserted here.
            camera_macs_result = await db.execute(select(Camera.device_mac))
            camera_macs: set[str] = {row[0] for row in camera_macs_result.all()}
            # For scan purposes, treat devices with a Camera as "known" — do not overwrite
            # their device_type or other fields; only update online status.
            existing_rows = (
                (await db.execute(select(Device).where(Device.mac.in_(macs)))).scalars().all()
            )
            existing_map = {d.mac: d for d in existing_rows}
            original_last_seen: dict[str, datetime | None] = {
                mac: dev.last_seen for mac, dev in existing_map.items()
            }

            now = datetime.now()  # noqa: DTZ005 - Device.last_seen is DateTime (naive)
            for data in enriched:
                mac = data['mac']
                # Skip devices that are managed as Cameras — only update is_online/last_seen
                if mac in camera_macs:
                    existing = existing_map.get(mac)
                    if existing:
                        existing.is_online = True
                        existing.last_seen = now
                        existing.ip = data['ip']
                    continue
                existing = existing_map.get(mac)
                if existing:
                    _persist_scan_fields(existing, data)
                    existing.is_online = True
                    existing.last_seen = now
                    # Registered cameras keep type from camera API; others use scan inference.
                    if mac not in camera_macs:
                        new_type = data['device_type']
                        if existing.device_type in ('unknown', None) or new_type != 'unknown':
                            existing.device_type = new_type
                else:
                    results['new'] += 1
                    device_type = data['device_type']
                    new_device = Device(
                        mac=mac,
                        device_type=device_type,
                        is_online=True,
                        last_seen=now,
                    )
                    _persist_scan_fields(new_device, data)
                    db.add(new_device)
            await db.commit()

            if macs:
                offline_result = await db.execute(
                    select(Device).where(Device.is_online, Device.mac.notin_(macs))
                )
                offline_devices = offline_result.scalars().all()
                for dev in offline_devices:
                    dev.is_online = False
                results['offline'] += len(offline_devices)
                await db.commit()

            try:
                bound_result = await db.execute(select(MemberDevice.mac))
                bound_macs = {row[0] for row in bound_result.all()}
                unknowns = _find_unknown_devices(enriched, original_last_seen, bound_macs, now)
                for u in unknowns:
                    await ws_manager.broadcast(
                        'unknown_device_detected',
                        {
                            'mac': u['mac'],
                            'ip': u['ip'],
                            'vendor': u.get('vendor'),
                            'hostname': u.get('hostname'),
                            'device_type': u.get('device_type'),
                            'open_ports': u.get('open_ports'),
                            'first_seen': now.isoformat(),
                        },
                    )
            except Exception as e:  # noqa: BLE001 - mixes SQLAlchemy + websockets, both can throw
                logger.debug(f'写入未知设备广播失败: {e}')

            try:
                bucket_hour = now.replace(minute=0, second=0, microsecond=0)
                await _log_scan_result(db, enriched, bucket_hour)
            except Exception as e:  # noqa: BLE001 - mixes SQLAlchemy + sqlite upsert paths
                logger.debug(f'写入扫描结果日志失败: {e}')

        await ws_manager.broadcast('scan_completed', results)
    except Exception as e:  # noqa: BLE001 - top-level catch-all for entire scan flow
        await ws_manager.broadcast('scan_completed', {'error': str(e)})

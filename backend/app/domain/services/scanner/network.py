"""Local network detection and subnet/gateway resolution."""

from __future__ import annotations

import ipaddress
import re
import socket
import struct
import subprocess
import sys

from loguru import logger

from . import constants

_PRIVATE_NETWORKS = (
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
)
_INVALID_ROUTE_MASKS = (0xFFFFFFFF, 0x00000000, 0x0)


def is_private_ipv4(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _PRIVATE_NETWORKS)


def local_ipv4_addresses() -> list[str]:
    """Collect private IPv4 addresses from all active interfaces."""
    found: list[str] = []
    seen: set[str] = set()

    def _add(ip: str) -> None:
        if ip and ip not in seen and is_private_ipv4(ip):
            seen.add(ip)
            found.append(ip)

    if constants.SCAPY_AVAILABLE:
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


def detect_prefix_length(local_ip: str) -> int:
    """Detect the real prefix length for the interface that holds local_ip."""
    addr = ipaddress.ip_address(local_ip)

    if constants.SCAPY_AVAILABLE:
        try:
            from scapy.all import conf

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

    return 24


def detect_local_networks() -> list[str]:
    """Derive all private IPv4 subnets from active interfaces."""
    networks: list[str] = []
    seen: set[str] = set()
    for local_ip in local_ipv4_addresses():
        prefix_len = detect_prefix_length(local_ip)
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

    if constants.SCAPY_AVAILABLE:
        try:
            from scapy.all import conf

            scapy_ran = True
            for net_int, mask_int, gw_int, _iface, _src, _metric in conf.route.routes:
                if gw_int in (0,):
                    continue
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
            out = subprocess.check_output(
                ['ip', '-4', 'route', 'show', 'default'], text=True, timeout=5
            )
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


def ip_in_scan_networks(
    ip: str,
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


# Backward-compatible private aliases.
_is_private_ipv4 = is_private_ipv4
_local_ipv4_addresses = local_ipv4_addresses
_detect_prefix_length = detect_prefix_length
_ip_in_scan_networks = ip_in_scan_networks

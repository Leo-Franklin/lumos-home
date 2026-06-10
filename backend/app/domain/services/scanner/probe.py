"""Low-level LAN device probing (ARP, ports, fingerprints)."""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import subprocess
import sys
from typing import Any

from loguru import logger

from app.domain.services.device_type_inference import guess_device_type_detailed

from . import constants
from .network import detect_local_networks, ip_in_scan_networks


class Scanner:
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

    def __init__(self, network: str):
        normalized = network.strip()
        if normalized.lower() == 'auto':
            self.networks = detect_local_networks()
        elif ',' in normalized:
            self.networks = [part.strip() for part in normalized.split(',') if part.strip()]
        else:
            self.networks = [normalized]
        self.network = self.networks[0]
        mac_lookup_cls = constants.AsyncMacLookup
        self._mac_lookup = mac_lookup_cls() if mac_lookup_cls is not None else None

    async def arp_scan(self) -> list[dict]:
        loop = asyncio.get_running_loop()
        seen: dict[str, dict] = {}
        scan_nets = [ipaddress.ip_network(net, strict=False) for net in self.networks]

        logger.info(f'开始网络扫描: {self.networks}')

        for net_str in self.networks:
            self.network = net_str
            if constants.SCAPY_AVAILABLE:
                try:
                    for d in await loop.run_in_executor(None, self._arp_scan_sync):
                        seen[d['mac']] = d
                    logger.info(f'Scapy ARP broadcast ({net_str}) 累计 {len(seen)} 台设备')
                except Exception as e:  # noqa: BLE001 - scapy third-party boundary
                    logger.warning(f'Scapy ARP 失败 ({net_str}): {e}')

            await loop.run_in_executor(None, self._ping_sweep_sync)

        self.network = self.networks[0]

        for d in await loop.run_in_executor(None, self._arp_table_scan_sync):
            seen.setdefault(d['mac'], d)
        logger.debug(f'ARP 缓存补充后共 {len(seen)} 台设备')

        local_entry = await loop.run_in_executor(None, self._get_local_machine_entry)
        if local_entry:
            seen.setdefault(local_entry['mac'], local_entry)

        result = [d for d in seen.values() if ip_in_scan_networks(d['ip'], scan_nets)]
        dropped = [d['ip'] for d in seen.values() if not ip_in_scan_networks(d['ip'], scan_nets)]
        if dropped:
            logger.info(f'网段过滤排除 {len(dropped)} 台设备: {dropped}')
        logger.info(f'网络扫描完成，发现 {len(result)} 台设备')
        return result

    def _arp_scan_sync(self) -> list[dict]:
        ether = constants.Ether
        arp = constants.ARP
        srp_fn = constants.srp
        if ether is None or arp is None or srp_fn is None:
            raise RuntimeError('scapy 不可用，无法执行 ARP broadcast 扫描')
        pkt = ether(dst='ff:ff:ff:ff:ff:ff') / arp(pdst=self.network)
        answered, _ = srp_fn(pkt, timeout=2, verbose=0)
        return [{'ip': rcv.psrc, 'mac': rcv.hwsrc.upper()} for _, rcv in answered]

    def _ping_sweep_sync(self) -> None:
        net = ipaddress.ip_network(self.network, strict=False)
        hosts = list(net.hosts())
        if len(hosts) > 2046:
            logger.warning(f'网段 {net} 超过 2046 个主机，跳过 ping sweep')
            return
        if sys.platform == 'win32':
            ping_args = lambda ip: ['ping', '-n', '1', '-w', '500', str(ip)]
        else:
            ping_args = lambda ip: ['ping', '-c', '1', '-W', '1', str(ip)]

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
        try:
            out = subprocess.check_output(['arp', '-a'], text=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning(f'arp -a 失败: {e}')
            return []
        results: list[dict] = []
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
        if constants.SCAPY_AVAILABLE:
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
                raw = subprocess.check_output(['ipconfig', '/all'], timeout=5)
                out = raw.decode('gbk', errors='replace')
                blocks = re.split(r'\n(?=\S)', out)
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
            constants.IO_EXECUTOR, self._resolve_hostname_sync, ip
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
            constants.IO_EXECUTOR, self._measure_latency_with_ttl_sync, ip
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
            constants.IO_EXECUTOR, self._probe_netbios_name_sync, ip
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

    async def probe_ports_async(self, ip: str, timeout: float = 0.8) -> list[int]:
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

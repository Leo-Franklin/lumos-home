import ipaddress
from urllib.parse import urlparse

_PRIVATE_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
]


def validate_webhook_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        raise ValueError(f'Webhook URL 必须使用 https 协议: {url}')
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f'Webhook URL 无效: {url}')
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        return
    for net in _PRIVATE_NETWORKS:
        if addr in net:
            raise ValueError(f'Webhook URL 不能指向内网地址: {hostname}')

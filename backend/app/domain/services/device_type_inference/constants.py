"""Weights, port sets, and keyword dictionaries for device type inference."""

# --- Reliability tiers ---
WEIGHT_GATEWAY_IP = 0.92
WEIGHT_PORT_STRONG = 0.90
WEIGHT_VENDOR_STRONG = 0.88
WEIGHT_PORT_MEDIUM = 0.85
WEIGHT_UPNP_TYPE = 0.85
WEIGHT_HTTP_BANNER = 0.82
WEIGHT_HOSTNAME_STRONG = 0.82
WEIGHT_UPNP_NAME = 0.80
WEIGHT_HOSTNAME = 0.78
WEIGHT_VENDOR = 0.75
WEIGHT_NETBIOS = 0.75
WEIGHT_PORT_WEAK = 0.68
WEIGHT_RANDOM_MAC = 0.58
WEIGHT_TTL_PHONE = 0.48
WEIGHT_TTL_OTHER = 0.30

MIN_CONFIDENCE = 0.35
AGREEMENT_BOOST = 1.15
AMBIGUITY_RATIO = 0.85
CONFLICT_RUNNER_UP_MIN = 0.80

ROUTER_SERVICE_PORTS: frozenset[int] = frozenset({80, 443, 8080, 8443})
CAMERA_PORTS_STRONG: frozenset[int] = frozenset({554, 8554, 10554, 2020, 37777, 34567, 8899, 9000})
CAMERA_PERSIST_MIN_CONFIDENCE = 0.65
CAMERA_SIGNAL_SOURCES: frozenset[str] = frozenset({'ports', 'http', 'upnp', 'vendor', 'hostname'})
PRINTER_PORTS: frozenset[int] = frozenset({631, 9100, 515})
NAS_PORTS: frozenset[int] = frozenset({5000, 5001, 548, 32400})
TV_PORTS: frozenset[int] = frozenset({8008, 8009})
IOT_PORTS: frozenset[int] = frozenset({1883})
COMPUTER_PORTS: frozenset[int] = frozenset({3389, 445})

ROUTER_HOSTNAME_KW: tuple[str, ...] = (
    'gateway',
    'router',
    'openwrt',
    'mikrotik',
    'suishen',
    'miwifi',
    'asus',
    'netgear',
    'dlink',
    'd-link',
    'tenda',
    'mercury',
    'phicomm',
    'cpe',
    '-ap',
    'wifi',
)
PHONE_HOSTNAME_KW: tuple[str, ...] = (
    'iphone',
    'ipad',
    'android',
    'galaxy',
    'redmi',
    'pixel',
    'honor',
    'magic',
    'hinova',
    'oppo',
    'vivo',
    'oneplus',
    'realme',
    'sm-',
    'rmx',
)
COMPUTER_HOSTNAME_KW: tuple[str, ...] = (
    'macbook',
    'imac',
    'desktop',
    'laptop',
    'pc-',
    'workstation',
)
PRINTER_HOSTNAME_KW: tuple[str, ...] = ('printer', 'canon', 'epson', 'brother')
TV_HOSTNAME_KW: tuple[str, ...] = (
    '-tv',
    'smarttv',
    'lgwebos',
    'tizen',
    'roku',
    'fire-tv',
    'appletv',
    'apple-tv',
)
SMART_SPEAKER_HOSTNAME_KW: tuple[str, ...] = (
    'echo',
    'home-mini',
    'nest-',
    'homepod',
    'xiaoai',
)
GAME_CONSOLE_HOSTNAME_KW: tuple[str, ...] = ('switch', 'playstation', 'xbox', 'ps5', 'ps4')
TABLET_HOSTNAME_KW: tuple[str, ...] = ('ipad', 'tab-', 'tablet', 'galaxy-tab')
CAMERA_HOSTNAME_KW: tuple[str, ...] = (
    'cam',
    'ipc',
    'ipcam',
    'nvr',
    'dvr',
    'hikvision',
    'dahua',
    'ezviz',
    'imou',
    'reolink',
    'uniview',
    'tapo',
    'kasa',
    'vigi',
)
TP_LINK_KW: tuple[str, ...] = ('tp-link', 'tplink', 'tp link')
ROUTER_HTTP_KW: tuple[str, ...] = (
    'wireless router',
    'lte router',
    'mobile router',
    'gateway',
    'archer',
    'deco',
    'tl-wr',
    'tl-mr',
    'tl-er',
    'openwrt',
    'mikrotik',
    'cpe',
)
CAMERA_VENDOR_KW: tuple[str, ...] = (
    'hikvision',
    'dahua',
    'hangzhou hikvision',
    'zhejiang dahua',
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
    'ezviz',
    'foscam',
    'vivotek',
    'annke',
    'lorex',
    'xiongmai',
    'goke',
    'sunell',
    'kedacom',
    'yushi',
    'xm',
    'tuya smart',
)
CAMERA_HTTP_KW: tuple[str, ...] = (
    'hikvision',
    'dahua',
    'reolink',
    'amcrest',
    'wyze',
    'axis',
    'uniview',
    'imou',
    'tiandy',
    'ezviz',
    'yoosee',
    'xmeye',
    'annke',
    'lorex',
    'foscam',
    'vivotek',
    'eufy',
    'tapo',
    'kasa',
    'vigi',
    'onvif',
    'ip camera',
    'network camera',
    'web service login',
    'surveillance',
    'net surveillance',
    'ipc',
)
CAMERA_HTTP_VENDOR_LABELS: dict[str, str] = {
    'hikvision': 'Hikvision',
    'dahua': 'Dahua',
    'reolink': 'Reolink',
    'amcrest': 'Amcrest',
    'wyze': 'Wyze',
    'axis': 'Axis',
    'uniview': 'Uniview',
    'imou': 'Imou',
    'tiandy': 'Tiandy',
    'ezviz': 'EZVIZ',
    'yoosee': 'Yoosee',
    'xmeye': 'XMEye',
    'annke': 'Annke',
    'lorex': 'Lorex',
    'foscam': 'Foscam',
    'vivotek': 'Vivotek',
    'eufy': 'Eufy',
    'tapo': 'TP-Link Tapo',
    'kasa': 'TP-Link Kasa',
    'tplink': 'TP-Link',
    'tp-link': 'TP-Link',
}

MAC_VENDOR_DISPLAY_LABELS: dict[str, str] = {
    'tp-link': 'TP-Link',
    'tplink': 'TP-Link',
    'hangzhou hikvision': 'Hikvision',
    'zhejiang dahua': 'Dahua',
    'synology': 'Synology',
}

ROUTER_VENDOR_KW: tuple[str, ...] = (
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
PHONE_VENDOR_KW: tuple[str, ...] = (
    'apple',
    'samsung',
    'xiaomi',
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
NAS_VENDOR_KW: tuple[str, ...] = ('synology', 'qnap', 'buffalo')
COMPUTER_VENDOR_KW: tuple[str, ...] = (
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
)
TV_VENDOR_KW: tuple[str, ...] = (
    'lg electronics',
    'tcl',
    'hisense',
    'skyworth',
    'roku',
    'amazon technologies',
    'chromecast',
)
IOT_VENDOR_KW: tuple[str, ...] = (
    'espressif',
    'tuya',
    'yeelight',
    'aqara',
    'sonoff',
    'meross',
)
PRINTER_VENDOR_KW: tuple[str, ...] = ('canon', 'epson', 'brother', 'ricoh', 'xerox')

# Private aliases used inside inference logic (unchanged from monolithic module).
_WEIGHT_GATEWAY_IP = WEIGHT_GATEWAY_IP
_WEIGHT_PORT_STRONG = WEIGHT_PORT_STRONG
_WEIGHT_VENDOR_STRONG = WEIGHT_VENDOR_STRONG
_WEIGHT_PORT_MEDIUM = WEIGHT_PORT_MEDIUM
_WEIGHT_UPNP_TYPE = WEIGHT_UPNP_TYPE
_WEIGHT_HTTP_BANNER = WEIGHT_HTTP_BANNER
_WEIGHT_HOSTNAME_STRONG = WEIGHT_HOSTNAME_STRONG
_WEIGHT_UPNP_NAME = WEIGHT_UPNP_NAME
_WEIGHT_HOSTNAME = WEIGHT_HOSTNAME
_WEIGHT_VENDOR = WEIGHT_VENDOR
_WEIGHT_NETBIOS = WEIGHT_NETBIOS
_WEIGHT_PORT_WEAK = WEIGHT_PORT_WEAK
_WEIGHT_RANDOM_MAC = WEIGHT_RANDOM_MAC
_WEIGHT_TTL_PHONE = WEIGHT_TTL_PHONE
_WEIGHT_TTL_OTHER = WEIGHT_TTL_OTHER
_MIN_CONFIDENCE = MIN_CONFIDENCE
_AGREEMENT_BOOST = AGREEMENT_BOOST
_AMBIGUITY_RATIO = AMBIGUITY_RATIO
_CONFLICT_RUNNER_UP_MIN = CONFLICT_RUNNER_UP_MIN
_ROUTER_SERVICE_PORTS = ROUTER_SERVICE_PORTS
_CAMERA_PORTS_STRONG = CAMERA_PORTS_STRONG
_CAMERA_PERSIST_MIN_CONFIDENCE = CAMERA_PERSIST_MIN_CONFIDENCE
_CAMERA_SIGNAL_SOURCES = CAMERA_SIGNAL_SOURCES
_PRINTER_PORTS = PRINTER_PORTS
_NAS_PORTS = NAS_PORTS
_TV_PORTS = TV_PORTS
_IOT_PORTS = IOT_PORTS
_COMPUTER_PORTS = COMPUTER_PORTS
_ROUTER_HOSTNAME_KW = ROUTER_HOSTNAME_KW
_PHONE_HOSTNAME_KW = PHONE_HOSTNAME_KW
_COMPUTER_HOSTNAME_KW = COMPUTER_HOSTNAME_KW
_PRINTER_HOSTNAME_KW = PRINTER_HOSTNAME_KW
_TV_HOSTNAME_KW = TV_HOSTNAME_KW
_SMART_SPEAKER_HOSTNAME_KW = SMART_SPEAKER_HOSTNAME_KW
_GAME_CONSOLE_HOSTNAME_KW = GAME_CONSOLE_HOSTNAME_KW
_TABLET_HOSTNAME_KW = TABLET_HOSTNAME_KW
_CAMERA_HOSTNAME_KW = CAMERA_HOSTNAME_KW
_TP_LINK_KW = TP_LINK_KW
_ROUTER_HTTP_KW = ROUTER_HTTP_KW
_CAMERA_VENDOR_KW = CAMERA_VENDOR_KW
_CAMERA_HTTP_KW = CAMERA_HTTP_KW
_CAMERA_HTTP_VENDOR_LABELS = CAMERA_HTTP_VENDOR_LABELS
_MAC_VENDOR_DISPLAY_LABELS = MAC_VENDOR_DISPLAY_LABELS
_ROUTER_VENDOR_KW = ROUTER_VENDOR_KW
_PHONE_VENDOR_KW = PHONE_VENDOR_KW
_NAS_VENDOR_KW = NAS_VENDOR_KW
_COMPUTER_VENDOR_KW = COMPUTER_VENDOR_KW
_TV_VENDOR_KW = TV_VENDOR_KW
_IOT_VENDOR_KW = IOT_VENDOR_KW
_PRINTER_VENDOR_KW = PRINTER_VENDOR_KW

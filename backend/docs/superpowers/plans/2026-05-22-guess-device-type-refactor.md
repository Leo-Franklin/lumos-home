# guess_device_type 重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `Scanner.guess_device_type`（291行/14种设备类型）拆分为1个主入口+多个私有检测方法的清晰结构。

**Architecture:** 保留静态方法签名不变，内部拆分为 `_detect_by_ports`、`_detect_by_hostname`、`_detect_by_vendor` 三个私有方法，按优先级依次尝试。关键词组抽取为类级 tuple 常量，消除字符串字面量重复。

**Tech Stack:** Python, pytest

---

## 文件清单

- **Modify**: `app/domain/services/scanner.py` — 重构 `guess_device_type` 及新增类级常量
- **Test**: `tests/test_scanner.py` — 验证 14 种设备类型检测行为不变

---

## Task 1: 在 `Scanner` 类中添加类级关键词常量

**Files:**
- Modify: `app/domain/services/scanner.py:36`（`class Scanner` 定义处）

- [ ] **Step 1: 确认 Scanner 类起始行**

查看当前 `class Scanner` 定义的行号位置（预计在 line 36 附近）。

- [ ] **Step 2: 在 `Scanner` 类起始处添加所有关键词 tuple 常量**

在 `class Scanner` 定义之后、第一个方法之前，插入以下全部常量：

```python
# ---------------------------------------------------------------------------
# Device-type detection keyword constants
# ---------------------------------------------------------------------------

# Port-based detection
_CAMERA_PORTS: frozenset[int] = frozenset({554, 2020, 8000})
_PRINTER_PORTS: frozenset[int] = frozenset({631, 9100, 515})

# Hostname-based detection keywords
_PHONE_HOSTNAME_KW: tuple[str, ...] = (
    'iphone', 'ipad', 'android', 'galaxy', 'redmi', 'pixel',
)
_COMPUTER_HOSTNAME_KW: tuple[str, ...] = (
    'macbook', 'imac', 'desktop', 'laptop', 'pc-', 'workstation',
)
_PRINTER_HOSTNAME_KW: tuple[str, ...] = (
    'printer', 'canon', 'epson', 'brother',
)
_TV_HOSTNAME_KW: tuple[str, ...] = (
    '-tv', 'smarttv', 'lgwebos', 'tizen', 'roku', 'fire-tv', 'appletv', 'apple-tv',
)
_SMART_SPEAKER_HOSTNAME_KW: tuple[str, ...] = (
    'echo', 'home-mini', 'nest-', 'homepod', 'xiaoai',
)
_GAME_CONSOLE_HOSTNAME_KW: tuple[str, ...] = (
    'switch', 'playstation', 'xbox', 'ps5', 'ps4',
)
_TABLET_HOSTNAME_KW: tuple[str, ...] = (
    'ipad', 'tab-', 'tablet', 'galaxy-tab',
)
_CAMERA_HOSTNAME_KW: tuple[str, ...] = (
    'cam', 'ipc', 'nvr', 'dvr',
)

# Vendor-based detection keywords
_ROUTER_VENDOR_KW: tuple[str, ...] = (
    'tp-link', 'tplink', 'tp link', 'netgear', 'd-link', 'dlink', 'cisco', 'linksys',
    'ubiquiti', 'mikrotik', 'zyxel', 'tenda', 'ruijie', 'h3c', 'huawei technologies',
    'aruba', 'juniper', 'netcore', 'mercury', 'fast(迅捷)', 'fast ', 'comfast',
    'wavlink', 'eero',
)
_NAS_VENDOR_KW: tuple[str, ...] = ('synology', 'qnap', 'buffalo')
_PHONE_VENDOR_KW: tuple[str, ...] = (
    'apple', 'samsung', 'xiaomi', 'huawei', 'honor', 'oppo', 'vivo', 'oneplus',
    'realme', 'motorola', 'nokia', 'sony mobile', 'google', 'zte', 'meizu',
    'transsion', 'tecno', 'infinix', 'nothing', 'fairphone',
)
_COMPUTER_VENDOR_KW: tuple[str, ...] = (
    'intel', 'realtek', 'dell', 'lenovo', 'hewlett', 'hp inc', 'acer', 'msi',
    'gigabyte', 'asustek', 'microsoft', 'razer', 'framework', 'system76',
    'mini pc', 'vmware', 'parallels', 'virtualbox',
)
_TV_VENDOR_KW: tuple[str, ...] = (
    'lg electronics', 'tcl', 'hisense', 'skyworth', 'changhong', 'konka', 'haier',
    'sharp', 'philips', 'panasonic', 'roku', 'amazon technologies', 'chromecast',
    'vizio', 'toshiba', 'funai',
)
_SMART_SPEAKER_VENDOR_KW: tuple[str, ...] = (
    'sonos', 'harman', 'bose', 'bang & olufsen', 'amazon.com', 'google llc',
    'apple inc', 'baidu', 'alibaba',
)
_PRINTER_VENDOR_KW: tuple[str, ...] = (
    'canon', 'epson', 'brother', 'ricoh', 'xerox', 'kyocera', 'lexmark', 'konica',
    'sharp manufacturing',
)
_CAMERA_VENDOR_KW: tuple[str, ...] = (
    'hikvision', 'dahua', 'axis', 'reolink', 'amcrest', 'wyze', 'ring', 'arlo',
    'eufy', 'imou', 'uniview', 'tiandy', 'kedacom', 'sunell', 'yushi',
)
_IOT_VENDOR_KW: tuple[str, ...] = (
    'espressif', 'tuya', 'shenzhen', 'hangzhou', 'yeelight', 'aqara', 'broadlink',
    'orvibo', 'sonoff', 'tasmota', 'switchbot', 'ikea of sweden', 'signify',
    'philips hue', 'lifx', 'wemo', 'meross', 'gosund', 'zigbee', 'smartthings',
    'nest', 'ecobee', 'honeywell', 'midea', 'gree', 'aux', 'roborock', 'dreame',
    'ecovacs', 'irobot', 'tineco',
)
_GAME_CONSOLE_VENDOR_KW: tuple[str, ...] = (
    'nintendo', 'sony interactive', 'microsoft xbox', 'valve', 'steam',
)
_WEARABLE_VENDOR_KW: tuple[str, ...] = (
    'fitbit', 'garmin', 'amazfit', 'zepp', 'whoop',
)
```

- [ ] **Step 3: 提交**

```bash
git add app/domain/services/scanner.py
git commit -m "refactor(scanner): add device-type detection keyword constants

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

## Task 2: 添加 `_detect_by_ports` 私有方法

**Files:**
- Modify: `app/domain/services/scanner.py` — 在 `guess_device_type` 方法之前插入新方法

- [ ] **Step 1: 在 `guess_device_type` 方法之前插入 `_detect_by_ports` 方法**

在 `guess_device_type` 静态方法之前（约 line 332 位置）插入：

```python
@staticmethod
def _detect_by_ports(open_ports: list[int]) -> str | None:
    """Detect device type by open ports. Returns None if no match."""
    ports = frozenset(open_ports)
    if ports & _CAMERA_PORTS:
        return 'camera'
    if ports & _PRINTER_PORTS:
        return 'printer'
    return None
```

- [ ] **Step 2: 提交**

```bash
git add app/domain/services/scanner.py
git commit -m "refactor(scanner): extract _detect_by_ports method

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

## Task 3: 添加 `_detect_by_hostname` 私有方法

**Files:**
- Modify: `app/domain/services/scanner.py`

- [ ] **Step 1: 在 `_detect_by_ports` 之后插入 `_detect_by_hostname` 方法**

```python
@staticmethod
def _detect_by_hostname(hostname: str | None) -> str | None:
    """Detect device type by hostname keywords. Returns None if no match."""
    if not hostname:
        return None
    h = hostname.lower()
    if any(kw in h for kw in _PHONE_HOSTNAME_KW):
        return 'phone'
    if any(kw in h for kw in _COMPUTER_HOSTNAME_KW):
        return 'computer'
    if any(kw in h for kw in _PRINTER_HOSTNAME_KW):
        return 'printer'
    if any(kw in h for kw in _TV_HOSTNAME_KW):
        return 'tv'
    if any(kw in h for kw in _SMART_SPEAKER_HOSTNAME_KW):
        return 'smart_speaker'
    if any(kw in h for kw in _GAME_CONSOLE_HOSTNAME_KW):
        return 'game_console'
    if any(kw in h for kw in _TABLET_HOSTNAME_KW):
        return 'tablet'
    if any(kw in h for kw in _CAMERA_HOSTNAME_KW):
        return 'camera'
    return None
```

- [ ] **Step 2: 提交**

```bash
git add app/domain/services/scanner.py
git commit -m "refactor(scanner): extract _detect_by_hostname method

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

## Task 4: 添加 `_detect_by_vendor` 私有方法

**Files:**
- Modify: `app/domain/services/scanner.py`

- [ ] **Step 1: 在 `_detect_by_hostname` 之后插入 `_detect_by_vendor` 方法**

```python
@staticmethod
def _detect_by_vendor(vendor: str, hostname: str | None = None) -> str | None:
    """Detect device type by vendor OUI name. Returns None if no match."""
    v = vendor.lower()
    h = (hostname or '').lower()

    # Routers / Network equipment (distinguish NAS from router)
    if any(kw in v for kw in _NAS_VENDOR_KW):
        return 'nas'
    if any(kw in v for kw in _ROUTER_VENDOR_KW):
        return 'router'

    # Phones / Tablets
    if any(kw in v for kw in _PHONE_VENDOR_KW):
        return 'phone'

    # Computers
    if any(kw in v for kw in _COMPUTER_VENDOR_KW):
        return 'computer'

    # Smart TVs / Streaming
    if any(kw in v for kw in _TV_VENDOR_KW):
        return 'tv'

    # Smart speakers / Voice assistants (ambiguous vendors need hostname disambiguation)
    if any(kw in v for kw in _SMART_SPEAKER_VENDOR_KW):
        if any(kw in h for kw in ('echo', 'home', 'nest', 'homepod', 'xiaoai', 'tmall')):
            return 'smart_speaker'
        if 'apple' in v:
            return 'phone'
        return 'smart_speaker'

    # Printers / Scanners
    if any(kw in v for kw in _PRINTER_VENDOR_KW):
        return 'printer'

    # Cameras / Security
    if any(kw in v for kw in _CAMERA_VENDOR_KW):
        return 'camera'

    # IoT / Smart home
    if any(kw in v for kw in _IOT_VENDOR_KW):
        return 'iot'

    # Game consoles
    if any(kw in v for kw in _GAME_CONSOLE_VENDOR_KW):
        return 'game_console'

    # Wearables
    if any(kw in v for kw in _WEARABLE_VENDOR_KW):
        return 'wearable'

    return None
```

- [ ] **Step 2: 提交**

```bash
git add app/domain/services/scanner.py
git commit -m "refactor(scanner): extract _detect_by_vendor method

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

## Task 5: 重构 `guess_device_type` 主入口方法

**Files:**
- Modify: `app/domain/services/scanner.py`

- [ ] **Step 1: 找到旧的 `guess_device_type` 方法（line ~333 起），将其替换为新的简洁版本**

将原有的 291 行方法体替换为：

```python
@staticmethod
def guess_device_type(
    vendor: str, open_ports: list[int], hostname: str | None = None
) -> str:
    """Infer device type from vendor OUI name, open ports, and hostname.

    Detection priority: ports > hostname > vendor.
    """
    if (result := Scanner._detect_by_ports(open_ports)) is not None:
        return result
    if (result := Scanner._detect_by_hostname(hostname)) is not None:
        return result
    if (result := Scanner._detect_by_vendor(vendor, hostname)) is not None:
        return result
    return 'unknown'
```

- [ ] **Step 2: 运行测试验证行为不变**

```bash
uv run pytest tests/test_scanner.py -v
```

预期：3 个测试全部 PASS

- [ ] **Step 3: 提交**

```bash
git add app/domain/services/scanner.py
git commit -m "refactor(scanner): simplify guess_device_type to orchestration-only

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

## Task 6: 全量回归测试

**Files:**
- Test: `tests/` 全部测试套件

- [ ] **Step 1: 运行全部测试**

```bash
uv run pytest tests/ -v
```

预期：全部 63 个测试 PASS

- [ ] **Step 2: 最终提交**

```bash
git add -A
git commit -m "refactor(scanner): complete guess_device_type decomposition

Refactored from 291-line monolithic method into:
- _detect_by_ports(): port-based camera/printer detection
- _detect_by_hostname(): hostname keyword matching for 8 types
- _detect_by_vendor(): vendor OUI-based detection for 11 types
- guess_device_type(): orchestration entry point (priority: ports > hostname > vendor)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

## 自检清单

完成所有任务后，确认：

1. `guess_device_type` 原有 14 种设备类型检测逻辑全部保留
2. 关键词组全部抽取为类级 `tuple`/`frozenset` 常量，无重复字符串字面量
3. `uv run pytest tests/test_scanner.py -v` 全部 PASS
4. `uv run pytest tests/ -v` 全部 63 个测试 PASS
# guess_device_type 重构设计

> 日期: 2026-05-22
> 状态: 已批准
> 关联: code-smell-report-2026-05-22.md

## 目标

将 `app/domain/services/scanner.py` 中 `Scanner.guess_device_type` 巨型静态方法（291 行，14 种设备类型）拆分为 1 个主入口 + 14 个私有检测方法的清晰结构。

## 现状问题

- 291 行巨型静态方法，单一职责过重
- 大量重复 `any(kw in x for kw in (...))` 模式，可读性差
- 端口检测、主机名检测、厂商检测混在同一个方法中

## 拆分方案

### 结构

```
guess_device_type(vendor, ports, hostname)
├── _detect_by_ports() → str | None  (最高优先级)
├── _detect_by_hostname() → str | None  (次优先级)
├── _detect_by_vendor() → str | None  (最低优先级)
└── return 'unknown' if all return None
```

### 实现细节

#### 1. 端口检测 `_detect_by_ports(ports)`

按端口号直接判定：
- 554/2020/8000 → `camera`
- 631/9100/515 → `printer`
- 其他 → `None`

#### 2. 主机名检测 `_detect_by_hostname(h)`

按关键词命中判定 13 种类型：
- phone: `iphone`, `ipad`, `android`, `galaxy`, `redmi`, `pixel`
- computer: `macbook`, `imac`, `desktop`, `laptop`, `pc-`, `workstation`
- printer: `printer`, `canon`, `epson`, `brother`
- tv: `-tv`, `smarttv`, `lgwebos`, `tizen`, `roku`, `fire-tv`, `appletv`, `apple-tv`
- smart_speaker: `echo`, `home-mini`, `nest-`, `homepod`, `xiaoai`
- game_console: `switch`, `playstation`, `xbox`, `ps5`, `ps4`
- tablet: `ipad`, `tab-`, `tablet`, `galaxy-tab`
- camera: `cam`, `ipc`, `nvr`, `dvr`
- 其他 → `None`

#### 3. 厂商检测 `_detect_by_vendor(v, h)`

按厂商 OUI 名称判定，关键词组抽取为类级 `tuple` 常量：

| 设备类型 | 关键词数 | 代表厂商 |
|----------|----------|----------|
| router | 20 | tp-link, netgear, cisco, huawei |
| nas | 3 | synology, qnap, buffalo |
| phone | 17 | apple, samsung, xiaomi, huawei |
| computer | 16 | intel, dell, lenovo, asustek |
| tv | 17 | lg electronics, tcl, roku, chromecast |
| smart_speaker | 9 | sonos, amazon.com, google llc, apple inc |
| printer | 9 | canon, epson, brother, xerox |
| camera | 15 | hikvision, dahua, axis, reolink |
| iot | 33 | espressif, tuya, aqara, broadlink, philips hue |
| game_console | 5 | nintendo, sony interactive, microsoft xbox |
| wearable | 5 | fitbit, garmin, amazfit |

其中 `smart_speaker` 对 Apple/Google/Amazon 等歧义厂商，需结合 hostname 做二次判断。

### 改动范围

- **文件**: `app/domain/services/scanner.py`
- **不新增文件**
- **不改变公开 API**: `Scanner.guess_device_type(...)` 签名和返回值不变
- **测试**: 复用现有测试，确保行为一致

### 新增类级常量（tuple，避免重复字符串）

```python
_PHONE_HOSTNAME_KW: tuple[str, ...] = ('iphone', 'ipad', 'android', ...)
_COMPUTER_HOSTNAME_KW: tuple[str, ...] = ('macbook', 'imac', ...)
# ... 其他设备类型的关键词组
```

## 验收标准

1. `guess_device_type` 拆分后，原有 14 种设备类型的检测逻辑完整保留
2. 所有关键词组抽取为类级常量，消除字符串字面量重复
3. 单元测试 `uv run pytest tests/` 全部通过

# 代码异味检测报告

> 生成日期: 2026-05-22
> 检测范围: `app/` 和 `tests/` 目录下的源代码文件
> 检测规则: 神类/巨型函数、重复代码、过深嵌套、过多参数、隐式状态管理、错误处理不一致、硬编码魔法数字、不合理类型使用

---

## 📊 问题汇总

| 问题类型 | 数量 | 严重程度分布 |
|----------|------|-------------|
| 神类/巨型函数 (>100行) | 5处 | 🔴严重×2, 🟡中等×3 |
| 重复代码 (>80%相似) | 2组 | 🔴严重×2 (完全相同) |
| 过深的嵌套 (>3层) | 6处 | 🟡中等×6 |
| 过多的参数 (>5) | 1处 | 🟡中等×1 |
| 隐式状态管理 | 6处 | 🟡中等×6 |
| 错误处理不一致 | 5处 | 🟡中等×5 |
| 硬编码的魔法数字 | 11处 | 🔴严重×3, 🟡中等×8 |
| 不合理的类型使用 | 4处 | 🟡中等×4 |

**总计: 38 处问题**

---

## 🔴 严重问题 (需优先修复)

### 1. 重复代码 - scanner.py 双重重复

| 项目 | 详情 |
|------|------|
| 文件 | `app/services/scanner.py` 与 `app/domain/services/scanner.py` |
| 行数 | 约620行/文件 |
| 相似度 | 100% 完全相同 |
| 问题 | 两份完全相同的代码，包含295行的 `guess_device_type` 巨型函数 |

**建议**: 删除 `app/services/scanner.py`，统一使用 `app/domain/services/scanner.py`

---

### 2. 重复代码 - dlna_service.py 重复

| 项目 | 详情 |
|------|------|
| 文件 | `app/services/dlna_service.py` 与 `app/domain/services/dlna_service.py` |
| 行数 | 约184行/文件 |
| 相似度 | 100% 完全相同 |

**建议**: 删除 `app/domain/services/dlna_service.py`，统一使用 `app/services/dlna_service.py`

---

### 3. 神类/巨型函数 - guess_device_type

| 项目 | 详情 |
|------|------|
| 文件 | `app/domain/services/scanner.py` 或 `app/services/scanner.py` |
| 行号 | 328-623 |
| 行数 | 295行 |
| 问题 | 单个函数承担过多设备类型检测逻辑，包含大量重复的 `any(kw in v for kw in (...))` 模式 |

**建议修复方向**:
- 按检测维度拆分为: `_detect_by_ports()`, `_detect_by_hostname()`, `_detect_by_vendor()`, `_detect_by_manufacturer()`
- 或按设备类型拆分为: `_detect_camera()`, `_detect_recorder()`, `_detect_dlna_device()` 等

---

### 4. 硬编码魔法数字 - config.py

| 文件 | 行号 | 代码 | 问题 |
|------|------|------|------|
| `app/config.py` | 88 | `recording_segment_seconds: int = 1800` | 30分钟无注释说明 |
| `app/config.py` | 89 | `recording_retention_days: int = 30` | 保留天数无注释说明 |

**建议**: 定义为具名常量并添加文档注释:
```python
# 录制分段时长: 30分钟
RECORDING_SEGMENT_SECONDS: int = 1800
# 录制文件保留天数
RECORDING_RETENTION_DAYS: int = 30
```

---

### 5. 硬编码魔法数字 - presence_service.py ping命令

| 文件 | 行号 | 代码 | 问题 |
|------|------|------|------|
| `app/services/presence_service.py` | 236-248 | `ping -n 1 -w 1000` (Windows), `ping -c 1 -W 1` (Linux) | ping超时硬编码，无常量定义 |

**建议**: 定义为 `PING_TIMEOUT_SECONDS = 1` 常量

---

### 6. 硬编码魔法数字 - recorder.py 流中断判断

| 文件 | 行号 | 代码 | 问题 |
|------|------|------|------|
| `app/domain/services/recorder.py` | 204-206 | `if elapsed >= 90 and grew == 0` | 90秒流中断判断阈值无注释 |

**建议**: 定义为 `STALL_THRESHOLD_SECONDS = 90` 并添加注释说明

---

## 🟡 中等问题

### 神类/巨型函数

| 文件 | 行号 | 行数 | 问题描述 |
|------|------|------|----------|
| `app/main.py` | 80-205 | ~125 | `lifespan` 异步上下文管理器承担启动初始化、恢复调度、启动服务、设置回调等多项职责 |
| `app/domain/services/scanner.py` | 728-829 | ~100 | `_run_scan` 函数包含扫描→丰富→upsert→标记离线→分析等多阶段逻辑 |

**建议**: `main.py:lifespan` 拆分为 `_restore_schedules()`, `_start_services()`, `_cleanup_on_shutdown()` 等独立函数

---

### 过深的嵌套 (>3层)

| 文件 | 行号 | 嵌套层级 | 问题描述 |
|------|------|----------|----------|
| `app/api/cameras.py` | 297-363 | 4层 | `_mjpeg_generate` 内 `while True` 循环嵌套 |
| `app/api/cameras.py` | 432-505 | 4层 | `start_live` 函数内 for + if 多层嵌套 |
| `app/api/recordings.py` | 168-253 | 3层 | `stream_recording` 内 range 处理逻辑 |
| `app/api/recordings.py` | 87-106 | 3层 | `list_recordings` 中 `for r in items` 内嵌多层条件 |
| `app/main.py` | 69-77 | 多层 | `presence_service._poll_interval` 赋值被多层嵌套包裹 |

---

### 过多的参数

| 文件 | 行号 | 参数数量 | 参数列表 |
|------|------|----------|----------|
| `app/services/nas_syncer.py` | 9-18 | 7个 | `mode, mount_path, local_storage_path, smb_host, smb_share, smb_user, smb_password` |

**建议**: 封装为 `NasConfig` 数据类

---

### 隐式状态管理

| 文件 | 类型 | 问题描述 |
|------|------|----------|
| `app/api/system.py` | 模块级变量 | `_start_time`, `_ffmpeg_available` 全局状态 |
| `app/api/cameras.py` | 模块级变量 | `_live_procs`, `_HLS_BASE` 被多处读写 |
| `app/services/ws_manager.py` | 全局单例 | `ws_manager` 全局单例直接修改 `_connections` |
| `app/services/presence_service.py` | 全局单例 | `presence_service` 全局单例被 `main.py:188` 直接修改 `_poll_interval` |
| `app/services/scheduler_service.py` | 全局单例 | `scheduler_service` 全局单例 |

**建议**: 通过依赖注入或 `request.app.state` 传递服务实例

---

### 错误处理不一致

| 文件 | 行号 | 问题描述 |
|------|------|----------|
| `app/services/ws_manager.py` | 37-38 | `broadcast` 中 `except Exception: stale.append(ws)` 静默吞掉所有异常，无日志 |
| `app/services/presence_service.py` | 165 | `_check_member` 捕获宽泛 `Exception` 无具体分类，静默失败 |
| `app/services/presence_service.py` | 249 | `_ping_ip` 使用 `except (TimeoutError, Exception):` 混搭捕获 |
| `app/domain/services/recording_domain.py` | 105-177 | `on_recording_failed` 中同时存在 try-except 和无保护直接访问 |
| `app/main.py` | 81-84 | `init_db()` 内部迁移使用 `try-except pass` 静默吞掉 ALTER TABLE 错误 |

---

### 硬编码的魔法数字 (中等)

| 文件 | 行号 | 代码 | 问题 |
|------|------|------|------|
| `app/api/dlna.py` | 47-48 | `MAX_UPLOAD_BYTES = 500 * 1024 * 1024`, `MEDIA_TTL_SECONDS = 3600` | 无注释 |
| `app/domain/services/recording_domain.py` | 218 | `await asyncio.sleep(3600)` | 1小时无注释 |
| `app/api/recordings.py` | 195 | `if file_size < 10 * 1024` | 文件最小大小无常量 |
| `app/api/recordings.py` | 201 | `range_header[len('bytes='):]` | 字符串长度硬编码 |
| `app/config.py` | 71 | `server_port: int = 8000` | 虽有注释但可强化为显式常量 |
| `app/domain/services/recording_domain.py` | 179-216 | 多处 `time.time()` 和 `server_port` 组合 | 媒体URL构造硬编码 |
| `app/domain/services/scanner.py` | 289-291 | `_PROBE_PORTS = [554, 2020, 8000, 80, 8080, 443, 8443]` | 端口号无注释 |

---

### 不合理的类型使用

| 文件 | 行号 | 问题描述 |
|------|------|----------|
| `app/services/presence_service.py` | 84 | `snapshots = [{'id': m.id, 'name': m.name, 'is_home': m.is_home} for m in members]` 返回 `list[dict]` 应使用 TypedDict |
| `app/services/presence_service.py` | 106 | `device_data: list[tuple[str, str]]` 使用无名称 tuple，应使用 NamedTuple |
| `app/api/members.py` | 89-99 | 列表推导内嵌套字典构造，类型不明确 |
| `app/api/analytics.py` | 191 | `pivot: dict[int, dict[str, float]]` 内层 dict 使用魔数字符串 key，应定义 TypedDict |

---

## 📋 完整问题表格

| 严重度 | 文件 | 行号 | 问题类型 | 具体描述 | 建议修复方向 |
|--------|------|------|----------|----------|--------------|
| 🔴严重 | app/services/scanner.py | 全文 | 重复代码 | 与 domain/services/scanner.py 完全相同(约620行) | 删除 services/scanner.py |
| 🔴严重 | app/domain/services/dlna_service.py | 全文 | 重复代码 | 与 services/dlna_service.py 完全相同(约184行) | 删除 domain/services/dlna_service.py |
| 🔴严重 | app/services/scanner.py | 328-623 | 神类/巨型函数 | `guess_device_type` 295行，包含大量重复模式 | 按检测维度拆分 |
| 🔴严重 | app/config.py | 88-89 | 硬编码魔法数字 | `1800`(30分钟), `30`(天数) 无注释 | 定义具名常量 |
| 🔴严重 | app/services/presence_service.py | 236-248 | 硬编码魔法数字 | ping命令超时硬编码 | 定义 PING_TIMEOUT_SECONDS |
| 🔴严重 | app/domain/services/recorder.py | 204-206 | 硬编码魔法数字 | `90` 秒流中断判断阈值无注释 | 定义 STALL_THRESHOLD_SECONDS |
| 🟡中等 | app/main.py | 80-205 | 神类/巨型函数 | `lifespan` 125行多职责 | 拆分为独立函数 |
| 🟡中等 | app/domain/services/scanner.py | 728-829 | 神类/巨型函数 | `_run_scan` 100行多阶段逻辑 | 拆分各阶段为独立函数 |
| 🟡中等 | app/api/cameras.py | 297-363 | 过深嵌套 | 4层 `while True` 嵌套 | 提取 `_read_frame()` |
| 🟡中等 | app/api/cameras.py | 432-505 | 过深嵌套 | 4层 for + if 嵌套 | 提取清理逻辑 |
| 🟡中等 | app/api/recordings.py | 168-253 | 过深嵌套 | 3层 range 处理 | 提取 `_parse_range_header()` |
| 🟡中等 | app/api/recordings.py | 87-106 | 过深嵌套 | 3层 for + if 嵌套 | 提取 `_to_recording_out()` |
| 🟡中等 | app/services/nas_syncer.py | 9-18 | 过多参数 | 7个参数 | 封装为 NasConfig |
| 🟡中等 | app/api/system.py | 20-21 | 隐式状态管理 | 模块级全局变量 | 使用类或上下文封装 |
| 🟡中等 | app/api/cameras.py | 33-34 | 隐式状态管理 | 模块级 `_live_procs`, `_HLS_BASE` | 封装为 LiveStreamManager |
| 🟡中等 | app/services/ws_manager.py | 全局 | 隐式状态管理 | 全局单例 `_connections` | 通过依赖注入使用 |
| 🟡中等 | app/services/presence_service.py | 全局 | 隐式状态管理 | 全局单例 `_poll_interval` 被直接修改 | 通过 app.state 传递配置 |
| 🟡中等 | app/services/ws_manager.py | 37-38 | 错误处理不一致 | 静默吞掉所有异常 | 添加日志记录 |
| 🟡中等 | app/services/presence_service.py | 165 | 错误处理不一致 | 宽泛 Exception 捕获静默失败 | 区分异常类型 |
| 🟡中等 | app/services/presence_service.py | 249 | 错误处理不一致 | `except (TimeoutError, Exception)` 混搭 | 移除冗余 |
| 🟡中等 | app/domain/services/recording_domain.py | 105-177 | 错误处理不一致 | try-except 和无保护访问混用 | 统一异常处理 |
| 🟡中等 | app/main.py | 81-84 | 错误处理不一致 | `try-except pass` 静默吞掉迁移错误 | 添加日志或使用 alembic |
| 🟡中等 | app/api/dlna.py | 47-48 | 硬编码魔法数字 | 500MB, 3600秒无注释 | 添加注释说明 |
| 🟡中等 | app/domain/services/recording_domain.py | 218 | 硬编码魔法数字 | `3600` 秒无注释 | 定义常量 |
| 🟡中等 | app/api/recordings.py | 195 | 硬编码魔法数字 | `10 * 1024` 文件最小大小 | 定义常量 |
| 🟡中等 | app/domain/services/recording_domain.py | 179-216 | 硬编码魔法数字 | 媒体URL构造多处硬编码 | 封装 `_build_media_url()` |
| 🟡中等 | app/domain/services/scanner.py | 289-291 | 硬编码魔法数字 | 端口号列表无注释 | 添加注释 |
| 🟡中等 | app/services/presence_service.py | 84 | 不合理类型使用 | `list[dict]` 类型不明确 | 定义 TypedDict |
| 🟡中等 | app/services/presence_service.py | 106 | 不合理类型使用 | 无名称 tuple | 改为 NamedTuple |
| 🟡中等 | app/api/members.py | 89-99 | 不合理类型使用 | 类型不明确 | 定义 Pydantic 模型 |
| 🟡中等 | app/api/analytics.py | 191 | 不合理类型使用 | dict key 字符串无定义 | 定义 TypedDict |

---

## ✅ 审核清单

- [ ] 确认是否同意将 `services/` 下的 scanner.py 和 dlna_service.py 标记为待删除
- [ ] 确认 `guess_device_type` 的拆分方案（按维度 vs 按设备类型）
- [ ] 确认硬编码数字的修复优先级
- [ ] 确认全局单例状态管理的重构方向

---

*报告生成工具: Claude Code 代码异味扫描*

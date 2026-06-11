# Lumos Home 智能家庭控制中心 2.0 — 设计文档

> **日期**: 2026-06-11
> **状态**: Draft（待用户审阅）
> **作者**: Claude (brainstorming 流程产出)
> **基线**: 当前代码库已实现设备扫描、录制调度、DLNA、成员到家/离家联动（Phase A）、Frigate MQTT 桥接、`ws_manager` WebSocket 推送、Analytics API
> **目标**: 把 Lumos Home 从「设备 / 录像管理后台」升级为「事件驱动的智能家庭控制中心」
> **关联**: `docs/smart_home_tool_design_v3.md`、`backend/docs/superpowers/specs/2026-04-29-smart-home-features-design.md`、`docs/go2rtc-live-streaming-plan.md`、`docs/frigate_borrowing_execution_plan.md`

---

## 0. 概览 (One-liner)

Lumos Home 引入**事件驱动的智能化基座**:
- **大脑** = Automation Engine：规则 + 触发器 + 条件 + 动作
- **触手** = Notification Center：邮件 + Webhook，聚合去噪
- **脸面** = Digital Twin：three.js 3D 户型，实时反映自动化结果

**一次完整交付**；代码层面按 PR 顺序分阶段合入。

### 0.1 现状与差距

| 已有能力 | 缺口 |
|---|---|
| `ws_manager.broadcast()` 推送 15+ 种 WS 事件（`camera_offline`、`recording_completed` 等） | 模块间无统一事件总线；规则无法由用户配置 |
| Phase A 硬编码联动（成员到家自动录制、陌生设备告警、摄像头掉线、录制后投屏） | 逻辑散落在各 service，不可视化、不可禁用单条规则 |
| 前端 `notifications.js` store + Element Plus Toast | 无持久化通知历史、无渠道配置、无模板 |
| FrigateBridge → `CameraEvent` 表 | 未发布到 Event Bus，Automation Engine 无法订阅 |
| Analytics API + `HeatmapChart.vue`（2D） | 无 3D 空间绑定、无设备位置可视化 |

本期在**不破坏既有行为**的前提下叠加规则引擎与通知中心；Phase A 硬编码逻辑保留，逐步提供等价的可配置规则作为迁移路径（见 §5.7）。

---

## 1. 架构总览

```
┌────────────────────────────────────────────────────────────────────┐
│                       Browser (Vue 3 SPA)                           │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────────────┐    │
│  │ Automations │ │  Digital     │ │  Notification Center       │    │
│  │ View        │ │  Twin View   │ │  (Bell icon + drawer)      │    │
│  │ (规则编辑)   │ │  (three.js)  │ │                            │    │
│  └──────┬──────┘ └──────┬───────┘ └────────────┬───────────────┘    │
│         └────────────────┴─────────────────────┘                    │
│              REST API + WebSocket  /api/v1/*                        │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│                      FastAPI Backend                                 │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ Automation Engine  (B2 - 大脑)                            │      │
│  │   ┌──────────┐  ┌──────────┐  ┌────────────────────┐     │      │
│  │   │Trigger   │→│Condition │→│ Actions[]           │     │      │
│  │   │Manager   │  │Evaluator │  │  - SendNotification │     │      │
│  │   └──────────┘  └──────────┘  │  - ControlDevice    │     │      │
│  │                              │  - StartRecording   │     │      │
│  │                              │  - Webhook          │     │      │
│  │                              └────────────────────┘     │      │
│  └──────────────────────────────────────────────────────────┘      │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────┐      │
│  │ Notification Center  (B1 - 触手)                          │      │
│  │   ChannelRegistry: Email / Webhook / (Mobile预留)         │      │
│  │   TemplateEngine(占位符 {{device.name}} {{event.time}})    │      │
│  │   AntiSpam: 规则级去重 + 全局静默时段 + 聚类折叠           │      │
│  └──────────────────────────────────────────────────────────┘      │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────┐      │
│  │ Event Bus  (内部轻量 pub/sub,内存实现,Future 留 Redis)    │      │
│  │   Topics: camera_offline, recording_completed,            │      │
│  │           motion.detect, rule.fired, notification.sent  │      │
│  └──────────────────────────────────────────────────────────┘      │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────┐      │
│  │ WebSocket Broadcaster  (推送给前端)                        │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  既有: Scanner / Camera / Recorder / Topology / DLNA / Auth       │
└────────────────────────────────────────────────────────────────────┘
```

**关键设计点**:
1. **Event Bus 内部使用，不上 Redis**：够用，后期可替换（为 LLM 管家等铺路）
2. **Actions 是后端抽象，内置实现 ≥4 种**：通知、设备控制、录制、Webhook
3. **前端不直接订阅数据库，统一通过 WebSocket 接收事件**：保持单向流
4. **复用既有 `ws_manager`**：Event Bus 与 WebSocket 通过桥接层联通，不替换现有推送机制

### 1.1 Event Bus 桥接（与既有 `ws_manager` 的关系）

现有各 service 直接调用 `ws_manager.broadcast(event, data)`。本期**不改动**这些调用点，而是在 `ws_manager.broadcast()` 内增加可选钩子：

```python
# ws_manager.broadcast() 伪代码
async def broadcast(self, event: str, data: dict):
    # 1. 保持既有 WS 推送格式不变
    message = {"event": event, "timestamp": ..., "data": data}
    await self._send_to_all_connections(message)
    # 2. 同步发布到内部 Event Bus（topic 与 event 名一致）
    await event_bus.publish(event, data)
```

Automation Engine 的 `EventTrigger` 订阅 Event Bus；Digital Twin 和 Notification Center 继续消费既有 WS 格式，无需改动前端协议。

### 1.2 事件目录（Event Catalog）

Event Bus topic 与既有 WS `event` 字段**同名**，避免两套命名：

| Topic / WS event | 发布者 | 典型 payload 字段 |
|---|---|---|
| `scan_completed` | `scanner/pipeline.py` | `online`, `offline`, `new` |
| `unknown_device_detected` | `scanner/pipeline.py` | `mac`, `ip`, `hostname` |
| `camera_online` / `camera_offline` | `camera_health.py` | `mac` |
| `member_arrived` / `member_left` | `presence_service.py` | `member_id`, `name` |
| `recording_started` / `recording_completed` / `recording_failed` | `recording_domain.py` | `camera_mac`, … |
| `motion.detect` | `frigate_bridge.py`（**新增发布**） | `camera_mac`, `label`, `score` |
| `rule.fired` | Automation Engine（**新增**） | `rule_id`, `rule_name` |
| `notification.sent` / `notification.failed` | Notification Center（**新增**） | `channel_id`, `severity` |

> **注意**：文档早期草稿中的 `device.online` / `recording.start` 为概念名，实现统一采用上表中的既有事件名。`motion.detect` 在 FrigateBridge 写入 `CameraEvent` 后额外 `event_bus.publish()`。

---

## 2. 后端核心:Automation Engine

### 2.1 核心抽象

```python
from typing import ClassVar, Protocol
from dataclasses import dataclass

# 触发器:何时激活规则
class Trigger(Protocol):
    async def evaluate(self, ctx: TriggerContext) -> bool: ...
    async def start(self): ...  # 订阅事件源
    async def stop(self): ...

# 条件:触发后是否执行
class Condition(Protocol):
    async def check(self, ctx: RuleContext) -> bool: ...

# 动作:执行什么 — type 由具体子类声明,Registry 用它来反序列化 ActionSpec
class Action(Protocol):
    type: ClassVar[str]  # 子类必须声明,例如 "send_notification" / "control_device"
    async def execute(self, ctx: RuleContext) -> ActionResult: ...

# 规则:把三者串起来
@dataclass
class Rule:
    id: UUID
    name: str
    enabled: bool
    trigger: TriggerSpec       # JSON 配置
    conditions: list[ConditionSpec]
    actions: list[ActionSpec]
    cooldown_seconds: int = 60  # 防止风暴
    created_at, updated_at
```

### 2.2 内置 Trigger 类型

| 类型 | 配置 | 触发时机 |
|---|---|---|
| `cron` | `{ "expr": "0 22 * * *" }` | APScheduler 定时（与既有 `schedules` 模块共用 scheduler 实例，但规则独立存储于 `automation_rules` 表） |
| `device_event` | `{ "topic": "camera_online" \| "camera_offline" \| "unknown_device_detected", "filter": {"device_type":"camera"} }` | Event Bus 收到对应 topic |
| `recording_event` | `{ "topic": "recording_started" \| "recording_completed" \| "recording_failed", "filter": {"camera_mac":"..."} }` | 同上 |
| `presence_event` | `{ "topic": "member_arrived" \| "member_left", "filter": {"member_id":"..."} }` | 同上 |
| `motion_event` | `{ "camera_mac": "...", "labels": ["person","motion"], "min_confidence": 0.7 }` | FrigateBridge 发布 `motion.detect` 后触发 |
| `manual` | (无配置) | 仅 API 触发，用作测试按钮 |

### 2.2.1 内置 Condition 类型

| 类型 | 配置 | 行为 |
|---|---|---|
| `time_window` | `{ "start": "22:00", "end": "07:00", "timezone": "Asia/Shanghai" }` | 仅在时段内执行（支持跨午夜） |
| `device_state` | `{ "device_mac": "AA:BB:...", "field": "is_online", "op": "eq", "value": true }` | 触发时查 DB 快照 |
| `event_field` | `{ "path": "label", "op": "in", "value": ["person","car"] }` | 对 trigger payload 做 JSONPath 过滤 |
| `and` / `or` | `{ "conditions": [...] }` | 组合嵌套，最大深度 3 |

所有 Condition 默认**空列表 = 恒真**（触发即执行）。

### 2.3 内置 Action 类型

| 类型 | 配置示例 | 副作用 |
|---|---|---|
| `send_notification` | `{ "channel_id": "...", "template": "..." }` | 走 Notification Center |
| `control_device` | `{ "device_mac": "AA:BB:...", "command": {...} }` | 调 DeviceService（若设备支持；与既有 API 一致用 MAC 标识） |
| `start_recording` | `{ "camera_id": "...", "duration_minutes": 30 }` | 调 Recorder |
| `webhook` | `{ "url": "...", "method": "POST", "body": "..." }` | HTTP 出站 |
| `chain_rule` | `{ "rule_id": "..." }` | 触发另一条规则（级联，最大深度 3，Engine 检测环并拒绝执行） |

### 2.4 持久化（新增 SQLite 表，共 8 张）

```sql
CREATE TABLE automation_rules (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT,
    enabled       BOOLEAN NOT NULL DEFAULT 1,
    trigger_spec  TEXT NOT NULL,    -- JSON
    conditions    TEXT NOT NULL DEFAULT '[]',  -- JSON
    actions       TEXT NOT NULL,    -- JSON
    cooldown_seconds INTEGER NOT NULL DEFAULT 60,
    last_fired_at TIMESTAMP,
    created_at    TIMESTAMP NOT NULL,
    updated_at    TIMESTAMP NOT NULL
);

CREATE TABLE rule_executions (       -- 审计日志
    id            TEXT PRIMARY KEY,
    rule_id       TEXT NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    fired_at      TIMESTAMP NOT NULL,
    trigger_data  TEXT,              -- JSON
    action_results TEXT,             -- JSON array
    success       BOOLEAN,
    error         TEXT
);
CREATE INDEX idx_rule_exec_rule_time ON rule_executions(rule_id, fired_at DESC);
```

### 2.5 调度与并发

- `RuleRegistry` 启动时从 DB 加载所有 enabled 规则,根据 `trigger.type` 分发到对应适配器
- `CronTrigger` 用 **APScheduler 3.10.x**(项目已选,与既有 Schedule 模块共用,JobStore 用 SQLAlchemyJobStore 持久化到 SQLite)
- `EventTrigger` 订阅 Event Bus,filter 在收到事件时同步评估(内存轻量)
- **Event Bus 投递语义:at-least-once**。同一事件可能因发布者重试被处理多次,所有 Trigger/Action 实现必须幂等,配合 `cooldown_seconds` 抑制重复副作用
- **单规则执行串行**;不同规则并行;`cooldown_seconds` 抑制同一规则短时间重复触发
- 失败 Action 单独记录,不影响其他 Action(`gather` 语义)

### 2.6 REST API

```
GET    /api/v1/automations                          # 列表（分页）
POST   /api/v1/automations                          # 创建
GET    /api/v1/automations/{id}                     # 详情
PATCH  /api/v1/automations/{id}                     # 更新
DELETE /api/v1/automations/{id}                     # 删除
POST   /api/v1/automations/{id}/test                # 手动触发（模拟），用于调试
GET    /api/v1/automations/{id}/executions          # 执行历史
GET    /api/v1/automations/triggers                 # 可用 trigger 列表（元数据，前端表单用）
GET    /api/v1/automations/actions                  # 可用 action 列表
GET    /api/v1/automations/conditions               # 可用 condition 列表
POST   /api/v1/automations/inbound                  # 外部 webhook 入站（Frigate HTTP 等，见 §2.6.1）
```

#### 2.6.1 入站 Webhook（`/automations/inbound`）

供无法走 MQTT 的外部系统（或测试）推送事件到 Event Bus：

- 鉴权：`X-Lumos-Token` header，值来自环境变量 `AUTOMATION_INBOUND_TOKEN`（可选，未配置则禁用此端点）
- Body：`{ "topic": "motion.detect", "payload": { ... } }`
- 行为：校验 topic 白名单 → `event_bus.publish()` → 202 Accepted
- Frigate **首选路径**仍是既有 `FrigateBridgeService`（MQTT）；入站端点作为补充，不替代桥接

### 2.7 测试策略(TDD 强制)

- 单元:每个 Trigger / Condition / Action 单独覆盖(用 mock event bus)
- 集成:`test_automations.py` 覆盖端到端"事件 → 触发 → 条件 → 动作 → 副作用"
- 关键 fixture:内存 SQLite + 假 Event Bus + HTTPX AsyncClient

---

## 3. Notification Center

### 3.1 渠道适配器(Channel)

```python
class NotificationChannel(Protocol):
    type: str  # "email" | "webhook"
    async def send(self, payload: RenderedNotification) -> SendResult: ...

@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    username: str
    password: SecretStr
    from_addr: EmailStr
    to_addrs: list[EmailStr]
    use_tls: bool = True

@dataclass
class WebhookConfig:
    url: HttpUrl
    method: Literal["GET", "POST", "PUT"] = "POST"
    headers: dict[str, str] = {}
    body_template: str  # 支持 Jinja2 模板
    timeout_seconds: int = 10
```

### 3.2 模板引擎

- **Jinja2**(`jinja2` 包,小型,无依赖问题)
- 上下文变量:
  - `event.type`, `event.timestamp`
  - `event.payload`(原事件数据)
  - `device.name`, `device.ip`, `device.type`
  - `rule.name`
- 邮件 Subject / Body / Webhook Body 各自独立模板
- 模板可保存到 `notification_templates` 表(命名 + 内容),复用

### 3.3 反骚扰(Anti-Spam)

| 机制 | 行为 |
|---|---|
| 规则 cooldown | 同一规则 N 秒内不重复触发(已在 Rule 层实现) |
| 全局静默时段 | `notification_settings` 表的 `quiet_hours_start/end`；静默期间只入队不发，早晨批量推送摘要 |
| 聚类折叠 | 同类型事件 5 分钟内 ≥3 条 → 合并为"摄像头 X 离线 3 次" |
| 严重程度 | 每条通知有 `severity: info / warning / critical`,critical 必发,warning 看时段,info 默认聚合 |
| 失败重试 | 渠道发送失败按指数退避重试 3 次（1s / 5s / 30s），仍失败将 `notification_log.status` 标为 `dead_letter` |

### 3.4 持久化(新增表)

```sql
CREATE TABLE notification_channels (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,         -- 'email' | 'webhook'
    config      TEXT NOT NULL,         -- JSON,加密存储敏感字段
    enabled     BOOLEAN NOT NULL DEFAULT 1,
    created_at, updated_at
);

CREATE TABLE notification_templates (
    id      TEXT PRIMARY KEY,
    name    TEXT UNIQUE NOT NULL,
    subject TEXT,
    body    TEXT NOT NULL            -- Jinja2
);

CREATE TABLE notification_log (        -- 发送历史
    id           TEXT PRIMARY KEY,
    channel_id   TEXT REFERENCES notification_channels(id) ON DELETE SET NULL,
    rule_id      TEXT REFERENCES automation_rules(id) ON DELETE SET NULL,
    severity     TEXT NOT NULL,
    subject      TEXT,
    body         TEXT,
    status       TEXT NOT NULL,        -- 'pending' | 'sent' | 'failed' | 'dead_letter'
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT,
    sent_at      TIMESTAMP,
    created_at   TIMESTAMP NOT NULL
);
CREATE INDEX idx_notif_log_created ON notification_log(created_at DESC);
CREATE INDEX idx_notif_log_status ON notification_log(status);

CREATE TABLE notification_settings (     -- 单行全局配置
    id                  INTEGER PRIMARY KEY DEFAULT 1,
    quiet_hours_start   TEXT,              -- "22:00" 或 NULL=不启用
    quiet_hours_end     TEXT,              -- "07:00"
    quiet_hours_tz      TEXT NOT NULL DEFAULT 'Asia/Shanghai',
    morning_digest_enabled BOOLEAN NOT NULL DEFAULT 1,
    updated_at          TIMESTAMP NOT NULL
);
```

### 3.5 加密

- 渠道配置中的敏感字段（`password`、`api_key`）用 **Fernet（AES-128-CBC + HMAC）**
- 主密钥：新增 `LUMOS_SECRET_KEY`（≥32 字符，与 `JWT_SECRET_KEY` 职责分离——JWT 签名 vs 配置加密）
- `.env.example` 增加占位；启动时校验格式，与 `JWT_SECRET_KEY` 校验逻辑一致

### 3.6 REST API

```
GET    /api/v1/notifications/channels
POST   /api/v1/notifications/channels
PATCH  /api/v1/notifications/channels/{id}
DELETE /api/v1/notifications/channels/{id}
POST   /api/v1/notifications/channels/{id}/test   # 发测试消息

GET    /api/v1/notifications/templates
POST   /api/v1/notifications/templates
PATCH  /api/v1/notifications/templates/{id}
DELETE /api/v1/notifications/templates/{id}

GET    /api/v1/notifications/log         # 历史(分页 + severity/status 过滤)
GET    /api/v1/notifications/settings    # 静默时段等全局配置
PATCH  /api/v1/notifications/settings
```

### 3.7 WebSocket 推送

新增 WS event：`notification.sent`、`notification.failed`（格式与既有 `{event, timestamp, data}` 一致）。

前端在**既有** `notifications.js` store 上扩展：
- 保留现有 WS 事件处理（`camera_offline`、`scan_completed` 等）和 `useNotificationPreferences` 开关
- 新增 `serverNotifications` 列表（来自 `notification_log` API）与未读计数
- `NotificationCenter.vue`（铃铛 + Drawer）与 Toast 并存，不替换现有即时 Toast 行为

### 3.8 测试

- 每个渠道适配器:用本地 SMTP catch-all(`aiosmtpd`)和 mock HTTP server
- 模板渲染:覆盖变量、空值、HTML 转义
- 反骚扰:fast-forward 时间,验证静默/聚类
- 重试:模拟连续失败,验证退避和 dead letter

---

## 4. 3D 数字孪生(Digital Twin)

### 4.1 技术栈与选型

- **three.js**(用户已选)+ **Vue 3 SFC 包装**(`<script setup>` + `<canvas>`)
- 不引入 `tres`(避免 binding 库对 three.js 升级的滞后,直用更可控)
- **GLSL 着色器**:活动热力图用 fragment shader 烘焙到地面/墙体纹理
- **GLTF 加载器**:支持用户上传 .glb / .gltf 户型模型
- 简化版支持:**无 GLTF 时,自动用平面图 SVG 拉伸成低多边形几何体**(地板+4 面墙+门窗)
- 性能兜底:OrbitControls + `frameloop="demand"`,空闲时停帧

### 4.2 数据模型

```sql
CREATE TABLE digital_twins (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    gltf_url    TEXT,                  -- 用户上传的模型路径
    floorplan_svg TEXT,                -- 兜底:平面图 SVG
    rooms       TEXT NOT NULL,         -- JSON:[{id, name, polygon, center}]
    created_at, updated_at
);

CREATE TABLE twin_device_bindings (   -- 设备在 3D 空间的位置
    id           TEXT PRIMARY KEY,
    twin_id      TEXT NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    device_mac   TEXT NOT NULL REFERENCES devices(mac) ON DELETE CASCADE,
    position_x   REAL NOT NULL,
    position_y   REAL NOT NULL,         -- 在房间内的归一化坐标 (0–1)
    position_z   REAL NOT NULL,
    icon_type    TEXT,                  -- 设备类型图标
    UNIQUE(twin_id, device_mac)
);
```

### 4.3 实时数据绑定

- 前端订阅既有 WebSocket（`/api/v1/ws`），按 `msg.event` 过滤：
  - `camera_online` / `camera_offline` → 改变对应 3D 设备图标颜色（绿/灰）
  - `motion.detect`（FrigateBridge 新增发布）→ 在摄像头 binding 位置播放粒子环
  - `rule.fired` → 短暂高亮被控设备（脉冲动画）
- 离线状态：WebSocket 断线重连后，主动 `GET /api/v1/devices` 拉一次快照
- 用 `pinia` 缓存 twin state，组件只做渲染，不直接操作 three.js 场景外的状态

### 4.4 视图与交互

```
/twins                              # Twin 列表(管理多个户型,例如家/办公室)
  /twins/:id                        # 3D 主视图
    - 左:3D 画布(75%)
    - 右:抽屉(设备列表 + 属性面板)
    - 顶栏:模式切换 = 实时模式 / 编辑模式
```

**实时模式**:
- 鼠标悬浮设备 → 显示设备名/IP/状态
- 点击设备 → 跳转 `/devices/:id` 详情
- 顶栏快速过滤:只看离线设备 / 只看摄像头

**编辑模式**:
- 拖拽设备图标到 3D 空间 → 保存 binding
- 上传/删除户型模型
- 切换楼层(支持多层:z 轴偏移)
- 时间滑块：回看过去 24h 的热力图（数据从 `GET /api/v1/camera-events?event_type=external_frigate&since=24h` 取 Frigate 事件，经 `twin_device_bindings` 将 `camera_mac` 映射为 3D xz 坐标；若 P9 需要聚合接口，可新增 `GET /api/v1/analytics/motion-heatmap` 薄封装）

### 4.5 热力图实现

- 房间地面 plane,自定义 `ShaderMaterial`:
  - uniform `uPoints`:vec3 array(过去 24h 所有 motion.detect 事件的 xz 坐标)
  - uniform `uTime`:float(回放进度)
  - fragment:每个点计算到 fragment 的距离 × 高斯衰减 × 时间窗口激活度 → RGB 强度
- 性能:points 数量上限 1000,超过则下采样
- 关闭热力图时把 shader 切回普通漫反射(零开销)

### 4.6 路由与菜单

- 路由:`/twins` 和 `/twins/:id`
- 入口:**Dashboard 顶部加 "3D 视图" 按钮**跳转(主入口),`SettingsView` 顶部加次级链接(管理多个 Twin 户型)
- 不放在侧边栏一级菜单 — Twin 是 Dashboard 的升级版,不是日常功能

### 4.7 测试

- 单元:数据归一化、坐标转换、WebSocket 事件分发纯函数
- 组件:`DigitalTwinCanvas.test.js` 验证 props 变化时场景正确更新
- 视觉(可选):Playwright 截图 + 像素 diff 阈值,只在关键改动时跑

---

## 5. 数据流 & 错误处理 & 测试

### 5.1 端到端数据流(以"摄像头检测到运动 → 通知 + 高亮 3D 摄像头"为例)

```
[Frigate MQTT] --> FrigateBridgeService --> CameraEvent 表
                         │
                         ▼
              Event Bus.publish("motion.detect", payload)
              （FrigateBridge 新增；HTTP inbound 为可选补充路径）
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
   Engine.EventTrigger      Engine.EventTrigger       WS Broadcaster
   (规则 A: 陌生运动)         (规则 B: 全记录)         (topic=motion.detect)
              │                        │                        │
              ▼                        ▼                        ▼
     Condition:陌生人?        Action: start_recording        前端 3D 视图
              │                        │                    粒子环动画
              ▼                        ▼
     Action: send_notification   Action: 控制灯(可选)
              │
              ▼
     NotificationCenter
              │
     ┌────────┴────────┐
     ▼                 ▼
  Email 渠道       Webhook 渠道
     │                 │
     ▼                 ▼
  SMTP send       HTTP POST
     │                 │
     └────────┬────────┘
              ▼
     notification_log (success/failed)
              │
              ▼
     Event Bus.publish("notification.sent", ...)
              │
              ▼
     WS Broadcaster → 前端铃铛红点 + Toast
```

**核心特性**:
- 单向数据流,后端是唯一真相源
- WebSocket 推送解耦:规则执行、日志、UI 三者独立
- 失败隔离:任一 Action 失败不影响其他 Action 与其他规则

### 5.2 错误处理

| 场景 | 处理 |
|---|---|
| Event Bus 投递失败(内部异常) | 5xx 错误响应 + loguru 记录;不影响其他事件 |
| 单 Action 执行失败 | 异常捕获到 `ActionResult.error`,继续执行同规则其他 Action;整体 RuleExecution 标 success=false |
| 渠道发送失败 | 指数退避重试 3 次(1s/5s/30s),仍失败入 dead letter;不影响其他渠道 |
| WebSocket 断线 | 前端既有指数退避重连(后端无状态);重连后 `GET /devices` 拉快照 |
| APScheduler 任务崩溃 | scheduler 自带 job 异常隔离,不影响其他 job |
| DB 写入失败 | 整条 RuleExecution 回滚,5xx + loguru + 通知管理员(走 self-rule) |
| GLTF 加载失败 | 前端降级到 SVG 拉伸模式 + Toast 提示 |
| WebGL 不可用 | 检测后提示并降级到 2.5D 平面图模式 |

### 5.3 安全

- 所有 `/api/v1/automations/*` 和 `/api/v1/notifications/*` 走既有 `CurrentUser` 鉴权
- Webhook 出站:SSRF 防护(禁用 127.0.0.1/169.254.0.0/16 等内网段,可配置白名单)
- 模板渲染:Jinja2 `SandboxedEnvironment`,防 RCE
- 配置加密:见 §3.5
- 速率限制:每条规则触发频率上限 1 次/秒(防恶意配置)

### 5.4 测试金字塔(强制 TDD,与项目既有规范一致)

```
            ┌──────────┐
            │  E2E 1~2 │  端到端: 事件 → 通知 → WS(慢,CI 跑)
            ├──────────┤
        ┌───┤  集成 N  ├───┐  API 端点 + 真实 DB + mock SMTP/HTTP
        │   ├──────────┤   │
        │ ┌─┤ 单元 很多 ├─┐ │  每个 Trigger/Action/Channel/条件
        │ │ └──────────┘ │ │  纯函数 + mock
        │ └───────────────┘
```

- 后端测试:按 `backend/.claude/CLAUDE.md` §5 强制 TDD 流程
- 前端测试:Pinia store + 关键组件(`AutomationRuleForm.vue` / `DigitalTwinCanvas.vue`)
- 端到端:1-2 个 Playwright 脚本(可选,后期加入)

### 5.5 性能预算

- 单条规则触发 → Action 执行完成 p95 < 500ms(不含网络出站)
- 100 条 enabled 规则,系统启动加载 < 2s
- 3D 视图:60fps @ 100 设备(中端笔记本);超过 200 设备启用 LOD
- WS 推送频率限流:同一 topic 同一秒最多 1 条,超出批量合并

### 5.6 迁移与回滚

- 新增 **8 张表**（`automation_rules`、`rule_executions`、`notification_channels`、`notification_templates`、`notification_log`、`notification_settings`、`digital_twins`、`twin_device_bindings`），无既有表结构变更 → 升级无破坏
- 自动化引擎注册失败时，`lifespan` 启动仅记 warning，不影响其他模块
- 任何新功能模块都支持 `enabled=False` 关闭，降级到当前 Lumos Home 行为

### 5.7 与 Phase A 硬编码联动的共存策略

| Phase A 功能 | 既有实现位置 | 本期策略 |
|---|---|---|
| A1 成员到家/离家自动录制 | `presence_service._fire_event` | **保留**；后续提供等价 `presence_event` 规则模板，用户可选手动迁移 |
| A2 陌生设备告警 | `scanner/pipeline.py` | **保留**；可提供默认规则「陌生设备 → send_notification」作为 opt-in 替代 |
| A3 摄像头掉线检测 | `camera_health.py` | **保留**；规则引擎订阅同一 `camera_offline` topic，两者可并行 |
| A4 录制后自动投屏 | `recording_domain.py` | **保留**；`start_recording` / DLNA action 可覆盖同类需求 |

原则：**additive only**——新引擎不删除、不修改 Phase A 代码路径；避免「启用规则引擎后硬编码联动失效」的回归风险。迁移为可选、文档化的后续任务，不在 P0–P10 范围内。

---

## 6. 实施阶段(PR 顺序)

| 阶段 | 内容 | 估时 | 风险点 |
|---|---|---|---|
| **P0 基础** | Event Bus + ws_manager 桥接 + 8 张表 migration + SQLAlchemy 模型 | 1d | 启动流程注入，确保不影响既有 lifespan |
| **P1 Engine 骨架** | Trigger/Action 接口 + CronTrigger + ManualTrigger + Webhook Action + RuleRegistry | 2d | 调度并发,需要用 lock 防止重复触发 |
| **P2 持久化 + API** | automation_rules CRUD + 触发器元数据 API | 1d | Pydantic schema 严谨性 |
| **P3 EventTrigger** | 设备/录像事件订阅,filter 评估 | 1d | Event Bus 语义定为**至少一次投递**(at-least-once),同一事件可能被处理多次,故 cooldown_seconds 是必要而非可选 |
| **P4 Notification 渠道** | Email + Webhook 实现 + 模板 + 重试 + dead letter | 2d | SMTP 兼容性、SSL 验证、模板沙箱 |
| **P5 Notification API** | channels/templates/log/settings 接口 + WS 推送 | 1d | — |
| **P6 前端 Automations** | Pinia store + 规则编辑表单 + 列表 + 测试按钮 | 2d | 表单动态生成(根据 trigger/action schema) |
| **P7 前端 Notification Center** | 铃铛 + Drawer + Toast + 全局订阅 | 1d | — |
| **P8 3D Twin 数据** | digital_twins + bindings + API | 1d | — |
| **P9 3D Twin 视图** | three.js 画布 + GLTF/SVG 双模式 + 实时绑定 | 3d | 性能、WebGL 兼容性、坐标归一化 |
| **P10 集成测试** | 端到端 fixture + Playwright | 1d | — |

总计约 16 个工作日(纯单人,无外部阻塞)。

---

## 7. 不在本期范围(Out of Scope)

为避免 scope creep,以下功能**本期不做**:
- 移动 App 推送(后续考虑,需第三方账号)
- 本地 LLM 家庭管家(接 B2 引擎后再做)
- 第三方集成(HomeKit / Matter / 米家)— 留作后续 spec
- 录像自然语言检索(依赖 LLM)
- 多租户 / 多家庭(项目已明确 single household)
- 自动驾驶级别的隐私合规(局域网内单户,信任域)

---

## 8. 关键风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| GLTF 模型兼容 | 上传失败 → 3D 视图不可用 | 自动降级到 SVG 拉伸模式 |
| Jinja2 模板被滥用 | 任意代码执行 | `SandboxedEnvironment` + 模板白名单 |
| Webhook 出站打到内网 | SSRF | 内网段黑名单 + 可选白名单 |
| Event Bus 内存实现崩溃 | 整个事件流中断 | 加 try/except，error 写 loguru；保证模块边界 |
| `chain_rule` 循环引用 | 无限级联 | 最大深度 3 + 启动时环检测 |
| Phase A 与规则引擎双触发 | 同一事件执行两次副作用 | cooldown + 文档说明共存策略；迁移后关闭硬编码 |
| APScheduler 重启丢任务 | 计划规则漏触发 | 启动时 reload + 持久化作业(APScheduler 3.x JobStore) |
| 3D 性能 | 浏览器卡顿 | `frameloop="demand"` + LOD + 顶点数上限 |

---

## 9. 验收标准(Definition of Done)

- [ ] 所有 P0–P10 阶段完成,`uv run pytest` 全部通过
- [ ] `pnpm test` 全部通过
- [ ] `pnpm build` 产出 frontend/ 可被 PyInstaller 打包
- [ ] 端到端 Playwright 1 条通过(创建规则 → 触发 → 通知 → WS 推送)
- [ ] 文档更新:`backend/README.md` / `frontend/README.md` / `installer/`
- [ ] `.env.example` 增加 `LUMOS_SECRET_KEY`、`AUTOMATION_INBOUND_TOKEN` 等新环境变量
- [ ] 跨平台检查:Windows + Docker 启动均 OK

---

## 10. 修订记录

| 日期 | 变更 |
|---|---|
| 2026-06-11 | 初稿（brainstorming 产出） |
| 2026-06-11 | 审查修订：对齐既有 WS 事件名、补充 Event Bus 桥接与事件目录、补全 Condition/入站 API/`notification_settings` 表、修正表数量与文件路径、明确 Phase A 共存策略、修正 Frigate 数据流与 `device_mac` 外键 |

---

## 11. 相关文件清单（供 writing-plans 阶段细化）

新增/修改:
```
backend/app/
├── api/
│   ├── automations.py            # 新增
│   └── notifications.py          # 新增
├── domain/
│   ├── automation/
│   │   ├── engine.py             # 新增:Engine 编排 Trigger→Condition→Action
│   │   ├── registry.py           # 新增:RuleRegistry(加载/启停规则)
│   │   ├── triggers/             # 新增
│   │   │   ├── cron.py
│   │   │   ├── device_event.py
│   │   │   ├── recording_event.py
│   │   │   ├── motion_event.py
│   │   │   └── manual.py
│   │   ├── conditions/           # 新增
│   │   │   ├── time_window.py
│   │   │   ├── device_state.py
│   │   │   ├── event_field.py
│   │   │   └── composite.py
│   │   └── actions/              # 新增
│   │       ├── send_notification.py
│   │       ├── control_device.py
│   │       ├── start_recording.py
│   │       ├── webhook.py
│   │       └── chain_rule.py
│   ├── notification/
│   │   ├── center.py             # 新增
│   │   ├── channels/
│   │   │   ├── email.py
│   │   │   └── webhook.py
│   │   ├── template_engine.py    # 新增
│   │   ├── anti_spam.py          # 新增
│   │   └── crypto.py             # 新增(Fernet 封装)
│   └── event_bus.py              # 新增（轻量 pub/sub）
├── domain/services/
│   ├── ws_manager.py             # 修改：broadcast 内增加 event_bus.publish 钩子
│   └── frigate_bridge.py         # 修改：写入 CameraEvent 后 publish motion.detect
├── domain/models/                # 新增 SQLAlchemy 模型（遵循既有 domain/models 布局）
│   ├── automation.py
│   ├── notification.py
│   └── digital_twin.py
├── schemas/                      # 新增 Pydantic（与 api/ 同级）
│   ├── automation.py
│   ├── notification.py
│   └── digital_twin.py
├── main.py                       # 修改:注册路由 + lifespan 注入 engine
└── config.py                     # 修改:增加 LUMOS_SECRET_KEY 等

frontend/src/
├── api/
│   ├── automations.js            # 新增
│   ├── notificationChannels.js   # 新增（渠道/模板/日志 API，与 WS Toast store 分离）
│   └── digitalTwins.js           # 新增
├── stores/
│   ├── automations.js            # 新增
│   ├── notifications.js          # 修改：扩展既有 store，非新建
│   └── digitalTwins.js           # 新增
├── views/
│   ├── AutomationsView.vue       # 新增
│   ├── TwinsView.vue             # 新增
│   └── TwinDetailView.vue        # 新增
├── components/
│   ├── automations/
│   │   ├── RuleForm.vue          # 新增
│   │   ├── TriggerPicker.vue
│   │   ├── ActionPicker.vue
│   │   └── ExecutionHistory.vue
│   ├── notifications/
│   │   ├── ChannelForm.vue
│   │   ├── TemplateForm.vue
│   │   └── LogTable.vue
│   ├── twins/
│   │   ├── DigitalTwinCanvas.vue # 核心
│   │   ├── DeviceBinding.vue
│   │   └── HeatmapLegend.vue
│   └── NotificationCenter.vue    # 全局铃铛 + Drawer
├── composables/
│   └── useWebSocketTopics.js     # 扩展:订阅新 topic
├── lib/
│   └── three/                    # 新增 three.js 工具
│       ├── scene.ts
│       ├── heatmapShader.ts
│       └── deviceIcon.ts
└── router/index.js               # 修改:增加新路由
```

测试:
```
backend/tests/
├── unit/
│   ├── domain/
│   │   ├── test_automation_engine.py
│   │   ├── test_triggers.py
│   │   ├── test_actions.py
│   │   ├── test_event_bus.py
│   │   ├── test_notification_center.py
│   │   ├── test_channels.py
│   │   ├── test_template_engine.py
│   │   ├── test_anti_spam.py
│   │   └── test_crypto.py
│   └── services/
└── integration/
    ├── test_automations_api.py
    ├── test_notifications_api.py
    └── test_e2e_automation.py    # 端到端 Playwright Python

frontend/tests/
├── components/
│   ├── automations/
│   ├── notifications/
│   └── twins/
└── stores/
```

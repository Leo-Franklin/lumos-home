# Smart Home Control Center 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在既有 Lumos Home 上叠加 Event Bus、Automation Engine、Notification Center、3D Digital Twin，实现用户可配置的规则驱动智能家居控制中心，且不破坏 Phase A 硬编码联动。

**Architecture:** 在 `ws_manager.broadcast()` 内桥接内存 Event Bus；Automation Engine 通过 Trigger→Condition→Action 管道消费事件；Notification Center 作为 Action 副作用层；前端继续消费既有 WS 格式并扩展 REST 管理界面。8 张新表经 `init_db()` 的 `create_all` 创建，lifespan 注入 Engine/NotificationCenter，失败仅 warning。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2 async, SQLite, APScheduler 3.10, Jinja2 SandboxedEnvironment, Fernet (cryptography), Vue 3, Pinia, Element Plus, three.js, Vitest, pytest-asyncio, httpx

**Spec:** `docs/superpowers/specs/2026-06-11-smart-home-control-center-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/app/domain/event_bus.py` | 内存 pub/sub，`publish` / `subscribe` |
| Modify | `backend/app/domain/services/ws_manager.py` | `broadcast` 内调用 `event_bus.publish` |
| Create | `backend/app/domain/models/automation.py` | `AutomationRule`, `RuleExecution` ORM |
| Create | `backend/app/domain/models/notification.py` | channels/templates/log/settings ORM |
| Create | `backend/app/domain/models/digital_twin.py` | twins + bindings ORM |
| Modify | `backend/app/domain/models/__init__.py` | 导出新模型 |
| Modify | `backend/app/database.py` | `init_db` import 新模型 |
| Modify | `backend/app/config.py` | `LUMOS_SECRET_KEY`, `AUTOMATION_INBOUND_TOKEN` |
| Modify | `backend/.env.example` | 新环境变量占位 |
| Create | `backend/app/domain/automation/types.py` | `TriggerContext`, `RuleContext`, `ActionResult` dataclasses |
| Create | `backend/app/domain/automation/registry.py` | Trigger/Action/Condition 反序列化注册表 |
| Create | `backend/app/domain/automation/engine.py` | 规则执行、cooldown、chain 深度限制 |
| Create | `backend/app/domain/automation/triggers/*.py` | cron/device/recording/presence/motion/manual |
| Create | `backend/app/domain/automation/conditions/*.py` | time_window/device_state/event_field/composite |
| Create | `backend/app/domain/automation/actions/*.py` | 5 种内置 Action |
| Create | `backend/app/domain/notification/center.py` | 发送编排、重试、WS 广播 |
| Create | `backend/app/domain/notification/channels/email.py` | SMTP 适配器 |
| Create | `backend/app/domain/notification/channels/webhook.py` | HTTP 出站 + SSRF 校验 |
| Create | `backend/app/domain/notification/template_engine.py` | Jinja2 沙箱渲染 |
| Create | `backend/app/domain/notification/anti_spam.py` | 静默/聚类/severity |
| Create | `backend/app/domain/notification/crypto.py` | Fernet 加解密 |
| Create | `backend/app/schemas/automation.py` | CRUD + 元数据 schema |
| Create | `backend/app/schemas/notification.py` | 渠道/模板/日志 schema |
| Create | `backend/app/schemas/digital_twin.py` | twin/binding schema |
| Create | `backend/app/api/automations.py` | 规则 CRUD + inbound + 元数据 |
| Create | `backend/app/api/notifications.py` | 渠道/模板/日志/settings |
| Create | `backend/app/api/digital_twins.py` | twin CRUD + binding |
| Modify | `backend/app/domain/services/frigate_bridge.py` | 写 CameraEvent 后 publish `motion.detect` |
| Modify | `backend/app/main.py` | lifespan 启动 Engine；注册 3 个新 router |
| Modify | `backend/pyproject.toml` | 添加 `jinja2`；dev 组添加 `aiosmtpd` |
| Create | `frontend/src/api/automations.js` | 规则 API 客户端 |
| Create | `frontend/src/api/notificationChannels.js` | 通知渠道 API |
| Create | `frontend/src/api/digitalTwins.js` | Twin API |
| Create | `frontend/src/stores/automations.js` | 规则 Pinia store |
| Modify | `frontend/src/stores/notifications.js` | 扩展 serverNotifications + 未读数 |
| Create | `frontend/src/stores/digitalTwins.js` | Twin Pinia store |
| Create | `frontend/src/views/AutomationsView.vue` | 规则列表/编辑 |
| Create | `frontend/src/components/NotificationCenter.vue` | 铃铛 + Drawer |
| Create | `frontend/src/views/TwinsView.vue` | Twin 列表 |
| Create | `frontend/src/views/TwinDetailView.vue` | 3D 主视图 |
| Create | `frontend/src/lib/three/*.ts` | scene/heatmapShader/deviceIcon |
| Modify | `frontend/package.json` | 添加 `three` 依赖 |
| Modify | `frontend/src/router/index.js` | `/automations`, `/twins`, `/twins/:id` |

---

## Task 1: Event Bus（P0）

**Files:**
- Create: `backend/app/domain/event_bus.py`
- Create: `backend/tests/unit/domain/test_event_bus.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/domain/test_event_bus.py
import pytest
from app.domain.event_bus import EventBus


@pytest.mark.asyncio
async def test_publish_calls_all_subscribers():
    bus = EventBus()
    received: list[tuple[str, dict]] = []

    async def handler(topic: str, payload: dict):
        received.append((topic, payload))

    bus.subscribe("camera_offline", handler)
    await bus.publish("camera_offline", {"mac": "AA:BB:CC:DD:EE:FF"})
    assert received == [("camera_offline", {"mac": "AA:BB:CC:DD:EE:FF"})]


@pytest.mark.asyncio
async def test_subscriber_exception_does_not_break_others():
    bus = EventBus()
    ok: list[str] = []

    async def bad(_topic, _payload):
        raise RuntimeError("boom")

    async def good(_topic, _payload):
        ok.append("ok")

    bus.subscribe("x", bad)
    bus.subscribe("x", good)
    await bus.publish("x", {})
    assert ok == ["ok"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_event_bus.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'app.domain.event_bus'`

- [ ] **Step 3: Implement EventBus**

```python
# backend/app/domain/event_bus.py
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

Subscriber = Callable[[str, dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(self, topic: str, handler: Subscriber) -> None:
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Subscriber) -> None:
        handlers = self._subscribers.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            handlers = list(self._subscribers.get(topic, []))
        for handler in handlers:
            try:
                await handler(topic, payload)
            except Exception as e:  # noqa: BLE001
                logger.error(f"EventBus handler failed topic={topic}: {e!r}")


event_bus = EventBus()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/domain/test_event_bus.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/event_bus.py backend/tests/unit/domain/test_event_bus.py
git commit -m "feat: add in-memory EventBus with isolated subscriber errors"
```

---

## Task 2: ws_manager 桥接（P0）

**Files:**
- Modify: `backend/app/domain/services/ws_manager.py`
- Create: `backend/tests/unit/domain/test_ws_manager_bridge.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/domain/test_ws_manager_bridge.py
import pytest
from unittest.mock import AsyncMock, patch
from app.domain.services.ws_manager import WebSocketManager


@pytest.mark.asyncio
async def test_broadcast_publishes_to_event_bus():
    mgr = WebSocketManager()
    published: list[tuple[str, dict]] = []

    async def capture(topic, payload):
        published.append((topic, payload))

    with patch("app.domain.services.ws_manager.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock(side_effect=capture)
        # No WS connections — only test bus hook
        await mgr.broadcast("camera_offline", {"mac": "AA:BB:CC:DD:EE:01"})

    assert published == [("camera_offline", {"mac": "AA:BB:CC:DD:EE:01"})]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_ws_manager_bridge.py -v`
Expected: FAIL — `publish` never called

- [ ] **Step 3: Add bridge hook to broadcast**

在 `backend/app/domain/services/ws_manager.py` 的 `broadcast` 方法末尾（`stale` 清理之后）添加：

```python
from app.domain.event_bus import event_bus

# inside broadcast(), after stale cleanup:
try:
    await event_bus.publish(event, data)
except Exception as e:  # noqa: BLE001
    logger.warning(f"EventBus publish failed for {event}: {e!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/domain/test_ws_manager_bridge.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/services/ws_manager.py backend/tests/unit/domain/test_ws_manager_bridge.py
git commit -m "feat: bridge ws_manager.broadcast to EventBus"
```

---

## Task 3: 数据库模型 + config（P0）

**Files:**
- Create: `backend/app/domain/models/automation.py`
- Create: `backend/app/domain/models/notification.py`
- Create: `backend/app/domain/models/digital_twin.py`
- Modify: `backend/app/domain/models/__init__.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Create: `backend/tests/unit/models/test_automation_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/models/test_automation_models.py
from app.domain.models.automation import AutomationRule, RuleExecution


def test_automation_rule_tablename():
    assert AutomationRule.__tablename__ == "automation_rules"


def test_rule_execution_tablename():
    assert RuleExecution.__tablename__ == "rule_executions"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/models/test_automation_models.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Create automation models**

```python
# backend/app/domain/models/automation.py
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trigger_spec: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    actions: Mapped[str] = mapped_column(Text, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RuleExecution(Base):
    __tablename__ = "rule_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False
    )
    fired_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    trigger_data: Mapped[str | None] = mapped_column(Text)
    action_results: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool | None] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)
```

按 spec §3.4 / §4.2 同样方式创建 `notification.py`（4 表）和 `digital_twin.py`（2 表），`twin_device_bindings.device_mac` 外键指向 `devices.mac`。

- [ ] **Step 4: Register models in init_db**

`backend/app/database.py` — 在 `init_db()` 的 model import 注释处添加：

```python
import app.domain.models.automation  # noqa: F401
import app.domain.models.notification  # noqa: F401
import app.domain.models.digital_twin  # noqa: F401
```

`backend/app/domain/models/__init__.py` — 追加导出。

- [ ] **Step 5: Add LUMOS_SECRET_KEY to config**

`backend/app/config.py` — 在 Settings 类添加：

```python
lumos_secret_key: str = ""
automation_inbound_token: str = ""
```

并在 `validate_settings()` 中校验 `lumos_secret_key` 长度 ≥32（开发/测试环境可通过 conftest 设置测试值）。

`backend/.env.example` 追加：

```
LUMOS_SECRET_KEY=your_random_secret_here_at_least_32_chars
AUTOMATION_INBOUND_TOKEN=
```

`backend/tests/conftest.py` 追加：

```python
os.environ["LUMOS_SECRET_KEY"] = "test_lumos_secret_key_at_least_32_chars_long"
```

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest tests/unit/models/test_automation_models.py -v`
Expected: PASS

Run: `cd backend && uv run python -c "import asyncio; from app.database import init_db; asyncio.run(init_db()); print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/domain/models/ backend/app/database.py backend/app/config.py backend/.env.example backend/tests/
git commit -m "feat: add automation/notification/twin models and LUMOS_SECRET_KEY config"
```

---

## Task 4: Automation Engine 核心（P1）

**Files:**
- Create: `backend/app/domain/automation/types.py`
- Create: `backend/app/domain/automation/registry.py`
- Create: `backend/app/domain/automation/engine.py`
- Create: `backend/app/domain/automation/triggers/manual.py`
- Create: `backend/app/domain/automation/triggers/cron.py`
- Create: `backend/app/domain/automation/actions/webhook.py`
- Create: `backend/tests/unit/domain/test_automation_engine.py`

- [ ] **Step 1: Write the failing integration-style unit test**

```python
# backend/tests/unit/domain/test_automation_engine.py
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock
import pytest
from app.domain.automation.engine import AutomationEngine
from app.domain.automation.types import ActionResult


@pytest.mark.asyncio
async def test_manual_trigger_executes_webhook_action():
    engine = AutomationEngine(session_factory=AsyncMock())
    engine._webhook_sender = AsyncMock(return_value=ActionResult(success=True))

    rule = {
        "id": "rule-1",
        "name": "test",
        "enabled": True,
        "trigger_spec": json.dumps({"type": "manual"}),
        "conditions": "[]",
        "actions": json.dumps([
            {"type": "webhook", "url": "https://example.com/hook", "method": "POST", "body": "{}"}
        ]),
        "cooldown_seconds": 0,
    }
    results = await engine.execute_rule(rule, trigger_data={"test": True})
    assert results[0].success is True
    engine._webhook_sender.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_automation_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement types + registry + engine skeleton**

`types.py` — 定义 `TriggerContext`, `RuleContext`, `ActionResult`, `TriggerSpec`, `ActionSpec`（TypedDict 或 Pydantic）。

`registry.py` — `TRIGGER_REGISTRY`, `ACTION_REGISTRY`, `CONDITION_REGISTRY` 字典，`build_trigger(spec)`, `build_action(spec)`, `build_conditions(specs)`。

`engine.py` 核心逻辑：

```python
class AutomationEngine:
    MAX_CHAIN_DEPTH = 3

    async def execute_rule(self, rule_row, trigger_data: dict, chain_depth: int = 0) -> list[ActionResult]:
        if chain_depth > self.MAX_CHAIN_DEPTH:
            return [ActionResult(success=False, error="chain depth exceeded")]
        # 1. cooldown check against rule_row["last_fired_at"]
        # 2. evaluate conditions (empty = True)
        # 3. asyncio.gather actions, return_exceptions=False, catch per action
        # 4. write RuleExecution row
        # 5. event_bus.publish("rule.fired", {"rule_id": ..., "rule_name": ...})
```

`triggers/manual.py` — `evaluate` 始终 False（仅 API 直调 `execute_rule`）；`start/stop` 空操作。

`triggers/cron.py` — 用 `scheduler_service.scheduler.add_job` 注册，job 回调调 `engine.execute_rule`。

`actions/webhook.py` — 复用 `app.domain.services.webhook_validation.validate_webhook_url` 做 SSRF 防护；`httpx.AsyncClient` 发送。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/domain/test_automation_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/automation/
git commit -m "feat: add AutomationEngine with manual trigger and webhook action"
```

---

## Task 5: RuleRegistry + lifespan 注入（P1）

**Files:**
- Create: `backend/app/domain/automation/registry_service.py`（RuleRegistry：DB 加载/启停）
- Modify: `backend/app/main.py`
- Create: `backend/tests/unit/domain/test_rule_registry.py`

- [ ] **Step 1: Write failing test for load enabled rules**

```python
@pytest.mark.asyncio
async def test_registry_loads_enabled_rules_only(db):
    # seed 2 rules: one enabled, one disabled
    # registry.reload() → assert only enabled rule registered
```

- [ ] **Step 2–4: Implement RuleRegistry**

- `reload()`: `SELECT * FROM automation_rules WHERE enabled=1`
- 按 `trigger.type` 调用对应 trigger 的 `start(engine, rule)`
- `unload_rule(rule_id)`: 调 `trigger.stop()`
- 在 `main.py` lifespan `yield` 前：

```python
from app.domain.automation.registry_service import RuleRegistry
from app.domain.automation.engine import AutomationEngine

engine = AutomationEngine(session_factory=AsyncSessionLocal)
registry = RuleRegistry(engine=engine, session_factory=AsyncSessionLocal)
try:
    await registry.reload()
    app.state.automation_engine = engine
    app.state.rule_registry = registry
except Exception as e:
    logger.warning(f"AutomationEngine 启动失败，已跳过: {e}")
```

`yield` 后 `await registry.shutdown()`。

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: wire RuleRegistry into app lifespan"
```

---

## Task 6: Automations REST API（P2）

**Files:**
- Create: `backend/app/schemas/automation.py`
- Create: `backend/app/api/automations.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/api/test_automations_api.py`

- [ ] **Step 1: Write failing CRUD test**

```python
@pytest.mark.asyncio
async def test_create_and_list_automation(auth_client):
    payload = {
        "name": "Camera offline alert",
        "enabled": True,
        "trigger_spec": {"type": "device_event", "topic": "camera_offline"},
        "conditions": [],
        "actions": [{"type": "webhook", "url": "https://example.com", "method": "POST", "body": "{}"}],
        "cooldown_seconds": 60,
    }
    resp = await auth_client.post("/api/v1/automations", json=payload)
    assert resp.status_code == 201
    list_resp = await auth_client.get("/api/v1/automations")
    assert list_resp.json()["total"] >= 1
```

- [ ] **Step 2–4: Implement schemas + router**

`schemas/automation.py`:
- `AutomationCreate`, `AutomationUpdate`, `AutomationOut`
- `TriggerMetaOut`, `ActionMetaOut`, `ConditionMetaOut`（静态元数据列表）
- `InboundEvent`（topic + payload）

`api/automations.py` 端点按 spec §2.6 实现；创建/更新后调 `request.app.state.rule_registry.reload()`。

元数据端点返回：

```python
TRIGGER_METADATA = [
    {"type": "cron", "label": "定时", "fields": [...]},
    {"type": "device_event", "label": "设备事件", "fields": [...]},
    # ...
]
```

`main.py` 添加：

```python
from app.api import automations
app.include_router(automations.router, prefix=P)
```

- [ ] **Step 5: Run integration tests**

Run: `cd backend && uv run pytest tests/integration/api/test_automations_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add automations CRUD API and trigger/action metadata"
```

---

## Task 7: EventTrigger + Frigate motion（P3）

**Files:**
- Create: `backend/app/domain/automation/triggers/event_trigger.py`（device/recording/presence 共用）
- Create: `backend/app/domain/automation/triggers/motion_event.py`
- Create: `backend/app/domain/automation/conditions/time_window.py`
- Create: `backend/app/domain/automation/conditions/event_field.py`
- Create: `backend/app/domain/automation/conditions/device_state.py`
- Create: `backend/app/domain/automation/conditions/composite.py`
- Modify: `backend/app/domain/services/frigate_bridge.py`
- Create: `backend/tests/unit/domain/test_event_trigger.py`
- Create: `backend/tests/integration/services/test_frigate_motion_publish.py`

- [ ] **Step 1: Write failing EventTrigger test**

```python
@pytest.mark.asyncio
async def test_device_event_trigger_fires_on_camera_offline():
    engine = AutomationEngine(...)
    fired: list[str] = []
    engine.execute_rule = AsyncMock(side_effect=lambda *a, **k: fired.append("yes") or [])

    trigger = DeviceEventTrigger({"type": "device_event", "topic": "camera_offline"})
    await trigger.start(engine, rule_row)
    await event_bus.publish("camera_offline", {"mac": "AA:BB:CC:DD:EE:01"})
    assert fired == ["yes"]
```

- [ ] **Step 2–4: Implement EventTrigger family**

`event_trigger.py`:
- `start()` → `event_bus.subscribe(topic, self._on_event)`
- `_on_event`: filter 评估（`device_type` 等）→ `engine.execute_rule(rule, payload)`
- `device_event` / `recording_event` / `presence_event` 均为配置不同的 topic + filter

`motion_event.py`:
- 订阅 `motion.detect`
- filter: `camera_mac`, `labels`, `min_confidence`

Conditions 按 spec §2.2.1 实现；`composite.py` 递归深度 ≤3。

`frigate_bridge.py` — 在 `_create_event` 成功 commit 后：

```python
from app.domain.event_bus import event_bus
await event_bus.publish("motion.detect", {
    "camera_mac": camera_mac,
    "label": label,
    "score": score,
})
```

- [ ] **Step 5: Implement inbound webhook**

`POST /api/v1/automations/inbound`:
- 若 `settings.automation_inbound_token` 为空 → 404
- 校验 `X-Lumos-Token` header
- topic 白名单：`motion.detect`, `camera_offline`, `unknown_device_detected`, …
- `await event_bus.publish(body.topic, body.payload)` → 202

- [ ] **Step 6: Run tests + commit**

```bash
git commit -m "feat: add event triggers, conditions, Frigate motion.detect publish"
```

---

## Task 8: 剩余 Actions（P3）

**Files:**
- Create: `backend/app/domain/automation/actions/send_notification.py`
- Create: `backend/app/domain/automation/actions/control_device.py`
- Create: `backend/app/domain/automation/actions/start_recording.py`
- Create: `backend/app/domain/automation/actions/chain_rule.py`
- Create: `backend/tests/unit/domain/test_actions.py`

- [ ] **Step 1–5: TDD each action**

`send_notification` — 调 `NotificationCenter.send()`（Task 9 实现后接通）；本期先用接口注入。

`start_recording` — 通过 `app.state.recorder` 调 `start_recording(camera_mac, ...)`，已在录制则跳过（幂等）。

`control_device` — MVP：记录日志 + 返回 success；真实设备控制留后续（spec 允许「若设备支持」）。

`chain_rule` — 调 `engine.execute_rule(target_rule, trigger_data, chain_depth+1)`；启动时 DFS 检测环。

Run: `cd backend && uv run pytest tests/unit/domain/test_actions.py -v`

```bash
git commit -m "feat: add send_notification, start_recording, chain_rule actions"
```

---

## Task 9: Notification Center 后端（P4）

**Files:**
- Create: `backend/app/domain/notification/crypto.py`
- Create: `backend/app/domain/notification/template_engine.py`
- Create: `backend/app/domain/notification/channels/email.py`
- Create: `backend/app/domain/notification/channels/webhook.py`
- Create: `backend/app/domain/notification/anti_spam.py`
- Create: `backend/app/domain/notification/center.py`
- Modify: `backend/pyproject.toml`（`jinja2`, dev:`aiosmtpd`）
- Create: `backend/tests/unit/domain/test_notification_*.py`

- [ ] **Step 1: Add jinja2 dependency**

`backend/pyproject.toml`:

```toml
"jinja2>=3.1.0",
```

dev group: `"aiosmtpd>=1.4.6"`

Run: `cd backend && uv sync`

- [ ] **Step 2: TDD crypto + template engine**

`crypto.py`:

```python
from cryptography.fernet import Fernet
import base64, hashlib

def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt(secret: str, plaintext: str) -> str: ...
def decrypt(secret: str, token: str) -> str: ...
```

`template_engine.py` — `SandboxedEnvironment`，上下文含 `event`, `device`, `rule`。

- [ ] **Step 3: TDD email + webhook channels**

Email 用 `aiosmtplib` 或 stdlib `smtplib` 在 executor 中发送；测试用 `aiosmtpd` controller fixture。

Webhook 出站复用 `validate_webhook_url`。

- [ ] **Step 4: Implement NotificationCenter**

```python
class NotificationCenter:
    async def send(self, *, channel_id, template_id, severity, context, rule_id=None):
        # 1. anti_spam.should_send()
        # 2. render template
        # 3. channel.send() with retry 1s/5s/30s
        # 4. write notification_log
        # 5. ws_manager.broadcast("notification.sent" or "notification.failed", ...)
```

`anti_spam.py` — 静默时段查 `notification_settings`；聚类 5min/3条；critical 绕过静默。

- [ ] **Step 5: Wire send_notification action to NotificationCenter**

- [ ] **Step 6: Run tests + commit**

```bash
git commit -m "feat: add NotificationCenter with email/webhook channels and anti-spam"
```

---

## Task 10: Notifications REST API（P5）

**Files:**
- Create: `backend/app/schemas/notification.py`
- Create: `backend/app/api/notifications.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/api/test_notifications_api.py`

- [ ] **Step 1–5: TDD all endpoints per spec §3.6**

- channels CRUD + `POST .../test`
- templates CRUD
- `GET /log` 分页 + severity/status filter
- `GET/PATCH /settings`

渠道 config 写入前加密 `password` 字段；读出 API 返回 `password: "***"` 掩码。

```bash
git commit -m "feat: add notifications REST API"
```

---

## Task 11: 前端 Automations UI（P6）

**Files:**
- Create: `frontend/src/api/automations.js`
- Create: `frontend/src/stores/automations.js`
- Create: `frontend/src/views/AutomationsView.vue`
- Create: `frontend/src/components/automations/RuleForm.vue`
- Create: `frontend/src/components/automations/TriggerPicker.vue`
- Create: `frontend/src/components/automations/ActionPicker.vue`
- Create: `frontend/src/components/automations/ExecutionHistory.vue`
- Modify: `frontend/src/router/index.js`
- Create: `frontend/tests/stores/automations.test.js`

- [ ] **Step 1: Write failing store test**

```javascript
// frontend/tests/stores/automations.test.js
import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, vi } from 'vitest'
import { useAutomationsStore } from '@/stores/automations'

describe('automations store', () => {
  it('fetchRules loads list', async () => {
    setActivePinia(createPinia())
    vi.mock('@/api/automations', () => ({
      listAutomations: vi.fn().mockResolvedValue({ items: [{ id: '1', name: 'R1' }], total: 1 }),
    }))
    const store = useAutomationsStore()
    await store.fetchRules()
    expect(store.rules).toHaveLength(1)
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd frontend && pnpm test tests/stores/automations.test.js`
Expected: FAIL

- [ ] **Step 3: Implement API + store + views**

`api/automations.js` — `listAutomations`, `createAutomation`, `updateAutomation`, `deleteAutomation`, `testAutomation`, `getTriggerMeta`, `getActionMeta`, `getExecutions`。

`AutomationsView.vue` — Element Plus 表格 + 「新建规则」按钮。

`RuleForm.vue` — 根据 `getTriggerMeta()` 动态渲染 `TriggerPicker` / `ActionPicker`；保存调 store。

路由：

```javascript
{
  path: 'automations',
  component: () => import('@/views/AutomationsView.vue'),
  meta: { titleKey: 'layout.automations' },
},
```

- [ ] **Step 4: Run tests + manual smoke**

Run: `cd frontend && pnpm test && pnpm build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(frontend): add automations management UI"
```

---

## Task 12: 前端 Notification Center（P7）

**Files:**
- Create: `frontend/src/api/notificationChannels.js`
- Modify: `frontend/src/stores/notifications.js`
- Create: `frontend/src/components/NotificationCenter.vue`
- Create: `frontend/src/components/notifications/ChannelForm.vue`
- Create: `frontend/src/components/notifications/TemplateForm.vue`
- Create: `frontend/src/components/notifications/LogTable.vue`
- Modify: `frontend/src/layout/MainLayout.vue`（顶栏加铃铛）

- [ ] **Step 1: Extend notifications store**

在 `handle(msg)` switch 中追加：

```javascript
case 'notification.sent':
case 'notification.failed':
  serverNotifications.value.unshift(msg)
  unreadCount.value += 1
  break
```

新增 `fetchServerNotifications()`, `markAllRead()`。

**不删除**既有 `camera_offline` 等 case 和 `useNotificationPreferences` 逻辑。

- [ ] **Step 2: Build NotificationCenter.vue**

- 顶栏 `el-badge` 铃铛图标
- `el-drawer` 展示 `LogTable`（调 API 分页加载）
- 设置页入口：渠道/模板表单

- [ ] **Step 3: Run frontend tests + build**

Run: `cd frontend && pnpm test && pnpm build`

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(frontend): add NotificationCenter drawer and channel management"
```

---

## Task 13: Digital Twin 后端（P8）

**Files:**
- Create: `backend/app/schemas/digital_twin.py`
- Create: `backend/app/api/digital_twins.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/api/test_digital_twins_api.py`

- [ ] **Step 1–5: TDD twin CRUD + binding endpoints**

```
GET/POST        /api/v1/twins
GET/PATCH/DELETE /api/v1/twins/{id}
GET/POST        /api/v1/twins/{id}/bindings
PATCH/DELETE    /api/v1/twins/{id}/bindings/{binding_id}
POST            /api/v1/twins/{id}/upload-model   # multipart .glb
```

上传文件存 `data/twins/{twin_id}/model.glb`；`gltf_url` 存相对路径。

```bash
git commit -m "feat: add digital twins API and device bindings"
```

---

## Task 14: Digital Twin 前端（P9）

**Files:**
- Modify: `frontend/package.json`（`"three": "^0.170.0"`）
- Create: `frontend/src/lib/three/scene.ts`
- Create: `frontend/src/lib/three/deviceIcon.ts`
- Create: `frontend/src/lib/three/heatmapShader.ts`
- Create: `frontend/src/components/twins/DigitalTwinCanvas.vue`
- Create: `frontend/src/views/TwinsView.vue`
- Create: `frontend/src/views/TwinDetailView.vue`
- Modify: `frontend/src/views/DashboardView.vue`（「3D 视图」按钮）
- Modify: `frontend/src/router/index.js`
- Create: `frontend/tests/components/twins/DigitalTwinCanvas.test.js`

- [ ] **Step 1: Install three.js**

```bash
cd frontend && pnpm add three
```

- [ ] **Step 2: Implement scene.ts minimal bootstrap**

```typescript
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export function createScene(canvas: HTMLCanvasElement) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100)
  const controls = new OrbitControls(camera, canvas)
  return { renderer, scene, camera, controls }
}
```

- [ ] **Step 3: DigitalTwinCanvas.vue**

- props: `bindings`, `deviceStates`, `mode`（`live` | `edit`）
- watch WS 事件更新设备颜色（通过 store，不直接连 WS）
- GLTF 加载失败 → fallback SVG extrude（`THREE.ExtrudeGeometry` + 简单矩形）
- `frameloop="demand"`：`controls.addEventListener('change', render)` + 事件动画时 `requestAnimationFrame`

- [ ] **Step 4: TwinDetailView layout**

- 左 75%：`DigitalTwinCanvas`
- 右 25%：设备列表 + 属性
- 顶栏：实时/编辑模式切换；编辑模式可拖拽 binding

- [ ] **Step 5: Heatmap time slider**

从 `GET /api/v1/camera-events?event_type=external_frigate` 拉 24h 数据，映射到 binding xz，传入 `heatmapShader.ts`。

- [ ] **Step 6: Run tests + build**

Run: `cd frontend && pnpm test && pnpm build`

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(frontend): add 3D digital twin view with three.js"
```

---

## Task 15: 端到端集成 + 文档（P10）

**Files:**
- Create: `backend/tests/integration/test_e2e_automation.py`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Modify: `README.md`（简述新功能）

- [ ] **Step 1: Write E2E test**

```python
@pytest.mark.asyncio
async def test_event_to_notification_flow(auth_client, db):
    """创建 webhook 渠道 + camera_offline 规则 → 发布事件 → 验证 execution 记录"""
    # 1. POST /notifications/channels (webhook → mock server)
    # 2. POST /automations (device_event camera_offline → send_notification)
    # 3. await event_bus.publish("camera_offline", {"mac": "..."})
    # 4. GET /automations/{id}/executions → assert success
    # 5. assert notification_log has sent row
```

- [ ] **Step 2: Run full test suites**

```bash
cd backend && uv run pytest -v
cd frontend && pnpm test && pnpm build
```

Expected: all pass

- [ ] **Step 3: Update docs**

- `backend/README.md` — 新 API 端点表、环境变量、`domain/automation` 结构
- `frontend/README.md` — 新路由、three.js 注意点
- 根 `README.md` — Features 段追加「自动化规则」「通知中心」「3D 视图」

- [ ] **Step 4: Final commit**

```bash
git commit -m "test: add automation e2e flow and update documentation"
```

---

## Spec Coverage Checklist

| Spec section | Task |
|---|---|
| §1.1 Event Bus 桥接 | Task 2 |
| §1.2 事件目录 | Task 2, 7 |
| §2 Automation Engine | Task 4, 5, 6, 7, 8 |
| §2.6.1 inbound webhook | Task 7 |
| §3 Notification Center | Task 9, 10 |
| §4 Digital Twin | Task 13, 14 |
| §5.7 Phase A 共存 | 全计划 additive only，不修改 presence/scanner 硬编码路径 |
| §9 Definition of Done | Task 15 |

---

## Execution Order Summary

```
P0:  Task 1 → 2 → 3
P1:  Task 4 → 5
P2:  Task 6
P3:  Task 7 → 8
P4:  Task 9
P5:  Task 10
P6:  Task 11
P7:  Task 12
P8:  Task 13
P9:  Task 14
P10: Task 15
```

**Estimated:** ~16 工作日（与 spec §6 一致）。P9（three.js）建议预留 +2 天 buffer。

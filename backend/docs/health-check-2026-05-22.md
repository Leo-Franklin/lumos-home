# 项目健康检查报告 (2026-05-22)

## 1. 项目结构 — 重复的代码目录层

### `app/api/` vs `app/routers/` — P0

两个目录各自包含**功能重复的 API 路由实现**。`app/main.py:16-27` 导入的是 `app.api`，`app/api/__init__.py` 从 `app.api.*` 显式导入具体模块，但第 13 行又 `from app.routers import *`。

`app/routers/__init__.py` 是 re-export，但其余 9 个文件全部是独立实现，与 `app/api/` 下同名文件内容高度重合。来自 2026-05-13 重构计划（`docs/superpowers/plans/2026-05-13-backend-code-organization-refactor.md`）的过渡代码。

部分测试仍从 `app.routers` 导入内部函数：
- `tests/test_a2_unknown_device.py:3` → `from app.routers.devices import _find_unknown_devices`
- `tests/test_analytics.py:250,275,300` → `from app.routers.devices import _log_scan_result`

### `app/services/` vs `app/domain/services/` — P1

`app/services/__init__.py` 从 `app.domain.services` 做 re-export。`app/services/` 内的独立文件（如 `ws_manager.py`）也存在于 `app/domain/services/`。

### `app/models/` vs `app/domain/models/` — P1

`app/models/__init__.py` 从 `app.domain.models` 做 re-export，单向，无循环依赖。

### `app/infrastructure/` — P3

`app/infrastructure/__init__.py` 只有 docstring，无任何模块实现。

### `app/domain/repositories/` — P2

定义了 `CameraRepository`, `DeviceRepository`, `RecordingRepository`, `ScheduleRepository`，但**全项目无任何 import 引用**。业务代码在 router/service 层直接使用 SQLAlchemy `select` 操作数据库，repository 模式未落地。

---

## 2. 依赖问题

### 过时包（生产关注）

| 包 | 当前 | 最新 | 风险 |
|---|---|---|---|
| `cryptography` | 46.0.7 | 48.0.0 | 跨大版本，含安全修复 |
| `python-multipart` | 0.0.26 | 0.0.29 | 安全更新 |
| `certifi` | 2026.4.22 | 2026.5.20 | 证书过期风险 |
| `urllib3` | 2.6.3 | 2.7.0 | 主版本更新 |
| `pip` | 24.0 | 26.1.1 | 严重过时 |
| `setuptools` | 65.5.0 | 82.0.1 | 严重过时 |

### 依赖声明

`pyproject.toml:7-27` 全部使用 `>=` 约束，配合 `uv.lock` 可接受，但升级时需注意广度。

---

## 3. 死代码 / 未使用导出

### F841（赋值后未使用）

- `app/api/cameras.py:173` — `settings = get_settings()`
- `app/api/recordings.py:21` — `local_storage`
- `app/database.py:57` — `settings = get_settings()`
- `app/routers/cameras.py:173` — `settings = get_settings()`

### 废弃数据库文件

- `data/smarthome.db` — 0 字节，无引用
- `data/test_preset.db` — 0 字节，无引用

### 重复实现的旧路由代码

`app/routers/` 下 9 个非 `__init__` 文件均为旧版 router 实现，已在 `app/api/` 中有新版对应实现，但仍保留并包含从旧路径（`app.models`, `app.services`）的 import。

---

## 4. 循环依赖

### 严重: `app.api` ↔ `app.routers`

```
app/api/__init__.py:13  →  from app.routers import *
app/routers/__init__.py:3  →  from app.api import *
```

`app/api/__init__.py` 在 `__all__` 定义（第 15 行）之前就执行了跨包导入，此时模块尚未完成初始化。当前可运行仅因 `app.main` 跳过了 `__init__.py` 的 re-export 路径。

### 中度: `app.domain.services` ↔ `app.services`

```
app/domain/services/__init__.py:16  →  from app.services import *
app/services/__init__.py:3  →  from app.domain.services import *
```

### models 层安全

`app/models/__init__.py` → `app.domain.models` 单向，无循环。

---

## 5. 配置问题

### `.env.example` vs `.env` vs `.env.test`

- `.env.example` — 43 行，含分类注释
- `.env` — 3 个变量（JWT_SECRET_KEY, ADMIN_PASSWORD, CORS_ALLOW_ORIGINS）
- `.env.test` — 3 个变量（同上）

三套配置之间覆盖范围不一致，`.env` 缺失 `.env.example` 中的大部分配置项，运行时依赖 `config.py` 中的默认值。

### 废弃数据库文件

- `data/smarthome.db` — 0 字节
- `data/test_preset.db` — 0 字节

### Dockerfile `uv.lock*` 通配符

`Dockerfile:8` — `COPY pyproject.toml uv.lock* ./` 中 `uv.lock*` 匹配单个文件但用 glob 形式，实际无问题，仅略显冗余。

### root `main.py` 与 `app/main.py` 重复定义 `_dev`/`dev`

- 根目录 `main.py:8-9` — `dev()` 函数
- `app/main.py:280-283` — `_dev()` 函数，注册为 `[project.scripts] dev`

两处定义功能相同，根目录 `main.py` 实际未被任何脚本/命令引用，属于冗余文件。

---

## 修复优先级

| 优先级 | 项目 | 影响面 |
|---|---|---|
| P0 | 修复 `app.api` ↔ `app.routers` 循环依赖 | 运行时稳定性 |
| P1 | 清理 `app/routers/` 旧路由目录 | 可维护性 |
| P1 | 清理 `app/services/` 和 `app/models/` 兼容层 | 消除混淆 |
| P2 | 升级 `cryptography` 等过时依赖 | 安全性 |
| P2 | 实现或删除 `app/domain/repositories/` | 架构一致性 |
| P3 | 清理空目录和空数据库文件 | 整洁度 |
| P3 | 统一 `.env*` 配置项 | 环境一致性 |
| P3 | 删除根目录冗余 `main.py` | 整洁度 |

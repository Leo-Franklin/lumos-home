# 测试文件组织重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 tests/ 目录从扁平结构重构为按 unit/integration 分组，并统一命名风格（去掉 a1/a2/a3/a4 前缀）

**Architecture:** 将测试文件按 unit/integration 分类到子目录，合并重复测试文件，更新 import 路径，保持所有测试可运行

**Tech Stack:** pytest, Python 3.12, pytest-asyncio

---

## 文件映射总览

| 原文件 | 新位置 |
|--------|--------|
| `test_a1_presence_recording.py` + `test_recording_domain.py` | `tests/unit/domain/test_recording.py` |
| `test_presence_domain.py` | `tests/unit/domain/test_presence.py` |
| `test_a2_unknown_device.py` | `tests/unit/domain/test_unknown_devices.py` |
| `test_a3_camera_health.py` | `tests/unit/services/test_camera_health_service.py` |
| `test_a4_auto_cast.py` | `tests/unit/domain/test_auto_cast.py` |
| `test_auth_models.py` | `tests/unit/models/test_user.py` |
| `test_auth_schemas.py` | `tests/unit/models/test_auth_schemas.py` |
| `test_auth_email_token.py` | `tests/unit/utils/test_auth_email_tokens.py` |
| `test_email_service.py` | `tests/unit/services/test_email.py` |
| `test_api_auth.py` | `tests/integration/api/test_auth.py` |
| `test_analytics.py` | `tests/integration/api/test_analytics.py` |
| `test_recording_presets.py` | `tests/integration/test_recording_presets.py` |
| `test_api.py` | `tests/integration/api/test_devices.py` |
| `test_scanner.py` | `tests/unit/domain/test_scanner.py` |
| `test_recorder.py` | `tests/unit/domain/test_recorder.py` |
| `test_auth_backward_compat.py` | `tests/unit/utils/test_auth_backward_compat.py` |

---

## Task 1: 创建目录结构

**Files:**
- Create: `tests/unit/domain/__init__.py`
- Create: `tests/unit/models/__init__.py`
- Create: `tests/unit/services/__init__.py`
- Create: `tests/unit/utils/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/api/__init__.py`
- Create: `tests/e2e/__init__.py`

- [ ] **Step 1: 创建所有目录和 __init__.py 文件**

```bash
mkdir -p tests/unit/domain tests/unit/models tests/unit/services tests/unit/utils
mkdir -p tests/integration/api tests/e2e

# 创建所有 __init__.py 文件
touch tests/unit/domain/__init__.py
touch tests/unit/models/__init__.py
touch tests/unit/services/__init__.py
touch tests/unit/utils/__init__.py
touch tests/integration/__init__.py
touch tests/integration/api/__init__.py
touch tests/e2e/__init__.py
```

---

## Task 2: 移动并重命名单文件测试（无合并）

**Files:**
- Rename: `tests/test_a2_unknown_device.py` → `tests/unit/domain/test_unknown_devices.py`
- Rename: `tests/test_a3_camera_health.py` → `tests/unit/services/test_camera_health_service.py`
- Rename: `tests/test_a4_auto_cast.py` → `tests/unit/domain/test_auto_cast.py`
- Rename: `tests/test_email_service.py` → `tests/unit/services/test_email.py`
- Rename: `tests/test_auth_backward_compat.py` → `tests/unit/utils/test_auth_backward_compat.py`
- Rename: `tests/test_auth_schemas.py` → `tests/unit/models/test_auth_schemas.py`

- [ ] **Step 1: 移动 test_a2_unknown_device.py**

```bash
mv tests/test_a2_unknown_device.py tests/unit/domain/test_unknown_devices.py
```

- [ ] **Step 2: 移动 test_a3_camera_health.py**

```bash
mv tests/test_a3_camera_health.py tests/unit/services/test_camera_health_service.py
```

- [ ] **Step 3: 移动 test_a4_auto_cast.py**

```bash
mv tests/test_a4_auto_cast.py tests/unit/domain/test_auto_cast.py
```

- [ ] **Step 4: 移动 test_email_service.py**

```bash
mv tests/test_email_service.py tests/unit/services/test_email.py
```

- [ ] **Step 5: 移动 test_auth_backward_compat.py**

```bash
mv tests/test_auth_backward_compat.py tests/unit/utils/test_auth_backward_compat.py
```

- [ ] **Step 6: 移动 test_auth_schemas.py**

```bash
mv tests/test_auth_schemas.py tests/unit/models/test_auth_schemas.py
```

---

## Task 3: 合并 test_a1_presence_recording.py + test_recording_domain.py

**Files:**
- Create: `tests/unit/domain/test_recording.py`（合并后的文件）
- Delete: `tests/test_a1_presence_recording.py`
- Delete: `tests/test_recording_domain.py`

- [ ] **Step 1: 读取两个源文件内容**

读取 `tests/test_a1_presence_recording.py` 和 `tests/test_recording_domain.py`

- [ ] **Step 2: 创建合并后的 test_recording.py**

将 `test_recording_domain.py` 的内容（6个测试函数）添加到 `test_a1_presence_recording.py` 末尾，组成完整的 `test_recording.py`

```python
# tests/unit/domain/test_recording.py
# 内容合并自:
# - test_a1_presence_recording.py (3个测试: on_recording_complete_updates_recording_and_camera, on_recording_complete_triggers_dlna_cast, on_recording_failed_updates_recording)
# - test_recording_domain.py (6个测试: test_arrived_triggers_auto_start_recording, test_left_triggers_auto_stop_when_no_other_home_member, test_no_auto_record_cameras_no_callback)
# 共 9 个测试函数
```

- [ ] **Step 3: 删除原文件**

```bash
rm tests/test_a1_presence_recording.py tests/test_recording_domain.py
```

- [ ] **Step 4: 运行测试验证**

```bash
uv run pytest tests/unit/domain/test_recording.py -v
```

Expected: 所有 9 个测试 PASS

---

## Task 4: 移动 test_presence_domain.py → test_presence.py

**Files:**
- Rename: `tests/test_presence_domain.py` → `tests/unit/domain/test_presence.py`

- [ ] **Step 1: 移动文件**

```bash
mv tests/test_presence_domain.py tests/unit/domain/test_presence.py
```

- [ ] **Step 2: 运行测试验证**

```bash
uv run pytest tests/unit/domain/test_presence.py -v
```

---

## Task 5: 移动 test_auth_models.py → test_user.py

**Files:**
- Rename: `tests/test_auth_models.py` → `tests/unit/models/test_user.py`
- Update: `tests/unit/models/test_user.py` 中的 import 从 `app.models.user` 保持不变

- [ ] **Step 1: 移动文件**

```bash
mv tests/test_auth_models.py tests/unit/models/test_user.py
```

- [ ] **Step 2: 运行测试验证**

```bash
uv run pytest tests/unit/models/test_user.py -v
```

---

## Task 6: 移动 test_auth_email_token.py → test_auth_email_tokens.py

**Files:**
- Rename: `tests/test_auth_email_token.py` → `tests/unit/utils/test_auth_email_tokens.py`

- [ ] **Step 1: 移动文件**

```bash
mv tests/test_auth_email_token.py tests/unit/utils/test_auth_email_tokens.py
```

- [ ] **Step 2: 运行测试验证**

```bash
uv run pytest tests/unit/utils/test_auth_email_tokens.py -v
```

---

## Task 7: 移动 integration 测试

**Files:**
- Rename: `tests/test_api_auth.py` → `tests/integration/api/test_auth.py`
- Rename: `tests/test_analytics.py` → `tests/integration/api/test_analytics.py`
- Rename: `tests/test_recording_presets.py` → `tests/integration/test_recording_presets.py`
- Rename: `tests/test_api.py` → `tests/integration/api/test_devices.py`

- [ ] **Step 1: 移动 test_api_auth.py**

```bash
mv tests/test_api_auth.py tests/integration/api/test_auth.py
```

- [ ] **Step 2: 移动 test_analytics.py**

```bash
mv tests/test_analytics.py tests/integration/api/test_analytics.py
```

- [ ] **Step 3: 移动 test_recording_presets.py**

```bash
mv tests/test_recording_presets.py tests/integration/test_recording_presets.py
```

- [ ] **Step 4: 移动 test_api.py**

```bash
mv tests/test_api.py tests/integration/api/test_devices.py
```

---

## Task 8: 移动 test_scanner.py 和 test_recorder.py

**Files:**
- Rename: `tests/test_scanner.py` → `tests/unit/domain/test_scanner.py`
- Rename: `tests/test_recorder.py` → `tests/unit/domain/test_recorder.py`

- [ ] **Step 1: 移动 test_scanner.py**

```bash
mv tests/test_scanner.py tests/unit/domain/test_scanner.py
```

- [ ] **Step 2: 移动 test_recorder.py**

```bash
mv tests/test_recorder.py tests/unit/domain/test_recorder.py
```

---

## Task 9: 验证全部测试通过

- [ ] **Step 1: 运行全量测试**

```bash
uv run pytest tests/ -v
```

Expected: 所有 63 个测试 PASS

---

## Task 10: 提交 git

- [ ] **Step 1: 检查 git 状态**

```bash
git status
```

- [ ] **Step 2: 添加并提交**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: reorganize tests into unit/integration structure

- Group tests by unit/integration categories
- Remove a1/a2/a3/a4 prefixes, use semantic naming
- Merge test_a1_presence_recording.py + test_recording_domain.py
- Move auth tests to tests/unit/models/
- Move integration tests to tests/integration/api/

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## 目录结构（最终状态）

```
tests/
├── conftest.py
├── __init__.py
├── unit/
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── test_presence.py
│   │   ├── test_recording.py          # 合并自 a1 + recording_domain
│   │   ├── test_auto_cast.py           # 重命名自 a4
│   │   ├── test_unknown_devices.py     # 重命名自 a2
│   │   ├── test_scanner.py
│   │   └── test_recorder.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── test_user.py                # 重命名自 auth_models
│   │   └── test_auth_schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_email.py               # 重命名自 email_service
│   │   └── test_camera_health_service.py  # 重命名自 a3
│   └── utils/
│       ├── __init__.py
│       ├── test_auth_backward_compat.py
│       └── test_auth_email_tokens.py    # 重命名自 auth_email_token
└── integration/
    ├── __init__.py
    ├── api/
    │   ├── __init__.py
    │   ├── test_auth.py                 # 重命名自 api_auth
    │   ├── test_devices.py              # 重命名自 api
    │   └── test_analytics.py           # 重命名自 analytics
    └── test_recording_presets.py        # 重命名自 recording_presets
```

**注意**: `test_cleanup_phantoms.py` 保留在 `tests/` 根目录（维护脚本，非标准测试）

# 测试文件组织重构设计

**日期**: 2026-05-25
**状态**: 已批准

## 背景

当前 `tests/` 目录存在以下问题：
1. **前缀混乱**: `a1/a2/a3/a4` 前缀与其他 16 个文件的语义命名不一致
2. **平铺结构**: 所有 20 个测试文件都在顶层，没有子目录组织
3. **语义模糊**: 部分文件名不够自描述（如 `test_cleanup_phantoms`）
4. **重复覆盖**: `test_a1_presence_recording.py` 与 `test_presence_domain.py` + `test_recording_domain.py` 存在功能重叠

## 重构方案

### 最终目录结构

```
tests/
├── conftest.py                    # 全局 fixtures（保留）
├── __init__.py
├── unit/                          # 单元测试
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── test_presence.py       # ← test_presence_domain.py 合并
│   │   ├── test_recording.py      # ← test_recording_domain.py 合并
│   │   ├── test_auto_cast.py      # ← test_a4_auto_cast.py 重命名
│   │   ├── test_unknown_devices.py # ← test_a2_unknown_device.py 重命名
│   │   ├── test_camera_health.py  # ← test_a3_camera_health.py 重命名
│   │   ├── test_scanner.py
│   │   └── test_recorder.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── test_user.py            # ← test_auth_models.py 重命名（更明确）
│   │   └── test_auth_schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_email.py           # ← test_email_service.py 简化
│   │   └── test_camera_health_service.py  # ← test_a3_camera_health.py（同一文件拆出）
│   └── utils/
│       ├── __init__.py
│       ├── test_auth_backward_compat.py
│       └── test_auth_email_tokens.py  # ← test_auth_email_token.py 复数命名
├── integration/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_auth.py            # ← test_api_auth.py
│   │   ├── test_devices.py         # ← test_api.py 中设备相关部分（保留待定）
│   │   └── test_analytics.py      # ← test_analytics.py
│   └── test_recording_presets.py  # ← test_recording_presets.py（集成测试）
└── e2e/                            # 端到端测试（暂无，保留扩展性）
    ├── __init__.py
```

### 合并/重命名映射

| 原文件 | 新位置 | 操作 |
|--------|--------|------|
| `test_a1_presence_recording.py` | `tests/unit/domain/test_recording.py` | 与 `test_recording_domain.py` 合并 |
| `test_presence_domain.py` | `tests/unit/domain/test_presence.py` | 合并到新文件 |
| `test_recording_domain.py` | `tests/unit/domain/test_recording.py` | 与 `test_a1_presence_recording.py` 合并 |
| `test_a2_unknown_device.py` | `tests/unit/domain/test_unknown_devices.py` | 重命名（去掉 a2，改复数） |
| `test_a3_camera_health.py` | `tests/unit/services/test_camera_health_service.py` | 重命名（更明确） |
| `test_a4_auto_cast.py` | `tests/unit/domain/test_auto_cast.py` | 重命名（去掉 a4） |
| `test_auth_models.py` | `tests/unit/models/test_user.py` | 重命名（更通用） |
| `test_auth_schemas.py` | `tests/unit/models/test_auth_schemas.py` | 移动到 models/ |
| `test_auth_email_token.py` | `tests/unit/utils/test_auth_email_tokens.py` | 重命名（复数）+ 移动 |
| `test_email_service.py` | `tests/unit/services/test_email.py` | 简化命名 |
| `test_api_auth.py` | `tests/integration/api/test_auth.py` | 移动到 integration/api/ |
| `test_analytics.py` | `tests/integration/api/test_analytics.py` | 移动到 integration/api/ |
| `test_recording_presets.py` | `tests/integration/test_recording_presets.py` | 移动到 integration/ |
| `test_api.py` | `tests/integration/api/test_devices.py` | 重命名（待确认） |
| `test_scanner.py` | `tests/unit/domain/test_scanner.py` | 移动到 domain/ |
| `test_recorder.py` | `tests/unit/domain/test_recorder.py` | 移动到 domain/ |
| `test_cleanup_phantoms.py` | 删除或移至 `tests/utils/` | 需用户决定（维护脚本，非测试） |
| `test_auth_backward_compat.py` | `tests/unit/utils/test_auth_backward_compat.py` | 移动到 utils/ |

### 移除的前缀规则

- `a1_` → 合并到 `test_presence.py` 或 `test_recording.py`
- `a2_` → 改名为 `test_unknown_devices.py`
- `a3_` → 改名为 `test_camera_health_service.py`
- `a4_` → 改名为 `test_auto_cast.py`

### 测试分类说明

- **unit/**: 不依赖外部服务（数据库、HTTP）的纯单元测试，使用 mock
- **integration/**: 依赖数据库或需要启动 FastAPI 应用的集成测试
- **e2e/**: 端到端测试（目前暂无，预留）

## 实施步骤

1. 创建目标目录结构
2. 按映射表移动并重命名文件
3. 合并重复文件（`test_a1_presence_recording.py` + `test_recording_domain.py` → `test_recording.py`）
4. 更新合并后文件中的 import 路径
5. 运行 `uv run pytest tests/ -v` 验证所有测试通过
6. 提交 git

## 注意事项

- `conftest.py` 保持在 `tests/` 根目录
- 所有 `__init__.py` 文件为空文件，仅用于 Python 包标识
- `test_cleanup_phantoms.py` 实际是维护脚本而非测试，需用户确认是否保留
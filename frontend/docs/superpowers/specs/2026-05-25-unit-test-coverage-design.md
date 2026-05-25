# 单元测试补充方案

## 目标

为 smart-home-frontend 项目实现全面单元测试覆盖，策略为 **混合 Mock**：核心 store 逻辑用真实 API mock，API 模块本身用直接 mock。

## 测试文件结构

```
tests/
├── auth.test.js                    (已有)
├── views/
│   ├── LoginView.test.js           (已有)
│   └── SettingsView.test.js        (已有)
├── stores/
│   ├── auth.test.js                (已有)
│   ├── devices.test.js             (新建)
│   ├── cameras.test.js             (新建)
│   ├── members.test.js             (新建)
│   ├── dlna.test.js                (新建)
│   ├── locale.test.js              (新建)
│   └── notifications.test.js        (新建)
├── api/
│   ├── auth.test.js                (新建)
│   ├── devices.test.js             (新建)
│   ├── cameras.test.js             (新建)
│   ├── schedules.test.js           (新建)
│   ├── members.test.js             (新建)
│   ├── dlna.test.js                (新建)
│   ├── analytics.test.js           (新建)
│   ├── recordings.test.js          (新建)
│   └── system.test.js              (新建)
└── composables/
    ├── useWebSocket.test.js        (新建)
    └── useFormatDuration.test.js   (新建)
```

## Mock 架构

- 所有 store 测试：`vi.mock('@/api/index')` — mock axios 实例
- `useWebSocket` 测试：`vi.mock('ws')` 或直接构造 mock WebSocket
- `useFormatDuration` 测试：`vi.mock('vue-i18n')`
- View 测试：mock 对应的 store，保持现有模式

## 各模块测试要点

### Stores

| Store | 测试要点 |
|-------|---------|
| `auth` | login/logout/register/token 持久化、GitHub OAuth |
| `devices` | 分页、搜索防抖（300ms）、过滤、设备类型切换、scan 定时器（60s）、onScanCompleted |
| `cameras` | fetchCameras、loadPresets（404 容错）、addPreset、removePreset、setDefault、事件处理（onRecordingStarted/Stopped、onCameraOffline/Online） |
| `members` | fetchMembers、onPresenceEvent（arrived/left） |
| `dlna` | fetchDevices、discover（30s 超时）、onDiscoverCompleted、selectDevice、refreshStatus |
| `locale` | setLocale（同步 i18n + localStorage + API）、initLocale（API 失败回退） |
| `notifications` | 消息路由分发、各事件类型处理、ElNotification 调用、_scanRefreshTimer 防重入 |

### API 模块

验证每个导出函数：
- HTTP 方法正确（get/post/patch/put/delete）
- URL 路径正确
- 参数透传正确

### Composables

| Composable | 测试要点 |
|------------|---------|
| `useWebSocket` | 连接建立、token 注入、消息解析、重连逻辑（指数退避）、disconnect 清理、onUnmounted 自动断开 |
| `useFormatDuration` | 0秒、纯分钟、小时+分钟、null/undefined 处理 |

## 实施顺序

1. API 模块测试（9 个文件）
2. Composables 测试（2 个文件）
3. Stores 测试（7 个文件）
4. View 测试（如需要扩展）

## 验收标准

- 所有测试通过 (`pnpm test`)
- 测试覆盖所有导出的函数和公共方法
- 无未处理的 mock 警告

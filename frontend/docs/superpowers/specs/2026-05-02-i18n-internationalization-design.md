# i18n 国际化 — 设计规格说明书

**日期：** 2026-05-02  
**状态：** 待审核  
**目标：** 将项目中 ~200 条硬编码中文文本迁移至 vue-i18n，支持多语言（首发中英双语），架构可扩展。

---

## 1. 需求摘要

- 多语言支持，架构上预留扩展性，首批实现中文（zh-CN）和英文（en）
- 使用 vue-i18n 作为标准 i18n 库
- 翻译文件按页面/模块分文件组织
- Header 提供语言切换 UI
- 语言偏好通过后端接口持久化，localStorage 兜底
- Element Plus 组件库的文本同步切换

---

## 2. 整体架构

```
                 ┌──────────────────────────┐
                 │  Header 语言切换 (Dropdown) │
                 └──────────┬───────────────┘
                            │ 用户点击
                            ▼
                 ┌──────────────────────────┐
                 │  Pinia: useLocaleStore    │
                 │  - locale: 'zh-CN'|'en'  │
                 │  - setLocale() → 三路写入 │
                 └──────────┬───────────────┘
                            │ 驱动 locale 变化
                 ┌──────────▼───────────────┐
                 │    vue-i18n 实例           │
                 │  - messages: 模块级合并    │
                 │  - datetimeFormats        │
                 │  - Element Plus locale    │
                 └──────────┬───────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
    ┌──────────┐    ┌──────────┐    ┌──────────────┐
    │ 模板 $t() │    │ useI18n()│    │ Element Plus │
    │          │    │ (script) │    │  locale 同步  │
    └──────────┘    └──────────┘    └──────────────┘
```

**数据流：**  
用户点击切换 → store.setLocale(lang) → 同步更新 i18n.locale + localStorage + 后端 API  
→ vue-i18n 响应式更新所有 `$t()` → UI 即时切换，无页面刷新

---

## 3. 依赖

```json
{
  "dependencies": {
    "vue-i18n": "^11.x"
  }
}
```

现有依赖无需变更。`vue-i18n` 是 Vue 3 生态的官方 i18n 库。

---

## 4. 文件结构

```
src/
├── locales/
│   ├── index.js                 # i18n 实例创建 + Element Plus 集成
│   ├── zh-CN/
│   │   ├── common.js            # 通用：保存/取消/删除/刷新/在线/离线...
│   │   ├── layout.js            # 导航菜单、侧边栏、Header
│   │   ├── login.js             # 登录页
│   │   ├── dashboard.js         # 仪表板
│   │   ├── devices.js           # 设备列表 + DeviceCard
│   │   ├── cameras.js           # 摄像头管理 + CameraPlayer
│   │   ├── recordings.js        # 录像库
│   │   ├── schedule.js          # 录制计划 + CronSelector
│   │   ├── members.js           # 家庭成员
│   │   ├── analytics.js         # 数据分析
│   │   ├── topology.js          # 网络拓扑
│   │   ├── dlna.js              # 超级遥控器
│   │   └── settings.js          # 系统设置
│   └── en/                      # 英文翻译，同结构
│       └── ... (同上 12 个文件)
├── stores/
│   └── locale.js                # Pinia store：语言切换 + 后端持久化
├── composables/
│   └── useFormatDuration.js     # 统一时长格式化（替代各文件私有实现）
└── main.js                      # 注册 i18n + 调用 initLocale()
```

---

## 5. 核心模块设计

### 5.1 `src/locales/index.js` — i18n 实例

**职责：** 创建 vue-i18n 实例，合并所有模块翻译，配置 datetimeFormats，集成 Element Plus locale。

- 从所有 `zh-CN/*.js` 和 `en/*.js` 文件导入并合并 messages
- 定义 `datetimeFormats`（short、date 两种格式，中英文各自适配 24/12 小时制）
- 提供 `setElementLocale(i18n)` 函数：watch i18n.locale 变化，动态加载 Element Plus 对应语言包

### 5.2 `src/stores/locale.js` — 语言状态管理

**职责：** 管理当前语言状态，切换时三路同步写入。

| 操作 | 说明 |
|------|------|
| `initLocale()` | 应用启动时调用：先从 localStorage 读（无闪烁），再从后端拉取覆盖（多端同步） |
| `setLocale(lang)` | 1. 更新 i18n.locale 2. 写 localStorage 3. 异步 PUT `/user/profile` |

**异常处理：** 后端同步失败静默吞下，不影响前端切换。下次 `initLocale()` 时会用后端值纠正。

### 5.3 `src/composables/useFormatDuration.js` — 时长格式化

**职责：** 替代当前散落在 4 个文件中的私有 `formatDuration` 函数。

- 输入秒数，输出国际化时长文本（如 "2 小时 30 分钟" / "2h 30m"）
- 通过 `useI18n()` 获取 "小时"/"分钟" 的翻译

### 5.4 Header 语言切换 UI

**位置：** MainLayout.vue Header 右侧，WebSocket 状态和用户下拉之间。

**交互：**
- 显示当前语言标识（"中文" 或 "EN"）
- 点击展开下拉菜单，两个选项各有选中态高亮
- 切换即时生效，无 loading 状态

---

## 6. 翻译 Key 命名规范

**策略：扁平点分隔**，`模块.语义`。不使用深层嵌套对象。

| Key 模式 | 示例 | 说明 |
|----------|------|------|
| `common.xxx` | `common.save`, `common.cancel` | 跨模块通用词条 |
| `layout.xxx` | `layout.dashboard`, `layout.controlCenter` | 导航/侧边栏 |
| `<module>.xxx` | `devices.title`, `cameras.online` | 页面独有词条 |
| `common.deviceTypes.xxx` | `common.deviceTypes.camera` | 设备类型名称 |
| `schedule.cron*` | `schedule.cronEveryMinute` | Cron 描述 |

**插值语法：** 使用 vue-i18n 标准命名参数 `{name}`：
```js
devices.deleteConfirm: '确定删除设备 {name}？'
// 使用: $t('devices.deleteConfirm', { name: row.alias })
```

---

## 7. 动态字符串处理

### 7.1 时间格式化

**现状问题：** 5 个文件各有 `formatTime`/`fmtTime`，内部写死 `toLocaleString('zh-CN')`。

**解决方案：** 用 vue-i18n 的 `$d(value, 'short')` 替代所有私有 formatTime。datetimeFormats 中定义 `short` 和 `date` 两种预设，vue-i18n 根据当前 locale 自动选择格式。

迁移后删除各文件中的私有 `formatTime`/`fmtTime` 函数。

### 7.2 时长格式化

**现状问题：** 4 个文件各有 `formatDuration`，逻辑重复。

**解决方案：** 统一为 `useFormatDuration` composable。所有文件删除私有 `formatDuration`，改为调用该 composable。

### 7.3 Cron 描述（CronSelector.vue）

`formatCronDescription()` 中的 if/else 分支改为参数化的 i18n key：

```js
// 原来：
if (min === '*' && hour === '*') return '每分钟触发'
// 改为：
if (min === '*' && hour === '*') return t('schedule.cronEveryMinute')
```

星期简称（一/二/三.../日）放入翻译文件的 `schedule.weekdayShort` 对象中。

### 7.4 设备类型名称

**现状问题：** 设备类型 label 定义在 3 处，互不一致（DeviceCard 用英文，chartColors 用中文，TopologyView 用中文+emoji）。

**解决方案：** 统一到 `common.deviceTypes`。`chartColors.js` 的 `DEVICE_TYPE_LABELS` 改为从 i18n 获取；DeviceCard 和 TopologyView 的私有 TYPE_CONFIG 中删除 label 字段。

---

## 8. Element Plus 集成

安装 `vue-i18n` 后，Element Plus 的文本（分页、日历、空状态等）通过其内置的多语言支持同步切换：

- 在 `locales/index.js` 中 watch i18n locale 变化
- 动态 import Element Plus 对应语言包（`element-plus/es/locale/lang/zh-cn`、`element-plus/es/locale/lang/en`）
- 通过 ConfigProvider 或全局配置注入

---

## 9. 迁移策略（4 阶段）

### 阶段 1：基础设施

安装 `vue-i18n`，创建 `locales/index.js`、`stores/locale.js`、`common.js`（zh+en）、`useFormatDuration.js`，在 `main.js` 注册，Header 添加语言切换入口。

### 阶段 2：通用模块

迁移 `common.js` 完整词条、`layout.js`（MainLayout 导航）、共享组件（DeviceCard、ScanProgress、CameraPlayer、CronSelector）。

### 阶段 3：页面逐页迁移

按复杂度从低到高：Settings → Schedule → Login → Dashboard → Members → Recordings → Camera → Devices → Analytics → Topology → DLNA。

### 阶段 4：清理

删除所有私有 `formatTime`/`formatDuration`，统一 `DEVICE_TYPE_LABELS`，全量检查遗漏的硬编码中文。

**迁移规范（每个文件）：**
1. 在 `zh-CN/模块.js` 定义 key，值直接复制现有中文
2. 创建对应 `en/模块.js`（可先用机翻，标记 `// TODO: review`）
3. 模板替换：`"中文"` → `$t('模块.key')`
4. script 替换：`'中文'` → `t('模块.key')`
5. 验证中文界面零变化

**风险控制：**
- 每个页面独立 commit，便于回滚
- 阶段 1~2 完成后即可合入主分支，后续阶段不影响已有功能
- `zh-CN` 值原样复制，中文用户无感知

---

## 10. 边界条件 & 异常处理

| 场景 | 处理方式 |
|------|----------|
| 翻译 key 缺失 | vue-i18n 默认回退到 key 名本身，开发环境 console.warn |
| 后端 `/user/profile` 不可用 | `initLocale()` catch 后使用 localStorage 值 |
| 后端 PUT 语言偏好失败 | `setLocale()` catch 静默，本地已生效，下次 initLocale 时后端值覆盖 |
| 用户未登录时切换语言 | localStorage 仍生效，跳过后端同步 |
| 新语言扩展 | 在 `locales/` 下新建目录（如 `ja/`），复制 en/ 文件翻译即可 |
| Element Plus 语言包缺失 | 回退到英文 |

---

## 11. 文件清单（需修改）

| 文件 | 变更类型 |
|------|----------|
| `src/main.js` | 注册 i18n |
| `src/locales/index.js` | **新建** |
| `src/locales/zh-CN/*.js` (12 个) | **新建** |
| `src/locales/en/*.js` (12 个) | **新建** |
| `src/stores/locale.js` | **新建** |
| `src/composables/useFormatDuration.js` | **新建** |
| `src/layout/MainLayout.vue` | 导航文本 i18n + 语言切换入口 |
| `src/views/LoginView.vue` | 文本 i18n |
| `src/views/DashboardView.vue` | 文本 i18n + 时长格式化 |
| `src/views/DevicesView.vue` | 文本 i18n + 删除 formatTime |
| `src/views/CameraView.vue` | 文本 i18n + 删除 fmtTime |
| `src/views/RecordingsView.vue` | 文本 i18n + 删除 formatDuration |
| `src/views/ScheduleView.vue` | 文本 i18n |
| `src/views/MembersView.vue` | 文本 i18n + 删除 fmtTime/formatDuration |
| `src/views/AnalyticsView.vue` | 文本 i18n |
| `src/views/TopologyView.vue` | 文本 i18n + 删除 formatTime |
| `src/views/DLNAView.vue` | 文本 i18n |
| `src/views/SettingsView.vue` | 文本 i18n + 删除 formatUptime |
| `src/components/DeviceCard.vue` | 文本 i18n |
| `src/components/ScanProgress.vue` | 文本 i18n |
| `src/components/CameraPlayer.vue` | 文本 i18n |
| `src/components/CronSelector.vue` | 文本 i18n |
| `src/components/charts/chartColors.js` | DEVICE_TYPE_LABELS 改为从 i18n 获取 |

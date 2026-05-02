# i18n Internationalization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate ~200 hardcoded Chinese strings to vue-i18n with zh-CN/en support, extensible architecture, and Element Plus locale sync.

**Architecture:** vue-i18n instance with `import.meta.glob` auto-loading module files. Pinia store manages locale state with 3-way sync (i18n + localStorage + backend API). Element Plus integrated via `<el-config-provider>`. Translation files organized as `locales/{lang}/{module}.js` with flat dot-separated keys.

**Tech Stack:** Vue 3.5 + Vite 8 + Element Plus 2.13 + Pinia 3 + vue-i18n 11

---

## File Map

```
Create (28 files):
  src/locales/index.js                  — i18n instance, glob import, datetimeFormats, setElementLocale()
  src/locales/zh-CN/common.js           — shared UI strings
  src/locales/zh-CN/layout.js           — nav/sidebar/header
  src/locales/zh-CN/login.js            — login page
  src/locales/zh-CN/dashboard.js        — dashboard stats
  src/locales/zh-CN/devices.js          — device list + detail dialog
  src/locales/zh-CN/cameras.js          — camera management + player
  src/locales/zh-CN/recordings.js       — recording library + stats
  src/locales/zh-CN/schedule.js         — recording schedules + cron
  src/locales/zh-CN/members.js          — family members
  src/locales/zh-CN/analytics.js        — data analytics
  src/locales/zh-CN/topology.js         — network topology
  src/locales/zh-CN/dlna.js             — DLNA remote control
  src/locales/zh-CN/settings.js         — system settings
  src/locales/en/common.js              — (same 12 files for en)
  src/locales/en/layout.js
  src/locales/en/login.js
  src/locales/en/dashboard.js
  src/locales/en/devices.js
  src/locales/en/cameras.js
  src/locales/en/recordings.js
  src/locales/en/schedule.js
  src/locales/en/members.js
  src/locales/en/analytics.js
  src/locales/en/topology.js
  src/locales/en/dlna.js
  src/locales/en/settings.js
  src/stores/locale.js                  — Pinia locale store
  src/composables/useFormatDuration.js  — unified duration formatter

Modify (22 files):
  src/main.js                           — register i18n + Pinia
  src/App.vue                           — wrap with el-config-provider
  src/layout/MainLayout.vue             — i18n nav text + lang switcher
  src/views/LoginView.vue               — i18n text
  src/views/DashboardView.vue           — i18n text + useFormatDuration
  src/views/DevicesView.vue             — i18n text + delete formatTime
  src/views/CameraView.vue              — i18n text + delete fmtTime
  src/views/RecordingsView.vue          — i18n text + delete formatDuration/formatSize
  src/views/ScheduleView.vue            — i18n text
  src/views/MembersView.vue             — i18n text + delete fmtTime/fmtMinutes
  src/views/AnalyticsView.vue           — i18n text
  src/views/TopologyView.vue            — i18n text + delete formatTime
  src/views/DLNAView.vue                — i18n text
  src/views/SettingsView.vue            — i18n text + delete formatUptime
  src/components/DeviceCard.vue         — i18n text
  src/components/ScanProgress.vue       — i18n text
  src/components/CameraPlayer.vue       — i18n text
  src/components/CronSelector.vue       — i18n text + cron description
  src/components/charts/chartColors.js  — delete DEVICE_TYPE_LABELS
  src/components/charts/BaseChart.vue   — i18n empty text
  src/components/charts/HeatmapChart.vue— (if has CN text)
  src/components/charts/CalendarHeatmap.vue — (if has CN text)
```

---

### Task 1: Install vue-i18n

**Files:**
- Modify: `package.json`

- [ ] **Step 1: Install vue-i18n**

```bash
cd "D:/Project/Demo/smart_home/smart-home-frontend"
npm install vue-i18n@^11
```

- [ ] **Step 2: Verify install**

```bash
node -e "require('vue-i18n/package.json').version"
```

Expected: version 11.x.x printed.

- [ ] **Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: add vue-i18n dependency

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Create locales infrastructure (index.js + common.js zh/en)

**Files:**
- Create: `src/locales/index.js`
- Create: `src/locales/zh-CN/common.js`
- Create: `src/locales/en/common.js`

- [ ] **Step 1: Create zh-CN/common.js**

```js
// src/locales/zh-CN/common.js
export default {
  save: '保存',
  cancel: '取消',
  delete: '删除',
  edit: '编辑',
  close: '关闭',
  refresh: '刷新',
  confirm: '确认',
  search: '查询',
  create: '创建',
  download: '下载',
  play: '播放',
  pause: '暂停',
  stop: '停止',
  bind: '绑定',
  unbind: '解绑',
  detail: '详情',
  clear: '清除',
  all: '全部',
  loading: '加载中...',
  noData: '暂无数据',
  confirmDelete: '确认删除',
  operationFailed: '操作失败',
  online: '在线',
  offline: '离线',
  hour: '小时',
  minute: '分钟',
  unit_device: '台',
  unit_record: '条',
  deviceTypes: {
    camera: '摄像头',
    computer: '电脑',
    phone: '手机',
    iot: 'IoT',
    router: '路由器',
    tablet: '平板',
    tv: '电视',
    printer: '打印机',
    smart_speaker: '智能音箱',
    game_console: '游戏机',
    nas: 'NAS',
    wearable: '可穿戴',
    unknown: '未知',
  },
}
```

- [ ] **Step 2: Create en/common.js**

```js
// src/locales/en/common.js
export default {
  save: 'Save',
  cancel: 'Cancel',
  delete: 'Delete',
  edit: 'Edit',
  close: 'Close',
  refresh: 'Refresh',
  confirm: 'Confirm',
  search: 'Search',
  create: 'Create',
  download: 'Download',
  play: 'Play',
  pause: 'Pause',
  stop: 'Stop',
  bind: 'Bind',
  unbind: 'Unbind',
  detail: 'Detail',
  clear: 'Clear',
  all: 'All',
  loading: 'Loading...',
  noData: 'No data',
  confirmDelete: 'Confirm Delete',
  operationFailed: 'Operation failed',
  online: 'Online',
  offline: 'Offline',
  hour: 'h',
  minute: 'm',
  unit_device: '',
  unit_record: '',
  deviceTypes: {
    camera: 'Camera',
    computer: 'Computer',
    phone: 'Phone',
    iot: 'IoT',
    router: 'Router',
    tablet: 'Tablet',
    tv: 'TV',
    printer: 'Printer',
    smart_speaker: 'Smart Speaker',
    game_console: 'Game Console',
    nas: 'NAS',
    wearable: 'Wearable',
    unknown: 'Unknown',
  },
}
```

- [ ] **Step 3: Create locales/index.js**

```js
// src/locales/index.js
import { createI18n } from 'vue-i18n'

// Auto-load all module files via Vite glob import
const zhModules = import.meta.glob('./zh-CN/*.js', { eager: true, import: 'default' })
const enModules = import.meta.glob('./en/*.js', { eager: true, import: 'default' })

function buildMessages(modules) {
  const result = {}
  for (const [path, mod] of Object.entries(modules)) {
    const name = path.match(/\/([^/]+)\.js$/)[1]
    result[name] = mod
  }
  return result
}

const messages = {
  'zh-CN': buildMessages(zhModules),
  'en': buildMessages(enModules),
}

const datetimeFormats = {
  'zh-CN': {
    short: {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: false,
    },
    date: {
      year: 'numeric', month: '2-digit', day: '2-digit',
    },
  },
  'en': {
    short: {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: true,
    },
    date: {
      year: 'numeric', month: 'short', day: 'numeric',
    },
  },
}

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages,
  datetimeFormats,
})

export default i18n
```

- [ ] **Step 4: Verify files exist**

```bash
ls -la src/locales/index.js src/locales/zh-CN/common.js src/locales/en/common.js
```

- [ ] **Step 5: Commit**

```bash
git add src/locales/
git commit -m "feat: add i18n infrastructure with vue-i18n instance and common translations

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Create useFormatDuration composable

**Files:**
- Create: `src/composables/useFormatDuration.js`

- [ ] **Step 1: Create useFormatDuration.js**

```js
// src/composables/useFormatDuration.js
import { useI18n } from 'vue-i18n'

export function useFormatDuration() {
  const { t } = useI18n()

  function formatDuration(seconds) {
    if (!seconds) return `0 ${t('common.minute')}`
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h} ${t('common.hour')} ${m} ${t('common.minute')}`
    return `${m} ${t('common.minute')}`
  }

  return { formatDuration }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/composables/useFormatDuration.js
git commit -m "feat: add useFormatDuration composable for i18n-aware time formatting

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Create locale store + update main.js + update App.vue

**Files:**
- Create: `src/stores/locale.js`
- Modify: `src/main.js`
- Modify: `src/App.vue`

- [ ] **Step 1: Create stores/locale.js**

```js
// src/stores/locale.js
import { defineStore } from 'pinia'
import { useI18n } from 'vue-i18n'
import api from '@/api'

export const useLocaleStore = defineStore('locale', {
  state: () => ({
    locale: localStorage.getItem('app-locale') || 'zh-CN',
  }),

  actions: {
    setLocale(lang) {
      this.locale = lang
      // Sync to vue-i18n — useI18n is available when called from a component context,
      // but for store-level access we set the global instance
      const { global: i18n } = useI18n()
      i18n.locale.value = lang
      localStorage.setItem('app-locale', lang)
      // Async backend sync — silent on failure
      api.put('/user/profile', { language: lang }).catch(() => {})
    },

    async initLocale() {
      try {
        const { data } = await api.get('/user/profile')
        if (data.language && data.language !== this.locale) {
          this.setLocale(data.language)
        }
      } catch {
        // backend unavailable, use localStorage value
      }
    },
  },
})
```

- [ ] **Step 2: Update main.js**

Read `src/main.js` first, then replace with:

```js
// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import i18n from './locales'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus, { size: 'default' })
app.use(i18n)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
```

- [ ] **Step 3: Update App.vue to wrap with el-config-provider**

Read `src/App.vue` first. If the current App.vue is minimal (just `<router-view />`), replace with:

```vue
<!-- src/App.vue -->
<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import { useLocaleStore } from '@/stores/locale'

const { locale } = useI18n()
const localeStore = useLocaleStore()

localeStore.initLocale()

const elLocale = computed(() => (locale.value === 'zh-CN' ? zhCn : en))
</script>

<template>
  <el-config-provider :locale="elLocale">
    <router-view />
  </el-config-provider>
</template>
```

- [ ] **Step 4: Verify the app starts without errors**

```bash
npm run dev
```

Open browser, check console for errors. App should render (even though translations are incomplete — missing keys fall back to key name).

- [ ] **Step 5: Commit**

```bash
git add src/stores/locale.js src/main.js src/App.vue
git commit -m "feat: add locale store and integrate i18n with Element Plus locale sync

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Add language switcher to MainLayout + migrate navigation text

**Files:**
- Create: `src/locales/zh-CN/layout.js`
- Create: `src/locales/en/layout.js`
- Modify: `src/layout/MainLayout.vue`

- [ ] **Step 1: Create zh-CN/layout.js**

```js
// src/locales/zh-CN/layout.js
export default {
  brandName: '智能家居',
  controlCenter: '控制中心',
  dashboard: '仪表板',
  devices: '设备列表',
  analytics: '数据分析',
  topology: '网络拓扑',
  cameras: '摄像头',
  recordings: '录像库',
  schedule: '录制计划',
  members: '家庭成员',
  dlna: '超级遥控器',
  settings: '系统设置',
  connected: '已连接',
  disconnected: '未连接',
  logout: '退出登录',
}
```

- [ ] **Step 2: Create en/layout.js**

```js
// src/locales/en/layout.js
export default {
  brandName: 'Smart Home',
  controlCenter: 'Control Center',
  dashboard: 'Dashboard',
  devices: 'Devices',
  analytics: 'Analytics',
  topology: 'Topology',
  cameras: 'Cameras',
  recordings: 'Recordings',
  schedule: 'Schedule',
  members: 'Members',
  dlna: 'Remote Control',
  settings: 'Settings',
  connected: 'Connected',
  disconnected: 'Disconnected',
  logout: 'Logout',
}
```

- [ ] **Step 3: Modify MainLayout.vue — add script imports and language handler**

In the `<script setup>` section, after the existing imports add:

```js
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'

const { t } = useI18n()
const localeStore = useLocaleStore()

function switchLang(lang) {
  localeStore.setLocale(lang)
}
```

- [ ] **Step 4: Modify MainLayout.vue — replace template text with $t()**

Replace hardcoded Chinese in the template:

| Current text | Replace with |
|---|---|
| `智能家居` | `{{ $t('layout.brandName') }}` |
| `{{ connected ? '已连接' : '未连接' }}` | `{{ connected ? $t('layout.connected') : $t('layout.disconnected') }}` |
| `退出登录` | `{{ $t('layout.logout') }}` |
| `控制中心` | `{{ $t('layout.controlCenter') }}` |
| `仪表板` | `{{ $t('layout.dashboard') }}` |
| `设备列表` | `{{ $t('layout.devices') }}` |
| `数据分析` | `{{ $t('layout.analytics') }}` |
| `网络拓扑` | `{{ $t('layout.topology') }}` |
| `摄像头` | `{{ $t('layout.cameras') }}` |
| `录像库` | `{{ $t('layout.recordings') }}` |
| `录制计划` | `{{ $t('layout.schedule') }}` |
| `家庭成员` | `{{ $t('layout.members') }}` |
| `超级遥控器` | `{{ $t('layout.dlna') }}` |
| `系统设置` | `{{ $t('layout.settings') }}` |

- [ ] **Step 5: Add language switcher dropdown to header**

In the template, inside `.header-right`, between the `ws-status` div and the user dropdown, add:

```vue
<el-dropdown @command="switchLang" class="lang-switcher">
  <span class="lang-trigger">{{ localeStore.locale === 'zh-CN' ? '中文' : 'EN' }}</span>
  <template #dropdown>
    <el-dropdown-menu>
      <el-dropdown-item
        command="zh-CN"
        :class="{ 'is-active': localeStore.locale === 'zh-CN' }"
      >中文</el-dropdown-item>
      <el-dropdown-item
        command="en"
        :class="{ 'is-active': localeStore.locale === 'en' }"
      >English</el-dropdown-item>
    </el-dropdown-menu>
  </template>
</el-dropdown>
```

Add scoped styles:

```css
.lang-switcher {
  margin-right: 4px;
}
.lang-trigger {
  font-size: 12px;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out;
}
.lang-trigger:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}
```

- [ ] **Step 6: Verify — start dev server and test language switch**

```bash
npm run dev
```
- Open browser, check sidebar text is using i18n
- Click language switcher, toggle to English, verify sidebar changes
- Toggle back to Chinese, verify it restores

- [ ] **Step 7: Commit**

```bash
git add src/locales/zh-CN/layout.js src/locales/en/layout.js src/layout/MainLayout.vue
git commit -m "feat: add language switcher to header and i18n-ize navigation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Migrate LoginView

**Files:**
- Create: `src/locales/zh-CN/login.js`
- Create: `src/locales/en/login.js`
- Modify: `src/views/LoginView.vue`

- [ ] **Step 1: Create zh-CN/login.js**

```js
// src/locales/zh-CN/login.js
export default {
  title: '智能家居管理',
  subtitle: 'Smart Home Control Panel',
  username: '用户名',
  password: '密码',
  login: '登录',
  fillRequired: '请填写用户名和密码',
  loginFailed: '登录失败，请检查用户名和密码',
}
```

- [ ] **Step 2: Create en/login.js**

```js
// src/locales/en/login.js
export default {
  title: 'Smart Home Management',
  subtitle: 'Smart Home Control Panel',
  username: 'Username',
  password: 'Password',
  login: 'Login',
  fillRequired: 'Please enter username and password',
  loginFailed: 'Login failed, please check your credentials',
}
```

- [ ] **Step 3: Modify LoginView.vue script**

Add import:
```js
import { useI18n } from 'vue-i18n'
```

Inside `handleLogin`, replace:
```js
const { t } = useI18n()
// ...
ElMessage.warning('请填写用户名和密码')     // → ElMessage.warning(t('login.fillRequired'))
ElMessage.error(e.response?.data?.detail || '登录失败，请检查用户名和密码')  // → t('login.loginFailed')
```

- [ ] **Step 4: Modify LoginView.vue template**

Replace:
| Current | Replace with |
|---|---|
| `智能家居管理` | `{{ $t('login.title') }}` |
| `Smart Home Control Panel` | `{{ $t('login.subtitle') }}` |
| `placeholder="用户名"` | `:placeholder="$t('login.username')"` |
| `placeholder="密码"` | `:placeholder="$t('login.password')"` |
| `登录` | `{{ $t('login.login') }}` |

- [ ] **Step 5: Verify login page renders in both languages**

- [ ] **Step 6: Commit**

```bash
git add src/locales/zh-CN/login.js src/locales/en/login.js src/views/LoginView.vue
git commit -m "feat: i18n-ize LoginView

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Migrate DeviceCard + ScanProgress

**Files:**
- Modify: `src/components/DeviceCard.vue`
- Modify: `src/components/ScanProgress.vue`

- [ ] **Step 1: Migrate DeviceCard.vue — replace hardcoded text**

In the template, replace:

| Current | Replace with |
|---|---|
| `{{ device.alias \|\| '未命名' }}` | `{{ device.alias \|\| $t('devices.unnamed') }}` |
| `详情` | `{{ $t('common.detail') }}` |
| `编辑` | `{{ $t('common.edit') }}` |
| `删除` | `{{ $t('common.delete') }}` |

The `TYPE_CONFIG` labels are already in English and map to device type keys — replace label references with `$t('common.deviceTypes.' + device.device_type)` in the `typeConfig` function.

In `<script setup>`, update `typeConfig`:
```js
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

function typeConfig(type) {
  const cfg = TYPE_CONFIG[type] || TYPE_CONFIG.unknown
  return {
    ...cfg,
    label: t('common.deviceTypes.' + (type || 'unknown')),
  }
}
```

Note: Keep `TYPE_CONFIG` for color/icon mapping, but labels come from i18n now.

- [ ] **Step 2: Add 'unnamed' key to zh-CN/devices.js and en/devices.js**

In `zh-CN/devices.js` if not yet created, or append to it:
```js
// ensure these exist:
// unnamed: '未命名',
```

This will be handled in Task 16 when DevicesView is migrated and the full devices.js is created.

For now, add a minimal `zh-CN/devices.js`:
```js
// src/locales/zh-CN/devices.js (temporary — will be expanded in Task 16)
export default {
  unnamed: '未命名',
}
```

And `en/devices.js`:
```js
// src/locales/en/devices.js
export default {
  unnamed: 'Unnamed',
}
```

- [ ] **Step 3: Migrate ScanProgress.vue — replace hardcoded text**

Replace:
| Current | Replace with |
|---|---|
| `扫描中...` | `{{ $t('devices.scanning') }}` |
| `发现` | `{{ $t('devices.found') }}` |
| `台，` | (restructure as interpolation, or inline) |
| `新增` | `{{ $t('devices.newDevices') }}` |

The current text is "发现 X 台，新增 Y". Rewrite as:

```vue
{{ $t('devices.scanResult', { found: lastScan.data.found, new: lastScan.data.new }) }}
```

And add to `zh-CN/devices.js`:
```js
scanning: '扫描中...',
scanResult: '发现 {found} 台，新增 {new}',
```

Add to `en/devices.js`:
```js
scanning: 'Scanning...',
scanResult: 'Found {found}, {new} new',
```

- [ ] **Step 4: Verify DeviceCard and ScanProgress render correctly**

- [ ] **Step 5: Commit**

```bash
git add src/components/DeviceCard.vue src/components/ScanProgress.vue src/locales/zh-CN/devices.js src/locales/en/devices.js
git commit -m "feat: i18n-ize DeviceCard and ScanProgress components

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Migrate CameraPlayer

**Files:**
- Modify: `src/components/CameraPlayer.vue`

- [ ] **Step 1: Add i18n to CameraPlayer script**

Add import:
```js
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

- [ ] **Step 2: Replace error messages in script**

```js
error.value = t('cameras.streamLoadFailed')           // was: '实时画面加载失败...'
error.value = t('cameras.hlsLoadFailed')              // was: 'HLS 流加载失败...'

const msgs = {
  1: t('cameras.errAborted'),                         // was: '加载被中止'
  2: t('cameras.errNetwork'),                         // was: '网络错误...'
  3: t('cameras.errDecode'),                          // was: '视频解码失败...'
  4: t('cameras.errFormat'),                          // was: '视频格式不支持...'
}
error.value = msgs[code] || t('cameras.errGeneric', { code })
```

- [ ] **Step 3: Replace template text**

| Current | Replace with |
|---|---|
| `{{ mode === 'live' ? '连接摄像头中...' : '加载中...' }}` | `{{ mode === 'live' ? $t('cameras.connecting') : $t('common.loading') }}` |
| `在新标签页中打开查看详情` | `{{ $t('cameras.openInNewTab') }}` |

- [ ] **Step 4: Add camera player keys to zh-CN/cameras.js and en/cameras.js**

Create `zh-CN/cameras.js`:
```js
// src/locales/zh-CN/cameras.js (partial — will be expanded in Task 21)
export default {
  streamLoadFailed: '实时画面加载失败，请检查摄像头是否在线及 RTSP 地址是否正确',
  hlsLoadFailed: 'HLS 流加载失败，请确认转码已完成',
  errAborted: '加载被中止',
  errNetwork: '网络错误，无法加载视频',
  errDecode: '视频解码失败（可能是不支持的编码格式，如 H.265）',
  errFormat: '视频格式不支持或资源不可用',
  errGeneric: '视频加载失败（错误码 {code}）',
  connecting: '连接摄像头中...',
  openInNewTab: '在新标签页中打开查看详情',
}
```

Create `en/cameras.js`:
```js
// src/locales/en/cameras.js
export default {
  streamLoadFailed: 'Failed to load live stream, check if camera is online and RTSP address is correct',
  hlsLoadFailed: 'HLS stream failed to load, please confirm transcoding is complete',
  errAborted: 'Loading aborted',
  errNetwork: 'Network error, unable to load video',
  errDecode: 'Video decode failed (possibly unsupported codec, e.g. H.265)',
  errFormat: 'Video format not supported or resource unavailable',
  errGeneric: 'Video load failed (error code {code})',
  connecting: 'Connecting to camera...',
  openInNewTab: 'Open in new tab',
}
```

- [ ] **Step 5: Verify CameraPlayer renders errors correctly in both languages**

- [ ] **Step 6: Commit**

```bash
git add src/components/CameraPlayer.vue src/locales/zh-CN/cameras.js src/locales/en/cameras.js
git commit -m "feat: i18n-ize CameraPlayer component

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Migrate CronSelector + chartColors

**Files:**
- Create: `src/locales/zh-CN/schedule.js` (CronSelector uses schedule namespace)
- Create: `src/locales/en/schedule.js`
- Modify: `src/components/CronSelector.vue`
- Modify: `src/components/charts/chartColors.js`

- [ ] **Step 1: Create zh-CN/schedule.js with cron keys**

```js
// src/locales/zh-CN/schedule.js
export default {
  // Cron presets
  presetDaily2am: '每天凌晨 2:00',
  presetWeekday8am: '工作日早 8:00',
  presetDaily10pm: '每天晚上 22:00',
  presetEvery30min: '每 30 分钟',
  presetWeekendMidnight: '周末凌晨',
  presetHourly: '每小时整点',
  // Cron tabs
  tabPreset: '快速选择',
  tabCustom: '自定义时间',
  tabAdvanced: '高级 (Cron)',
  // Cron descriptions
  cronNotSet: '未设置',
  cronEveryMinute: '每分钟触发',
  cronEveryNMinute: '每 {n} 分钟触发',
  cronHourlyAt: '每小时第 {min} 分触发',
  cronDaily: '每天 {time} 触发',
  cronWeekday: '工作日 {time} 触发',
  cronWeekend: '周末 {time} 触发',
  cronCustom: '自定义：{expr}',
  // Weekday labels
  weekdayShort: { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 0: '日' },
  // UI
  triggerTime: '触发时间',
  weekday: '星期（全选 = 每天）',
  advPlaceholder: '分 时 日 月 周，如 0 2 * * *',
  advHint: '格式：分 小时 日 月 周几',
  trigger: ' 触发',
}
```

- [ ] **Step 2: Create en/schedule.js**

```js
// src/locales/en/schedule.js
export default {
  presetDaily2am: 'Daily at 2:00 AM',
  presetWeekday8am: 'Weekdays at 8:00 AM',
  presetDaily10pm: 'Daily at 10:00 PM',
  presetEvery30min: 'Every 30 minutes',
  presetWeekendMidnight: 'Weekends at midnight',
  presetHourly: 'Every hour',
  tabPreset: 'Presets',
  tabCustom: 'Custom',
  tabAdvanced: 'Advanced (Cron)',
  cronNotSet: 'Not set',
  cronEveryMinute: 'Every minute',
  cronEveryNMinute: 'Every {n} minutes',
  cronHourlyAt: 'Hourly at minute {min}',
  cronDaily: 'Daily at {time}',
  cronWeekday: 'Weekdays at {time}',
  cronWeekend: 'Weekends at {time}',
  cronCustom: 'Custom: {expr}',
  weekdayShort: { 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 0: 'Sun' },
  triggerTime: 'Trigger Time',
  weekday: 'Day of week (all = every day)',
  advPlaceholder: 'min hour day month weekday, e.g. 0 2 * * *',
  advHint: 'Format: min hour day month weekday',
  trigger: ' trigger',
}
```

- [ ] **Step 3: Migrate CronSelector.vue**

In `<script setup>`, add:
```js
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

Replace preset `label` values to use `t()` (these are static, so computed via a helper or inline). Since the presets array is defined at module scope (outside setup), restructure:

Move presets inside setup or use a computed:
```js
const presets = computed(() => [
  { label: t('schedule.presetDaily2am'),       cron: '0 2 * * *' },
  { label: t('schedule.presetWeekday8am'),     cron: '0 8 * * 1-5' },
  { label: t('schedule.presetDaily10pm'),      cron: '0 22 * * *' },
  { label: t('schedule.presetEvery30min'),     cron: '*/30 * * * *' },
  { label: t('schedule.presetWeekendMidnight'), cron: '0 0 * * 6,0' },
  { label: t('schedule.presetHourly'),         cron: '0 * * * *' },
])

const weekOptions = computed(() => [
  { label: t('schedule.weekdayShort.1'), value: 1 },
  { label: t('schedule.weekdayShort.2'), value: 2 },
  { label: t('schedule.weekdayShort.3'), value: 3 },
  { label: t('schedule.weekdayShort.4'), value: 4 },
  { label: t('schedule.weekdayShort.5'), value: 5 },
  { label: t('schedule.weekdayShort.6'), value: 6 },
  { label: t('schedule.weekdayShort.0'), value: 0 },
])

const tabOptions = computed(() => [
  { key: 'preset',   label: t('schedule.tabPreset') },
  { key: 'custom',   label: t('schedule.tabCustom') },
  { key: 'advanced', label: t('schedule.tabAdvanced') },
])
```

Update `formatCronDescription()` to use `t()`:
```js
function formatCronDescription(cron) {
  if (!cron) return t('schedule.cronNotSet')
  const preset = presets.value.find(p => p.cron === cron)
  if (preset) return preset.label + t('schedule.trigger')
  const parts = cron.split(/\s+/)
  if (parts.length !== 5) return t('schedule.cronCustom', { expr: cron })
  const [min, hour, , , dow] = parts
  if (min === '*' && hour === '*') return t('schedule.cronEveryMinute')
  if (min.startsWith('*/')) return t('schedule.cronEveryNMinute', { n: min.slice(2) })
  if (hour === '*') return t('schedule.cronHourlyAt', { min })
  const timeStr = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`
  if (dow === '*') return t('schedule.cronDaily', { time: timeStr })
  if (dow === '1-5' || dow === '1,2,3,4,5') return t('schedule.cronWeekday', { time: timeStr })
  if (dow === '6,0' || dow === '0,6') return t('schedule.cronWeekend', { time: timeStr })
  return t('schedule.cronCustom', { expr: cron })
}
```

Replace template text:
| Current | Replace with |
|---|---|
| `触发时间` | `{{ $t('schedule.triggerTime') }}` |
| `星期（全选 = 每天）` | `{{ $t('schedule.weekday') }}` |
| `placeholder="分 时 日 月 周，如 0 2 * * *"` | `:placeholder="$t('schedule.advPlaceholder')"` |
| `格式：分 小时 日 月 周几` | `{{ $t('schedule.advHint') }}` |

Template must also reference `presets`, `weekOptions`, `tabOptions` instead of the old static arrays.

- [ ] **Step 4: Update chartColors.js — delete DEVICE_TYPE_LABELS export**

Remove the `DEVICE_TYPE_LABELS` constant. Update `BaseChart.vue` references to use `$t('common.deviceTypes.' + type)` instead. Update `AnalyticsView.vue` to get labels from i18n.

- [ ] **Step 5: Verify CronSelector renders presets/tabs correctly in both languages**

- [ ] **Step 6: Commit**

```bash
git add src/locales/zh-CN/schedule.js src/locales/en/schedule.js src/components/CronSelector.vue src/components/charts/chartColors.js
git commit -m "feat: i18n-ize CronSelector and remove DEVICE_TYPE_LABELS from chartColors

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: Migrate SettingsView

**Files:**
- Create: `src/locales/zh-CN/settings.js`
- Create: `src/locales/en/settings.js`
- Modify: `src/views/SettingsView.vue`

- [ ] **Step 1: Create zh-CN/settings.js**

```js
// src/locales/zh-CN/settings.js
export default {
  title: '系统设置',
  healthStatus: '系统健康状态',
  componentStatus: '组件状态',
  overallStatus: '整体状态',
  version: '版本',
  uptime: '运行时长',
  uptimeFormat: '{h} 小时 {m} 分钟',
  healthy: '正常',
  abnormal: '异常',
  refresh: '刷新',
}
```

- [ ] **Step 2: Create en/settings.js**

```js
// src/locales/en/settings.js
export default {
  title: 'System Settings',
  healthStatus: 'System Health',
  componentStatus: 'Component Status',
  overallStatus: 'Overall Status',
  version: 'Version',
  uptime: 'Uptime',
  uptimeFormat: '{h}h {m}m',
  healthy: 'Healthy',
  abnormal: 'Abnormal',
  refresh: 'Refresh',
}
```

- [ ] **Step 3: Migrate SettingsView.vue**

Add `import { useI18n } from 'vue-i18n'` and `const { t } = useI18n()`.

Replace `formatUptime`:
```js
function formatUptime(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return t('settings.uptimeFormat', { h, m })
}
```

Template replacements:
| Current | Replace with |
|---|---|
| `系统设置` | `{{ $t('settings.title') }}` |
| `刷新` | `{{ $t('common.refresh') }}` |
| `系统健康状态` | `{{ $t('settings.healthStatus') }}` |
| `整体状态` | `{{ $t('settings.overallStatus') }}` |
| `版本` | `{{ $t('settings.version') }}` |
| `运行时长` | `{{ $t('settings.uptime') }}` |
| `组件状态` | `{{ $t('settings.componentStatus') }}` |
| `正常` / `异常` | `{{ $t('settings.healthy') }}` / `{{ $t('settings.abnormal') }}` |

- [ ] **Step 4: Verify SettingsView renders correctly in both languages**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/settings.js src/locales/en/settings.js src/views/SettingsView.vue
git commit -m "feat: i18n-ize SettingsView

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: Migrate ScheduleView

**Files:**
- Modify: `src/views/ScheduleView.vue`
- (schedule.js locale files already created in Task 9, append remaining keys)

- [ ] **Step 1: Append to zh-CN/schedule.js**

```js
// Add to existing zh-CN/schedule.js:
  title: '录制计划',
  newSchedule: '新建计划',
  editSchedule: '编辑计划',
  scheduleName: '计划名称',
  cameraMac: '摄像头 MAC',
  cronExpr: 'Cron 表达式',
  segmentDuration: '分段时长',
  segmentUnit: ' 分钟',
  status: '状态',
  actions: '操作',
  selectCamera: '选择摄像头',
  namePlaceholder: '如：夜间录制',
  segmentLabel: '分段时长(秒)',
  enabled: '是否启用',
  unnamed: '(未命名)',
  deleteConfirm: '确定删除计划「{name}」？',
  updated: '已更新',
  created: '已创建',
  deleted: '已删除',
```

- [ ] **Step 2: Append to en/schedule.js**

```js
// Add to existing en/schedule.js:
  title: 'Recording Schedule',
  newSchedule: 'New Schedule',
  editSchedule: 'Edit Schedule',
  scheduleName: 'Schedule Name',
  cameraMac: 'Camera MAC',
  cronExpr: 'Cron Expression',
  segmentDuration: 'Segment Duration',
  segmentUnit: ' min',
  status: 'Status',
  actions: 'Actions',
  selectCamera: 'Select camera',
  namePlaceholder: 'e.g. Night recording',
  segmentLabel: 'Segment Duration (sec)',
  enabled: 'Enabled',
  unnamed: '(unnamed)',
  deleteConfirm: 'Delete schedule "{name}"?',
  updated: 'Updated',
  created: 'Created',
  deleted: 'Deleted',
```

- [ ] **Step 3: Migrate ScheduleView.vue**

Add `import { useI18n } from 'vue-i18n'` and `const { t } = useI18n()`.

Replace in script:
```js
ElMessage.success(t('schedule.updated'))
ElMessage.success(t('schedule.created'))
ElMessage.error(e.response?.data?.error?.message || t('common.operationFailed'))
ElMessage.success(t('schedule.deleted'))
ElMessageBox.confirm(t('schedule.deleteConfirm', { name: row.name || row.cron_expr }), t('common.confirmDelete'), { type: 'warning' })
```

Template replacements:
| Current | Replace with |
|---|---|
| `录制计划` | `{{ $t('schedule.title') }}` |
| `新建计划` | `{{ $t('schedule.newSchedule') }}` |
| `计划名称` | `{{ $t('schedule.scheduleName') }}` |
| `摄像头 MAC` | `{{ $t('schedule.cameraMac') }}` |
| `Cron 表达式` | `{{ $t('schedule.cronExpr') }}` |
| `分段时长` | `{{ $t('schedule.segmentDuration') }}` |
| `{{ Math.floor(row.segment_duration / 60) }} 分钟` | `{{ Math.floor(row.segment_duration / 60) }}{{ $t('schedule.segmentUnit') }}` |
| `状态` | `{{ $t('schedule.status') }}` |
| `操作` | `{{ $t('schedule.actions') }}` |
| `选择摄像头` | `{{ $t('schedule.selectCamera') }}` |
| `如：夜间录制` | `{{ $t('schedule.namePlaceholder') }}` |
| `分段时长(秒)` | `{{ $t('schedule.segmentLabel') }}` |
| `是否启用` | `{{ $t('schedule.enabled') }}` |
| `(未命名)` | `{{ $t('schedule.unnamed') }}` |
| dialog title: `isEdit ? '编辑计划' : '新建计划'` | `isEdit ? $t('schedule.editSchedule') : $t('schedule.newSchedule')` |
| button text: `isEdit ? '保存' : '创建'` | `isEdit ? $t('common.save') : $t('common.create')` |

- [ ] **Step 4: Verify ScheduleView renders correctly with CronSelector in both languages**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/schedule.js src/locales/en/schedule.js src/views/ScheduleView.vue
git commit -m "feat: i18n-ize ScheduleView

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: Migrate DashboardView

**Files:**
- Create: `src/locales/zh-CN/dashboard.js`
- Create: `src/locales/en/dashboard.js`
- Modify: `src/views/DashboardView.vue`

- [ ] **Step 1: Create zh-CN/dashboard.js**

```js
// src/locales/zh-CN/dashboard.js
export default {
  title: '仪表板',
  refresh: '刷新',
  loadFailed: '加载失败',
  membersHome: '成员在家',
  cameras: '摄像头',
  networkDevices: '网络设备',
  todayRecordings: '今日录像',
  unknownDevices: '陌生设备',
  membersHomeDesc: '名成员当前在家',
  camerasOnline: '台在线',
  camerasRecording: ' 台录制中',
  devicesOnline: '台设备在线',
  todayAppeared: '台今日首次出现',
  onlineTrend: '24H 在线趋势',
  deviceTypes: '设备类型',
  newDevices: '近期新设备',
  zeroMinutes: '0 分钟',
  durationFormat: '{h} 小时 {m} 分钟',
  durationMinutesOnly: '{m} 分钟',
}
```

- [ ] **Step 2: Create en/dashboard.js**

```js
// src/locales/en/dashboard.js
export default {
  title: 'Dashboard',
  refresh: 'Refresh',
  loadFailed: 'Failed to load',
  membersHome: 'Members Home',
  cameras: 'Cameras',
  networkDevices: 'Network Devices',
  todayRecordings: 'Today\'s Recordings',
  unknownDevices: 'Unknown Devices',
  membersHomeDesc: 'members currently home',
  camerasOnline: ' online',
  camerasRecording: ' recording',
  devicesOnline: ' devices online',
  todayAppeared: ' first seen today',
  onlineTrend: '24H Online Trend',
  deviceTypes: 'Device Types',
  newDevices: 'Recent New Devices',
  zeroMinutes: '0 min',
  durationFormat: '{h}h {m}m',
  durationMinutesOnly: '{m}m',
}
```

- [ ] **Step 3: Migrate DashboardView.vue**

Add imports:
```js
import { useI18n } from 'vue-i18n'
import { useFormatDuration } from '@/composables/useFormatDuration'

const { t } = useI18n()
const { formatDuration } = useFormatDuration()
```

Replace `formatDuration` function (delete it, use composable).

Replace `error.value = e.response?.data?.detail || e.message || '加载失败'` with:
```js
error.value = e.response?.data?.detail || e.message || t('dashboard.loadFailed')
```

Template replacements:
| Current | Replace with |
|---|---|
| `仪表板` | `{{ $t('dashboard.title') }}` |
| `刷新` | `{{ $t('common.refresh') }}` |
| `成员在家` | `{{ $t('dashboard.membersHome') }}` |
| `摄像头` | `{{ $t('dashboard.cameras') }}` |
| `网络设备` | `{{ $t('dashboard.networkDevices') }}` |
| `今日录像` | `{{ $t('dashboard.todayRecordings') }}` |
| `陌生设备` | `{{ $t('dashboard.unknownDevices') }}` |
| `名成员当前在家` | `{{ $t('dashboard.membersHomeDesc') }}` |
| `台在线` | `{{ $t('dashboard.camerasOnline') }}` |
| ` 台录制中` | `{{ $t('dashboard.camerasRecording') }}` |
| `台设备在线` | `{{ $t('dashboard.devicesOnline') }}` |
| `条 · ` | `{{ $t('common.unit_record') }} · ` |
| `台今日首次出现` | `{{ $t('dashboard.todayAppeared') }}` |
| `24H 在线趋势` | `{{ $t('dashboard.onlineTrend') }}` |
| `设备类型` | `{{ $t('dashboard.deviceTypes') }}` |
| `近期新设备` | `{{ $t('dashboard.newDevices') }}` |

Note: `formatDuration` is now from composable and handles i18n internally.

- [ ] **Step 4: Verify DashboardView renders all stat cards correctly**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/dashboard.js src/locales/en/dashboard.js src/views/DashboardView.vue
git commit -m "feat: i18n-ize DashboardView with unified duration formatting

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: Migrate MembersView

**Files:**
- Create: `src/locales/zh-CN/members.js`
- Create: `src/locales/en/members.js`
- Modify: `src/views/MembersView.vue`

- [ ] **Step 1: Create zh-CN/members.js**

```js
// src/locales/zh-CN/members.js
export default {
  title: '家庭成员',
  addMember: '添加成员',
  editMember: '编辑成员',
  name: '姓名',
  status: '状态',
  lastArrived: '最近到家',
  lastLeft: '最近离家',
  webhook: 'Webhook',
  autoRecord: '自动录制',
  actions: '操作',
  home: '在家',
  away: '外出',
  bindDevice: '绑定设备',
  logs: '日志',
  stats: '统计',
  unbind: '解绑',
  arrived: '到家',
  left: '离家',
  bindDevicesTitle: '绑定设备 — {name}',
  logsTitle: '到家日志 — {name}',
  statsTitle: '在家统计 — {name}',
  statsTotal: '累计在家：{duration}',
  recent7Days: '近 7 天',
  recent30Days: '近 30 天',
  noData: '暂无数据',
  selectDevice: '选择设备',
  noteOptional: '备注（可选）',
  device: '设备',
  mac: 'MAC',
  note: '备注',
  triggeredBy: '触发设备 MAC',
  time: '时间',
  event: '事件',
  cameraCount: ' 台',
  namePlaceholder: '如：张三',
  avatarOptional: '可选',
  webhookPlaceholder: '到家/离家时推送，可选',
  autoRecordPlaceholder: '到家时自动启动录制（可选）',
  deleteConfirm: '确定删除成员「{name}」？关联数据也会一并删除。',
  updated: '已更新',
  created: '已创建',
  deleted: '已删除',
  bound: '已绑定',
  unbound: '已解绑',
  bindFailed: '绑定失败',
  statsFailed: '统计加载失败',
  zeroMinute: '0 分钟',
}
```

- [ ] **Step 2: Create en/members.js**

```js
// src/locales/en/members.js
export default {
  title: 'Family Members',
  addMember: 'Add Member',
  editMember: 'Edit Member',
  name: 'Name',
  status: 'Status',
  lastArrived: 'Last Arrived',
  lastLeft: 'Last Left',
  webhook: 'Webhook',
  autoRecord: 'Auto Record',
  actions: 'Actions',
  home: 'Home',
  away: 'Away',
  bindDevice: 'Bind Device',
  logs: 'Logs',
  stats: 'Stats',
  unbind: 'Unbind',
  arrived: 'Arrived',
  left: 'Left',
  bindDevicesTitle: 'Bound Devices — {name}',
  logsTitle: 'Presence Logs — {name}',
  statsTitle: 'Home Stats — {name}',
  statsTotal: 'Total at home: {duration}',
  recent7Days: 'Last 7 Days',
  recent30Days: 'Last 30 Days',
  noData: 'No data',
  selectDevice: 'Select device',
  noteOptional: 'Note (optional)',
  device: 'Device',
  mac: 'MAC',
  note: 'Note',
  triggeredBy: 'Trigger Device MAC',
  time: 'Time',
  event: 'Event',
  cameraCount: '',
  namePlaceholder: 'e.g. John Doe',
  avatarOptional: 'Optional',
  webhookPlaceholder: 'Push on arrival/departure, optional',
  autoRecordPlaceholder: 'Auto start recording on arrival (optional)',
  deleteConfirm: 'Delete member "{name}"? Associated data will also be removed.',
  updated: 'Updated',
  created: 'Created',
  deleted: 'Deleted',
  bound: 'Bound',
  unbound: 'Unbound',
  bindFailed: 'Bind failed',
  statsFailed: 'Failed to load stats',
  zeroMinute: '0 min',
}
```

- [ ] **Step 3: Migrate MembersView.vue**

Add imports:
```js
import { useI18n } from 'vue-i18n'
import { useFormatDuration } from '@/composables/useFormatDuration'

const { t } = useI18n()
const { formatDuration } = useFormatDuration()
```

Replace `fmtMinutes` — use `formatDuration` from composable instead. Delete `fmtMinutes`.

Replace `fmtTime` — use `$d(iso, 'short')` in template. Delete `fmtTime`.

Replace messages in script:
```js
// submitMember:
ElMessage.success(t('members.updated'))
ElMessage.success(t('members.created'))
ElMessage.error(e.response?.data?.detail || t('common.operationFailed'))

// handleDeleteMember:
await ElMessageBox.confirm(t('members.deleteConfirm', { name: row.name }), t('common.confirmDelete'), { type: 'warning' })
ElMessage.success(t('members.deleted'))

// handleBind:
ElMessage.success(t('members.bound'))
ElMessage.error(e.response?.data?.detail || t('members.bindFailed'))

// handleUnbind:
ElMessage.success(t('members.unbound'))

// fetchMemberStats:
ElMessage.error(e.response?.data?.detail || t('members.statsFailed'))
```

Template replacements — replace all hardcoded Chinese with `$t('members.xxx')` following the key mapping above. Key changes:

| Current | Replace with |
|---|---|
| `家庭成员` | `{{ $t('members.title') }}` |
| `添加成员` | `{{ $t('members.addMember') }}` |
| Table column labels (姓名/状态/最近到家/最近离家/Webhook/自动录制/操作) | `$t('members.xxx')` |
| `在家` / `外出` | `$t('members.home')` / `$t('members.away')` |
| Tooltip contents (绑定设备/日志/统计/编辑/删除) | `$t('members.xxx')` |
| Dialog titles | `$t('members.xxx', { name: ... })` |
| `formatTime`/`formatDuration` | Use `$d()` / `formatDuration()` |

- [ ] **Step 4: Verify MembersView renders correctly, dialogs open with correct titles**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/members.js src/locales/en/members.js src/views/MembersView.vue
git commit -m "feat: i18n-ize MembersView with unified time/duration formatting

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: Migrate RecordingsView

**Files:**
- Create: `src/locales/zh-CN/recordings.js`
- Create: `src/locales/en/recordings.js`
- Modify: `src/views/RecordingsView.vue`

- [ ] **Step 1: Create zh-CN/recordings.js**

```js
// src/locales/zh-CN/recordings.js
export default {
  title: '录像库',
  recordingStats: '录制统计',
  camera: '摄像头',
  date: '日期',
  query: '查询',
  all: '全部',
  allDates: '全部日期',
  cameraMac: '摄像头 MAC',
  startTime: '开始时间',
  duration: '时长',
  size: '大小',
  status: '状态',
  actions: '操作',
  playback: '录像回放',
  statsTitle: '录制统计',
  statsRange7d: '近 7 天',
  statsRange30d: '近 30 天',
  statsHint7d: '过去 7 天的录制汇总',
  statsHint30d: '过去 30 天的录制汇总',
  count: '录制次数',
  totalDuration: '总时长',
  totalSize: '总存储',
  noRecordings: '该时间段内暂无录制记录',
  play: '播放',
  recordingActive: '录制中，暂不可播放',
  recordingFailed: '录制失败，无可用文件',
  transcoding: '录像转码中，请稍候...',
  transcodeComplete: '转码完成，即将播放',
  transcodeFailed: '转码失败',
  deleteConfirm: '确定删除该录像？',
  deleted: '已删除',
  deleteFailed: '删除失败，请稍后重试',
  statusCompleted: 'completed',
  statusRecording: 'recording',
  statusFailed: 'failed',
  statusSynced: 'synced',
}
```

- [ ] **Step 2: Create en/recordings.js**

```js
// src/locales/en/recordings.js
export default {
  title: 'Recordings',
  recordingStats: 'Recording Stats',
  camera: 'Camera',
  date: 'Date',
  query: 'Search',
  all: 'All',
  allDates: 'All dates',
  cameraMac: 'Camera MAC',
  startTime: 'Start Time',
  duration: 'Duration',
  size: 'Size',
  status: 'Status',
  actions: 'Actions',
  playback: 'Playback',
  statsTitle: 'Recording Statistics',
  statsRange7d: 'Last 7 Days',
  statsRange30d: 'Last 30 Days',
  statsHint7d: 'Recording summary for the past 7 days',
  statsHint30d: 'Recording summary for the past 30 days',
  count: 'Recordings',
  totalDuration: 'Total Duration',
  totalSize: 'Total Size',
  noRecordings: 'No recordings in this period',
  play: 'Play',
  recordingActive: 'Recording in progress, cannot play',
  recordingFailed: 'Recording failed, no file available',
  transcoding: 'Transcoding, please wait...',
  transcodeComplete: 'Transcoding complete, starting playback',
  transcodeFailed: 'Transcoding failed',
  deleteConfirm: 'Delete this recording?',
  deleted: 'Deleted',
  deleteFailed: 'Delete failed, please try again later',
  statusCompleted: 'completed',
  statusRecording: 'recording',
  statusFailed: 'failed',
  statusSynced: 'synced',
}
```

- [ ] **Step 3: Migrate RecordingsView.vue**

Add imports:
```js
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
```

Replace `formatDuration` and `formatDurationLong` — use `useFormatDuration` composable. Replace `formatSize` — keep but use i18n for units? No, KB/MB are universal. Keep as-is.

Replace messages in script:
```js
ElMessage.info(t('recordings.transcoding'))
ElMessage.success(t('recordings.transcodeComplete'))
ElMessage.error(t('recordings.transcodeFailed'))
await ElMessageBox.confirm(t('recordings.deleteConfirm'), t('common.confirmDelete'), { type: 'warning' })
ElMessage.success(t('recordings.deleted'))
ElMessage.error(err.response?.data?.detail || t('recordings.deleteFailed'))
ElMessage.error(e.response?.data?.detail || t('recordings.statsFailed')) // in fetchStats
```

Template replacements — all labels, titles, placeholders to `$t('recordings.xxx')`.

- [ ] **Step 4: Verify RecordingsView renders correctly, play dialog and stats dialog work**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/recordings.js src/locales/en/recordings.js src/views/RecordingsView.vue
git commit -m "feat: i18n-ize RecordingsView

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 15: Migrate CameraView

**Files:**
- Modify: `src/views/CameraView.vue`
- (cameras.js locale files partially created in Task 8, expand them)

- [ ] **Step 1: Expand zh-CN/cameras.js** — append to the file from Task 8:

```js
// Add to existing src/locales/zh-CN/cameras.js:
  title: '摄像头管理',
  addCamera: '添加摄像头',
  editCamera: '编辑摄像头',
  deviceMac: '设备 MAC',
  onvifHost: 'ONVIF 地址',
  onvifPort: 'ONVIF 端口',
  onvifUser: 'ONVIF 用户名',
  onvifPassword: 'ONVIF 密码',
  rtspPort: 'RTSP 端口',
  rtspUrl: 'RTSP URL',
  streamProfile: '码流',
  online: '在线',
  offline: '离线',
  recording: '录制中',
  idle: '空闲',
  lastProbe: '上次探测',
  actions: '操作',
  onvifProbe: 'ONVIF 探测',
  livePreview: '实时预览',
  snapshot: '截图',
  hlsLive: 'HLS 直播',
  startRecord: '开始录制',
  stopRecord: '停止录制',
  selectDevice: '选择设备',
  onvifPlaceholder: '192.168.1.x',
  rtspUrlPlaceholder: '留空则由 ONVIF 探测自动填充',
  passwordPlaceholder: '不填则不修改',
  dlnaAutoCast: 'DLNA 自动投屏',
  dlnaPlaceholder: '录制完成后自动投屏到该设备（可选）',
  probeResult: 'ONVIF 探测结果',
  probing: '正在探测...',
  availableStreams: '可用码流',
  name: '名称',
  token: 'Token',
  rtspUrlWritten: '已自动写入 RTSP URL：{url}',
  liveTitle: '实时预览 — {host}',
  snapshotTitle: '截图 — {host}',
  hlsTitle: 'HLS 直播 — {host}',
  snapshotFailed: '截图失败，摄像头可能无信号',
  hlsStartFailed: 'HLS 直播启动失败',
  noRtspWarning: '该摄像头未配置 RTSP 地址，请先点击「ONVIF 探测」自动获取',
  noRtsp: '该摄像头未配置 RTSP 地址',
  added: '摄像头已添加',
  addFailed: '添加失败',
  saved: '已保存',
  saveFailed: '保存失败',
  deleted: '已删除',
  deleteConfirm: '确定删除摄像头 {host}？',
  recordStarted: '已发送开始录制指令',
  recordStopped: '已发送停止录制指令',
  mainStream: '主码流 (mainStream)',
  subStream: '子码流 (subStream)',
```

- [ ] **Step 2: Expand en/cameras.js** — append to the file from Task 8:

```js
// Add to existing src/locales/en/cameras.js:
  title: 'Camera Management',
  addCamera: 'Add Camera',
  editCamera: 'Edit Camera',
  deviceMac: 'Device MAC',
  onvifHost: 'ONVIF Address',
  onvifPort: 'ONVIF Port',
  onvifUser: 'ONVIF Username',
  onvifPassword: 'ONVIF Password',
  rtspPort: 'RTSP Port',
  rtspUrl: 'RTSP URL',
  streamProfile: 'Stream',
  online: 'Online',
  offline: 'Offline',
  recording: 'Recording',
  idle: 'Idle',
  lastProbe: 'Last Probe',
  actions: 'Actions',
  onvifProbe: 'ONVIF Probe',
  livePreview: 'Live Preview',
  snapshot: 'Snapshot',
  hlsLive: 'HLS Live',
  startRecord: 'Start Record',
  stopRecord: 'Stop Record',
  selectDevice: 'Select device',
  onvifPlaceholder: '192.168.1.x',
  rtspUrlPlaceholder: 'Leave blank to auto-fill via ONVIF probe',
  passwordPlaceholder: 'Leave blank to keep unchanged',
  dlnaAutoCast: 'DLNA Auto Cast',
  dlnaPlaceholder: 'Auto cast to this device after recording (optional)',
  probeResult: 'ONVIF Probe Result',
  probing: 'Probing...',
  availableStreams: 'Available Streams',
  name: 'Name',
  token: 'Token',
  rtspUrlWritten: 'RTSP URL auto-set: {url}',
  liveTitle: 'Live Preview — {host}',
  snapshotTitle: 'Snapshot — {host}',
  hlsTitle: 'HLS Live — {host}',
  snapshotFailed: 'Snapshot failed, camera may have no signal',
  hlsStartFailed: 'HLS live failed to start',
  noRtspWarning: 'Camera has no RTSP address configured, please run ONVIF probe first',
  noRtsp: 'Camera has no RTSP address configured',
  added: 'Camera added',
  addFailed: 'Add failed',
  saved: 'Saved',
  saveFailed: 'Save failed',
  deleted: 'Deleted',
  deleteConfirm: 'Delete camera {host}?',
  recordStarted: 'Record started',
  recordStopped: 'Record stopped',
  mainStream: 'Main Stream (mainStream)',
  subStream: 'Sub Stream (subStream)',
```

- [ ] **Step 3: Migrate CameraView.vue**

Add `import { useI18n } from 'vue-i18n'` and `const { t } = useI18n()`.

Replace `fmtTime` — use `$d(iso, 'short')` in template. Delete `fmtTime`.

Replace all ElMessage calls and dialog titles with `t('cameras.xxx')`.

Template — replace all table headers, button texts, dialog labels, tooltip contents with `$t('cameras.xxx')`.

- [ ] **Step 4: Verify CameraView renders, all dialogs open with correct titles, toasts work**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/cameras.js src/locales/en/cameras.js src/views/CameraView.vue
git commit -m "feat: i18n-ize CameraView

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 16: Migrate DevicesView

**Files:**
- Modify: `src/views/DevicesView.vue`
- (devices.js locale files partially created in Task 7, expand them)

- [ ] **Step 1: Expand zh-CN/devices.js**

```js
// Replace / expand existing src/locales/zh-CN/devices.js:
export default {
  title: '设备列表',
  scanNetwork: '扫描网络',
  heatmap: '活跃热力图',
  editDevice: '编辑设备',
  deviceDetail: '设备详情',
  deviceHeatmap: '设备活跃热力图',
  basicInfo: '基本信息',
  networkInfo: '网络信息',
  recordInfo: '记录信息',
  macAddress: 'MAC 地址',
  ipAddress: 'IP 地址',
  hostname: '主机名',
  deviceType: '设备类型',
  vendor: '厂商',
  openPorts: '开放端口',
  responseTime: '响应时间',
  firstSeen: '首次发现',
  lastSeen: '最后在线',
  notes: '备注',
  saveSuccess: '保存成功',
  saveFailed: '保存失败',
  deleteConfirm: '确定删除设备 {name}？',
  deleted: '已删除',
  noDevices: '暂无设备，请点击「扫描网络」',
  noDevicesOfType: '当前类型下暂无设备',
  onlineCount: '在线 {online} / 总计 {total}',
  unnamed: '未命名',
  scanning: '扫描中...',
  scanResult: '发现 {found} 台，新增 {new}',
  found: '发现',
  newDevices: '新增',
  mac: 'MAC',
  alias: '别名',
  type: '类型',
  heatmapFailed: '热力图加载失败',
  all: '全部',
  clear: '清除',
}
```

- [ ] **Step 2: Expand en/devices.js**

```js
// Replace / expand existing src/locales/en/devices.js:
export default {
  title: 'Devices',
  scanNetwork: 'Scan Network',
  heatmap: 'Activity Heatmap',
  editDevice: 'Edit Device',
  deviceDetail: 'Device Detail',
  deviceHeatmap: 'Device Activity Heatmap',
  basicInfo: 'Basic Info',
  networkInfo: 'Network Info',
  recordInfo: 'Record Info',
  macAddress: 'MAC Address',
  ipAddress: 'IP Address',
  hostname: 'Hostname',
  deviceType: 'Device Type',
  vendor: 'Vendor',
  openPorts: 'Open Ports',
  responseTime: 'Response Time',
  firstSeen: 'First Seen',
  lastSeen: 'Last Seen',
  notes: 'Notes',
  saveSuccess: 'Saved successfully',
  saveFailed: 'Save failed',
  deleteConfirm: 'Delete device {name}?',
  deleted: 'Deleted',
  noDevices: 'No devices found, click "Scan Network"',
  noDevicesOfType: 'No devices of this type',
  onlineCount: '{online} online / {total} total',
  unnamed: 'Unnamed',
  scanning: 'Scanning...',
  scanResult: 'Found {found}, {new} new',
  found: 'Found',
  newDevices: 'New',
  mac: 'MAC',
  alias: 'Alias',
  type: 'Type',
  heatmapFailed: 'Failed to load heatmap',
  all: 'All',
  clear: 'Clear',
}
```

- [ ] **Step 3: Migrate DevicesView.vue**

Add `import { useI18n } from 'vue-i18n'` and `const { t } = useI18n()`.

Replace `formatTime` — use `$d(val, 'short')` in template. Delete `formatTime`.

Replace `detailTypeLabel` computed — use `t('common.deviceTypes.' + ...)`.

Replace messages:
```js
ElMessage.success(t('devices.saveSuccess'))
ElMessage.error(t('devices.saveFailed'))
ElMessage.success(t('devices.deleted'))
ElMessage.error(e.response?.data?.detail || t('devices.heatmapFailed'))
ElMessageBox.confirm(t('devices.deleteConfirm', { name: row.alias || row.mac }), t('common.confirmDelete'), { type: 'warning' })
```

Template — all labels, titles, buttons to `$t('devices.xxx')`.

The `filterOptions` array labels are English (e.g. 'Camera', 'Computer') — these map to i18n device type labels. Update to use i18n:
```js
const { t } = useI18n()
const filterOptions = computed(() => [
  { value: 'camera', label: t('common.deviceTypes.camera'), hex: '#5E5CE6' },
  // ... etc
])
```

- [ ] **Step 4: Verify DevicesView renders, edit dialog, detail dialog, heatmap dialog work**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/devices.js src/locales/en/devices.js src/views/DevicesView.vue
git commit -m "feat: i18n-ize DevicesView with i18n device type labels

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 17: Migrate AnalyticsView

**Files:**
- Create: `src/locales/zh-CN/analytics.js`
- Create: `src/locales/en/analytics.js`
- Modify: `src/views/AnalyticsView.vue`
- Modify: `src/components/charts/BaseChart.vue`

- [ ] **Step 1: Create zh-CN/analytics.js**

```js
// src/locales/zh-CN/analytics.js
export default {
  title: '数据分析',
  subtitle: '家庭网络综合洞察',
  refreshAll: '刷新全部',
  heatmapTitle: '设备活跃时段',
  onlineTrend: '在线设备数量趋势',
  recordingsCalendar: '录像活动日历',
  deviceTypeDist: '设备类型分布',
  newDevicesTrend: '新设备发现趋势',
  activityByType: '各类型活跃时段（相对活跃度）',
  responseTime: '设备响应时延',
  responseTimeTitle: '设备响应时延（共 {n} 台）',
  stability: '设备在线稳定性',
  stabilityTitle: '设备在线稳定性（共 {n} 台）',
  last7Days: '近7天',
  last30Days: '近30天',
  noData: '暂无数据',
  loadFailed: '加载失败',
  heatmapFailed: '热力图加载失败',
  trendFailed: '在线趋势加载失败',
  typeFailed: '设备类型加载失败',
  rtFailed: '响应时延加载失败',
  calendarFailed: '录像日历加载失败',
  newDevFailed: '新设备趋势加载失败',
  stabilityFailed: '稳定性加载失败',
  activityFailed: '类型活跃加载失败',
}
```

- [ ] **Step 2: Create en/analytics.js**

```js
// src/locales/en/analytics.js
export default {
  title: 'Analytics',
  subtitle: 'Home Network Insights',
  refreshAll: 'Refresh All',
  heatmapTitle: 'Device Activity Heatmap',
  onlineTrend: 'Online Device Trend',
  recordingsCalendar: 'Recording Activity Calendar',
  deviceTypeDist: 'Device Type Distribution',
  newDevicesTrend: 'New Device Discovery Trend',
  activityByType: 'Activity by Type (relative)',
  responseTime: 'Device Response Time',
  responseTimeTitle: 'Device Response Time ({n} devices)',
  stability: 'Device Online Stability',
  stabilityTitle: 'Device Online Stability ({n} devices)',
  last7Days: 'Last 7 Days',
  last30Days: 'Last 30 Days',
  noData: 'No data',
  loadFailed: 'Failed to load',
  heatmapFailed: 'Failed to load heatmap',
  trendFailed: 'Failed to load online trend',
  typeFailed: 'Failed to load device types',
  rtFailed: 'Failed to load response time',
  calendarFailed: 'Failed to load recording calendar',
  newDevFailed: 'Failed to load new device trend',
  stabilityFailed: 'Failed to load stability',
  activityFailed: 'Failed to load activity by type',
}
```

- [ ] **Step 3: Migrate AnalyticsView.vue**

Add `import { useI18n } from 'vue-i18n'` and `const { t } = useI18n()`.

Replace all error message strings with `t('analytics.xxx')`.

Replace `rtTitle` and `stabilityTitle` computed — use `t('analytics.responseTimeTitle', { n: ... })`.

Template — all titles and labels to `$t('analytics.xxx')`.

- [ ] **Step 4: Migrate BaseChart.vue empty text**

Replace `暂无数据` with `{{ $t('common.noData') }}`.

- [ ] **Step 5: Verify AnalyticsView renders all charts, switching languages updates titles**

- [ ] **Step 6: Commit**

```bash
git add src/locales/zh-CN/analytics.js src/locales/en/analytics.js src/views/AnalyticsView.vue src/components/charts/BaseChart.vue
git commit -m "feat: i18n-ize AnalyticsView and BaseChart empty state

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 18: Migrate TopologyView

**Files:**
- Create: `src/locales/zh-CN/topology.js`
- Create: `src/locales/en/topology.js`
- Modify: `src/views/TopologyView.vue`

- [ ] **Step 1: Create zh-CN/topology.js**

```js
// src/locales/zh-CN/topology.js
export default {
  title: '网络拓扑',
  onlineCount: '在线 {online} / 共 {total} 台设备',
  scanning: '扫描中…',
  scanNetwork: '扫描网络',
  refresh: '刷新',
  online: '在线',
  offline: '离线',
  mac: 'MAC',
  ip: 'IP',
  hostname: '主机名',
  vendor: '厂商',
  lastSeen: '最后在线',
  owners: '归属成员',
  home: '在家',
  away: '外出',
  noDevices: '暂无设备数据，请点击「扫描网络」发现局域网设备',
  gateway: '家庭网关',
  loadFailed: '加载拓扑数据失败',
  // Device type labels — for legend/panel (keys match common.deviceTypes,
  // but topology has its own rendering with icons)
  // Actually, use common.deviceTypes directly in template
}
```

- [ ] **Step 2: Create en/topology.js**

```js
// src/locales/en/topology.js
export default {
  title: 'Network Topology',
  onlineCount: '{online} online / {total} total',
  scanning: 'Scanning...',
  scanNetwork: 'Scan Network',
  refresh: 'Refresh',
  online: 'Online',
  offline: 'Offline',
  mac: 'MAC',
  ip: 'IP',
  hostname: 'Hostname',
  vendor: 'Vendor',
  lastSeen: 'Last Seen',
  owners: 'Owners',
  home: 'Home',
  away: 'Away',
  noDevices: 'No device data, click "Scan Network" to discover LAN devices',
  gateway: 'Gateway',
  loadFailed: 'Failed to load topology data',
}
```

- [ ] **Step 3: Migrate TopologyView.vue**

Add `import { useI18n } from 'vue-i18n'` and `const { t } = useI18n()`.

Replace `formatTime` — use `$d(v, 'short')` in template. Delete `formatTime`.

The `TYPE_CONFIG` labels — use `common.deviceTypes` via i18n instead of the hardcoded Chinese strings. Keep the color and icon mappings, get labels from `t('common.deviceTypes.' + type)`.

```js
function typeLabel(type) {
  return t('common.deviceTypes.' + (type || 'unknown'))
}
```

Replace `ElMessage.error('加载拓扑数据失败')` with `ElMessage.error(t('topology.loadFailed'))`.

Replace `家庭网关` text with `t('topology.gateway')`.

Template — all labels, titles, tooltips to `$t('topology.xxx')` or `$t('common.deviceTypes.xxx')`.

- [ ] **Step 4: Verify TopologyView renders, legend and detail panel show correct labels**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/topology.js src/locales/en/topology.js src/views/TopologyView.vue
git commit -m "feat: i18n-ize TopologyView with i18n device types

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 19: Migrate DLNAView

**Files:**
- Create: `src/locales/zh-CN/dlna.js`
- Create: `src/locales/en/dlna.js`
- Modify: `src/views/DLNAView.vue`

- [ ] **Step 1: Create zh-CN/dlna.js**

```js
// src/locales/zh-CN/dlna.js
export default {
  title: '超级遥控器',
  searchDlna: '搜索 DLNA 设备',
  searching: '正在搜索...',
  foundDevices: '已发现设备',
  noDevices: '未发现 DLNA 设备',
  noDevicesHint: '点击「搜索 DLNA 设备」开始扫描',
  searchingHint: 'SSDP 广播搜索中…',
  selectPrompt: '请在左侧选择一个 DLNA 设备',
  currentDevice: '当前设备',
  castContent: '投屏内容',
  networkUrl: '网络 URL',
  localFile: '本地文件',
  urlPlaceholder: '输入媒体 URL，如 http://example.com/video.mp4',
  dragHint: '拖拽文件至此，或',
  clickUpload: '点击上传',
  uploadTip: '支持视频、音频、图片格式',
  startCast: '开始投屏',
  playbackControl: '播放控制',
  transportStatus: '传输状态',
  playing: '播放中',
  paused: '已暂停',
  stopped: '已停止',
  noMedia: '无媒体',
  transitioning: '切换中',
  castSent: '投屏指令已发送',
  fileCastSent: '文件投屏指令已发送',
  castFailed: '投屏失败',
  playSuccess: '播放',
  pausedSuccess: '已暂停',
  stoppedSuccess: '已停止',
  enterUrl: '请输入媒体 URL',
  selectFile: '请选择要投屏的文件',
  speed: '速度',
  statusCode: '状态码',
}
```

- [ ] **Step 2: Create en/dlna.js**

```js
// src/locales/en/dlna.js
export default {
  title: 'Remote Control',
  searchDlna: 'Search DLNA Devices',
  searching: 'Searching...',
  foundDevices: 'Discovered Devices',
  noDevices: 'No DLNA devices found',
  noDevicesHint: 'Click "Search DLNA Devices" to start scanning',
  searchingHint: 'SSDP broadcast search...',
  selectPrompt: 'Select a DLNA device from the left panel',
  currentDevice: 'Current Device',
  castContent: 'Cast Content',
  networkUrl: 'Network URL',
  localFile: 'Local File',
  urlPlaceholder: 'Enter media URL, e.g. http://example.com/video.mp4',
  dragHint: 'Drag file here, or',
  clickUpload: 'click to upload',
  uploadTip: 'Supports video, audio, and image formats',
  startCast: 'Start Casting',
  playbackControl: 'Playback Control',
  transportStatus: 'Transport Status',
  playing: 'Playing',
  paused: 'Paused',
  stopped: 'Stopped',
  noMedia: 'No Media',
  transitioning: 'Transitioning',
  castSent: 'Cast command sent',
  fileCastSent: 'File cast command sent',
  castFailed: 'Cast failed',
  playSuccess: 'Playing',
  pausedSuccess: 'Paused',
  stoppedSuccess: 'Stopped',
  enterUrl: 'Please enter a media URL',
  selectFile: 'Please select a file to cast',
  speed: 'Speed',
  statusCode: 'Status Code',
}
```

- [ ] **Step 3: Migrate DLNAView.vue**

Add `import { useI18n } from 'vue-i18n'` and `const { t } = useI18n()`.

Replace `stateLabel` computed — use `t('dlna.' + map[s])`.

Replace all ElMessage calls with `t('dlna.xxx')`.

Template — all labels, titles, buttons, placeholders to `$t('dlna.xxx')`.

- [ ] **Step 4: Verify DLNAView renders, device list and control panel work**

- [ ] **Step 5: Commit**

```bash
git add src/locales/zh-CN/dlna.js src/locales/en/dlna.js src/views/DLNAView.vue
git commit -m "feat: i18n-ize DLNAView

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 20: Cleanup — remove private helper functions + final check

**Files:**
- Modify: Multiple files (removing dead code)

- [ ] **Step 1: Remove private formatTime functions**

In each of these files, delete the private `formatTime`/`fmtTime` function (already replaced with `$d()` in templates):
- `src/views/DevicesView.vue` — delete `formatTime`
- `src/views/CameraView.vue` — delete `fmtTime`
- `src/views/MembersView.vue` — delete `fmtTime`
- `src/views/TopologyView.vue` — delete `formatTime`

- [ ] **Step 2: Remove private formatDuration functions**

Delete private `formatDuration`/`formatDurationLong`/`fmtMinutes`/`formatUptime` (already replaced with `useFormatDuration` composable):
- `src/views/DashboardView.vue` — delete `formatDuration`
- `src/views/MembersView.vue` — delete `fmtMinutes`
- `src/views/RecordingsView.vue` — delete `formatDuration`, `formatDurationLong`
- `src/views/SettingsView.vue` — delete `formatUptime`

- [ ] **Step 3: Final search — ensure no hardcoded Chinese remains**

```bash
cd "D:/Project/Demo/smart_home/smart-home-frontend"
grep -rPn '[\x{4e00}-\x{9fff}]' src/ --include='*.vue' --include='*.js' | grep -v 'locales/' | grep -v 'node_modules/'
```

Review any remaining matches. If any are in the `locales/` directory — those are the translation source files, which is correct. Any matches outside `locales/` should be investigated and migrated.

- [ ] **Step 4: Full app smoke test**

```bash
npm run dev
```

Visit each page, switch languages, verify:
- Navigation sidebar text switches
- Page titles switch
- Table headers switch
- Status tags switch
- Dialog titles switch
- Toast messages switch
- No console errors about missing translation keys

- [ ] **Step 5: Build check**

```bash
npm run build
```

Verify build succeeds without errors.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove private formatTime/formatDuration helpers, final i18n cleanup

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Plan Summary

| Phase | Tasks | New Files | Modified Files |
|-------|-------|-----------|----------------|
| 1. Infrastructure | 1-5 | 5 | 2 |
| 2. Common Components | 6-9 | 6 | 6 |
| 3. Page Migration | 10-19 | 10 | 10 |
| 4. Cleanup | 20 | 0 | 6+ |
| **Total** | **20** | **28** | **24+** |

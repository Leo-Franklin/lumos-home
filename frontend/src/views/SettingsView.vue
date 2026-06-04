<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh, User, Lock, Setting, Download, Delete,
  Sunny, Moon, Cellphone, ChatLineRound, VideoCamera,
  Camera as CameraIcon, Film, Connection, Failed,
} from '@element-plus/icons-vue'
import api from '@/api/index'
import { changePassword } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'
import { useDevicesStore } from '@/stores/devices'
import { useApiError } from '@/composables/useApiError'
import { exportCsv } from '@/composables/useCsvExport'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const localeStore = useLocaleStore()
const devicesStore = useDevicesStore()
const handleError = useApiError()

// ── Section 1: System status ─────────────────────────────────────
const health = ref(null)
const healthLoading = ref(false)
const healthError = ref('')

async function fetchHealth() {
  healthLoading.value = true
  healthError.value = ''
  try {
    const { data } = await api.get('/health')
    health.value = data
  } catch (e) {
    healthError.value = e?.response?.data?.detail || e?.message || t('common.operationFailed')
  } finally {
    healthLoading.value = false
  }
}

function formatUptime(s) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return t('settings.uptimeFormat', { h, m })
}

// ── Section 2: User info ────────────────────────────────────────
const loginTime = ref(null)

function readLoginTime() {
  const v = localStorage.getItem('login_time')
  if (v) loginTime.value = new Date(v)
}
readLoginTime()

const changePasswordDialog = ref(false)
const passwordForm = ref({ current: '', next: '', confirm: '' })
const passwordSubmitting = ref(false)
const passwordFormRef = ref(null)

const passwordRules = computed(() => ({
  current: [{ required: true, message: t('login.passwordRequired'), trigger: 'blur' }],
  next: [
    { required: true, message: t('login.passwordRequired'), trigger: 'blur' },
    {
      validator: (_, value, cb) => {
        if (value && value.length < 8) cb(new Error(t('settings.user.passwordTooShort')))
        else cb()
      },
      trigger: 'blur',
    },
  ],
  confirm: [
    { required: true, message: t('login.confirmPasswordRequired'), trigger: 'blur' },
    {
      validator: (_, value, cb) => {
        if (value !== passwordForm.value.next) cb(new Error(t('settings.user.passwordMismatch')))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}))

function openChangePassword() {
  passwordForm.value = { current: '', next: '', confirm: '' }
  changePasswordDialog.value = true
}

async function submitChangePassword() {
  if (!passwordFormRef.value) return
  try {
    await passwordFormRef.value.validate()
  } catch { return }
  passwordSubmitting.value = true
  try {
    await changePassword(passwordForm.value.current, passwordForm.value.next)
    ElMessage.success(t('settings.user.passwordChanged'))
    changePasswordDialog.value = false
  } catch (e) {
    handleError(e, 'settings.user.passwordChangeFailed')
  } finally {
    passwordSubmitting.value = false
  }
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm(t('settings.user.logoutConfirm'), t('settings.user.logout'), {
      type: 'warning',
    })
  } catch { return }
  auth.logout()
  ElMessage.success(t('settings.user.logout'))
  router.push('/login')
}

// ── Section 3: Preferences ──────────────────────────────────────
const prefLanguage = ref(localeStore.locale)
const prefEvents = ref({
  unknown_device_detected: true,
  camera_online: true,
  camera_offline: true,
  recording_completed: true,
  recording_failed: true,
  member_arrived: false,
  member_left: false,
  scan_completed: false,
})
const prefSound = ref(false)

const NOTIFY_EVENT_ICONS = {
  unknown_device_detected: Connection,
  camera_online: CameraIcon,
  camera_offline: CameraIcon,
  recording_completed: Film,
  recording_failed: Failed,
  member_arrived: User,
  member_left: User,
  scan_completed: Refresh,
}

const NOTIFY_EVENT_KEYS = [
  'unknown_device_detected',
  'camera_online',
  'camera_offline',
  'recording_completed',
  'recording_failed',
  'member_arrived',
  'member_left',
  'scan_completed',
]

function loadPreferences() {
  try {
    const raw = localStorage.getItem('pref:notify-events')
    if (raw) Object.assign(prefEvents.value, JSON.parse(raw))
    prefSound.value = localStorage.getItem('pref:notify-sound') === '1'
  } catch { /* ignore */ }
  prefLanguage.value = localeStore.locale
}

function persistPreferences() {
  localStorage.setItem('pref:notify-events', JSON.stringify(prefEvents.value))
  localStorage.setItem('pref:notify-sound', prefSound.value ? '1' : '0')
  // 立即应用语言切换
  if (prefLanguage.value !== localeStore.locale) {
    localeStore.setLocale(prefLanguage.value)
  }
  ElMessage.success(t('settings.preferences.saved'))
}

// ── Section 4: Data management ──────────────────────────────────
const exporting = ref({ devices: false, recordings: false })

async function doExportDevices() {
  exporting.value.devices = true
  try {
    const items = devicesStore.items?.length ? devicesStore.items : (await devicesStore.fetchDevices(), devicesStore.items)
    const headers = [
      t('devices.mac'), t('devices.alias'), t('devices.deviceType'),
      t('devices.ipAddress'), t('devices.vendor'), t('common.online'),
    ]
    const rows = (items || []).map((d) => [
      d.mac, d.alias || '', d.device_type || '',
      d.ip || '', d.vendor || '', d.is_online ? t('common.online') : t('common.offline'),
    ])
    const name = exportCsv(`devices-${Date.now()}.csv`, headers, rows)
    ElMessage.success(t('settings.data.exportSuccess', { name }))
  } catch (e) {
    handleError(e, 'settings.data.exportFailed')
  } finally {
    exporting.value.devices = false
  }
}

async function doExportRecordings() {
  exporting.value.recordings = true
  try {
    // 拉取所有页（最多 1000 条以避免阻塞 UI）
    const { data } = await api.get('/recordings', { params: { page: 1, page_size: 1000 } })
    const items = data.items || []
    const headers = [
      'ID', t('recordings.cameraMac'), t('recordings.file'),
      t('recordings.startTime'), t('recordings.duration'), t('recordings.size'),
      t('recordings.status'),
    ]
    const rows = items.map((r) => [
      r.id, r.camera_mac || '', r.file_name || '',
      r.started_at || '', r.duration || 0, r.file_size || 0, r.status || '',
    ])
    const name = exportCsv(`recordings-${Date.now()}.csv`, headers, rows)
    ElMessage.success(t('settings.data.exportSuccess', { name }))
  } catch (e) {
    handleError(e, 'settings.data.exportFailed')
  } finally {
    exporting.value.recordings = false
  }
}

async function clearCache() {
  try {
    await ElMessageBox.confirm(t('settings.data.cacheWarning'), t('settings.data.clearCache'), {
      type: 'warning',
    })
  } catch { return }
  // 保留 app-locale 但清掉其它键
  const keepLocale = localStorage.getItem('app-locale')
  localStorage.clear()
  if (keepLocale) localStorage.setItem('app-locale', keepLocale)
  ElMessage.success(t('settings.data.cacheCleared'))
  auth.logout()
  router.push('/login')
}

// 版本信息
const FRONTEND_VERSION = '0.0.0'
const backendVersion = ref('')
const backendVersionLoading = ref(false)

async function fetchBackendVersion() {
  backendVersionLoading.value = true
  try {
    const { data } = await api.get('/health')
    backendVersion.value = data?.version || data?.app_version || ''
  } catch {
    backendVersion.value = ''
  } finally {
    backendVersionLoading.value = false
  }
}

onMounted(() => {
  fetchHealth()
  fetchBackendVersion()
  loadPreferences()
})
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('settings.title') }}</h2>
        <span class="page-sub">{{ auth.username || $t('settings.user.username') }}</span>
      </div>
    </div>

    <!-- Section 1: System status -->
    <el-card class="settings-section" shadow="never">
      <template #header>
        <div class="section-header">
          <el-icon class="section-icon"><Setting /></el-icon>
          <span class="section-title">{{ $t('settings.healthStatus') }}</span>
          <el-button
            size="small"
            :icon="Refresh"
            :loading="healthLoading"
            @click="fetchHealth"
            class="section-action"
          >
            {{ $t('settings.refresh') }}
          </el-button>
        </div>
      </template>

      <el-alert v-if="healthError" :title="healthError" type="error" show-icon :closable="false" class="mb" />

      <el-skeleton v-else-if="healthLoading && !health" :rows="3" animated />

      <el-descriptions v-else-if="health" :column="2" border>
        <el-descriptions-item :label="$t('settings.overallStatus')">
          <el-tag :type="health.status === 'healthy' ? 'success' : 'danger'" size="small">
            {{ health.status === 'healthy' ? $t('settings.systemHealthy') : $t('settings.systemUnhealthy') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('settings.uptime')">
          {{ formatUptime(health.uptime_seconds) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Section 2: User info -->
    <el-card class="settings-section" shadow="never">
      <template #header>
        <div class="section-header">
          <el-icon class="section-icon"><User /></el-icon>
          <span class="section-title">{{ $t('settings.user.title') }}</span>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item :label="$t('settings.user.username')">
          {{ auth.username || '—' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('settings.user.role')">
          {{ auth.username === 'admin' ? $t('settings.user.roleAdmin') : $t('settings.user.roleUser') }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('settings.user.loginTime')">
          {{ loginTime ? loginTime.toLocaleString() : '—' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('settings.user.changePassword')">
          <el-button size="small" :icon="Lock" @click="openChangePassword">
            {{ $t('settings.user.changePassword') }}
          </el-button>
        </el-descriptions-item>
      </el-descriptions>

      <div class="section-actions">
        <el-button type="danger" plain :icon="Delete" @click="handleLogout">
          {{ $t('settings.user.logout') }}
        </el-button>
      </div>
    </el-card>

    <!-- Section 3: Preferences -->
    <el-card class="settings-section" shadow="never">
      <template #header>
        <div class="section-header">
          <el-icon class="section-icon"><Setting /></el-icon>
          <span class="section-title">{{ $t('settings.preferences.title') }}</span>
        </div>
      </template>

      <div class="pref-row">
        <div class="pref-label">
          <span class="pref-name">{{ $t('settings.preferences.language') }}</span>
          <span class="pref-desc">{{ $t('settings.preferences.languageDesc') }}</span>
        </div>
        <el-select v-model="prefLanguage" style="width: 180px">
          <el-option value="zh-CN" :label="t('login.langChinese')" />
          <el-option value="en" :label="t('login.langEnglish')" />
        </el-select>
      </div>

      <el-divider />

      <div class="pref-row">
        <div class="pref-label">
          <span class="pref-name">{{ $t('settings.preferences.notifications') }}</span>
          <span class="pref-desc">{{ $t('settings.preferences.notificationsDesc') }}</span>
        </div>
        <el-switch v-model="prefSound" />
      </div>

      <div class="pref-row sub">
        <div class="pref-label">
          <span class="pref-name">{{ $t('settings.preferences.notifyToasts') }}</span>
        </div>
        <div class="pref-event-grid">
          <el-checkbox
            v-for="key in NOTIFY_EVENT_KEYS"
            :key="key"
            v-model="prefEvents[key]"
            class="pref-event"
          >
            <el-icon class="pref-event-icon">
              <component :is="NOTIFY_EVENT_ICONS[key]" />
            </el-icon>
            <span>{{ $t(`settings.notificationEvents.${key}`) }}</span>
          </el-checkbox>
        </div>
      </div>

      <el-divider />

      <div class="pref-row">
        <div class="pref-label">
          <span class="pref-name">{{ $t('settings.preferences.theme') }}</span>
          <span class="pref-desc">{{ $t('settings.preferences.themeDesc') }}</span>
        </div>
        <el-radio-group disabled>
          <el-tooltip :content="$t('settings.preferences.themeComingSoon')">
            <el-radio-button value="dark">
              <el-icon><Moon /></el-icon>
              {{ $t('settings.preferences.themeDark') }}
            </el-radio-button>
          </el-tooltip>
          <el-tooltip :content="$t('settings.preferences.themeComingSoon')">
            <el-radio-button value="light">
              <el-icon><Sunny /></el-icon>
              {{ $t('settings.preferences.themeLight') }}
            </el-radio-button>
          </el-tooltip>
        </el-radio-group>
      </div>

      <div class="section-actions">
        <el-button type="primary" @click="persistPreferences">
          {{ $t('common.save') }}
        </el-button>
      </div>
    </el-card>

    <!-- Section 4: Data management -->
    <el-card class="settings-section" shadow="never">
      <template #header>
        <div class="section-header">
          <el-icon class="section-icon"><Download /></el-icon>
          <span class="section-title">{{ $t('settings.data.exportTitle') }}</span>
        </div>
      </template>

      <p class="section-desc">{{ $t('settings.data.exportDesc') }}</p>

      <div class="action-row">
        <el-button
          :loading="exporting.devices"
          :icon="Cellphone"
          @click="doExportDevices"
        >
          {{ $t('settings.data.exportDevices') }}
        </el-button>
        <el-button
          :loading="exporting.recordings"
          :icon="VideoCamera"
          @click="doExportRecordings"
        >
          {{ $t('settings.data.exportRecordings') }}
        </el-button>
      </div>
    </el-card>

    <el-card class="settings-section" shadow="never">
      <template #header>
        <div class="section-header">
          <el-icon class="section-icon"><Delete /></el-icon>
          <span class="section-title">{{ $t('settings.data.cacheTitle') }}</span>
        </div>
      </template>

      <p class="section-desc">{{ $t('settings.data.cacheDesc') }}</p>

      <el-button type="danger" plain :icon="Delete" @click="clearCache">
        {{ $t('settings.data.clearCache') }}
      </el-button>
    </el-card>

    <el-card class="settings-section" shadow="never">
      <template #header>
        <div class="section-header">
          <el-icon class="section-icon"><ChatLineRound /></el-icon>
          <span class="section-title">{{ $t('settings.data.versionsTitle') }}</span>
        </div>
      </template>

      <el-descriptions :column="1" border>
        <el-descriptions-item :label="$t('settings.data.frontendVersion')">
          <span class="mono">v{{ FRONTEND_VERSION }}</span>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('settings.data.backendVersion')">
          <span v-if="backendVersionLoading" class="text-muted">
            {{ $t('settings.data.loadingBackendVersion') }}
          </span>
          <span v-else-if="backendVersion" class="mono">v{{ backendVersion }}</span>
          <span v-else class="text-muted">—</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Change password dialog -->
    <el-dialog
      v-model="changePasswordDialog"
      :title="$t('settings.user.changePasswordTitle')"
      width="440px"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="120px"
        @submit.prevent
      >
        <el-form-item :label="$t('settings.user.currentPassword')" prop="current">
          <el-input v-model="passwordForm.current" type="password" show-password />
        </el-form-item>
        <el-form-item :label="$t('settings.user.newPassword')" prop="next">
          <el-input v-model="passwordForm.next" type="password" show-password />
        </el-form-item>
        <el-form-item :label="$t('settings.user.confirmNewPassword')" prop="confirm">
          <el-input v-model="passwordForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePasswordDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="passwordSubmitting" @click="submitChangePassword">
          {{ $t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.settings-section {
  margin-bottom: var(--space-6);
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-border) !important;
  border-radius: var(--radius-lg) !important;
}
.settings-section :deep(.el-card__header) {
  padding: 14px 20px;
  border-bottom: 1px solid var(--color-border-subtle);
}
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.section-icon {
  font-size: 16px;
  color: var(--color-primary);
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  flex: 1;
}
.section-action {
  margin-left: auto;
}
.section-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4);
  line-height: 1.5;
}
.section-actions {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.pref-row {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-2) 0;
}
.pref-row.sub {
  align-items: flex-start;
  padding-left: 0;
}
.pref-label {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pref-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
}
.pref-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
}
.pref-event-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 1fr));
  gap: 8px 16px;
  flex: 2;
}
.pref-event {
  display: flex;
  align-items: center;
  font-size: 13px;
}
.pref-event-icon {
  margin-right: 6px;
  color: var(--color-primary);
  font-size: 14px;
}
.action-row {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.mb {
  margin-bottom: var(--space-4);
}
.mono {
  font-family: var(--font-mono);
  font-size: 12px;
}
.text-muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh,
  User,
  Lock,
  Setting,
  Bell,
  FolderOpened,
  Monitor,
  ArrowRight,
  DataAnalysis,
  Calendar,
  Connection,
} from '@element-plus/icons-vue'
import api from '@/api/index'
import { changePassword } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'
import { useDevicesStore } from '@/stores/devices'
import { useApiError } from '@/composables/useApiError'
import { exportCsv } from '@/composables/useCsvExport'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import {
  loadNotifyEvents,
  loadNotifySound,
  saveNotifyEvents,
  saveNotifySound,
} from '@/composables/useNotificationPreferences'
import SettingsNav from '@/components/settings/SettingsNav.vue'
import SettingsSection from '@/components/settings/SettingsSection.vue'
import SettingsHealthPanel from '@/components/settings/SettingsHealthPanel.vue'
import SettingsPreferencesPanel from '@/components/settings/SettingsPreferencesPanel.vue'
import SettingsDataPanel from '@/components/settings/SettingsDataPanel.vue'
import { pickAppVersion } from '@/constants/appMeta'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const localeStore = useLocaleStore()
const devicesStore = useDevicesStore()
const handleError = useApiError()
const { connected } = useConnectionStatus()

// ── Navigation ───────────────────────────────────────────────────
const NAV_ITEMS = computed(() => [
  { id: 'account', label: t('settings.nav.account'), icon: User },
  { id: 'preferences', label: t('settings.nav.preferences'), icon: Bell },
  { id: 'system', label: t('settings.nav.system'), icon: Monitor },
  { id: 'data', label: t('settings.nav.data'), icon: FolderOpened },
])

const activeSection = ref('account')
let sectionObserver = null

function scrollToSection(id) {
  const el = document.getElementById(id)
  if (!el) return
  activeSection.value = id
  el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function setupSectionObserver() {
  const ids = NAV_ITEMS.value.map((item) => item.id)
  sectionObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
      if (visible.length) activeSection.value = visible[0].target.id
    },
    { rootMargin: '-20% 0px -55% 0px', threshold: [0.15, 0.4, 0.6] },
  )
  ids.forEach((id) => {
    const el = document.getElementById(id)
    if (el) sectionObserver.observe(el)
  })
}

// ── System health ────────────────────────────────────────────────
const health = ref(null)
const healthLoading = ref(false)
const healthError = ref('')

async function fetchHealth() {
  healthLoading.value = true
  healthError.value = ''
  try {
    const { data } = await api.get('/health')
    health.value = data
    backendVersion.value = pickAppVersion(data)
  } catch (e) {
    const payload = e?.response?.data
    if (payload && typeof payload === 'object' && payload.checks) {
      health.value = payload
      backendVersion.value = pickAppVersion(payload)
    } else {
      healthError.value =
        (typeof payload?.detail === 'string' ? payload.detail : null) ||
        e?.message ||
        t('common.operationFailed')
    }
  } finally {
    healthLoading.value = false
  }
}

// ── User account ─────────────────────────────────────────────────
const loginTime = ref(null)

function readLoginTime() {
  const v = localStorage.getItem('login_time')
  if (v) loginTime.value = new Date(v)
}
readLoginTime()

const isAdmin = computed(() => auth.username === 'admin')

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
  } catch {
    return
  }
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
  } catch {
    return
  }
  auth.logout()
  ElMessage.success(t('settings.user.logout'))
  router.push('/login')
}

// ── Preferences (auto-persist) ───────────────────────────────────
const prefLanguage = ref(localeStore.locale)
const prefEvents = ref(loadNotifyEvents())
const prefSound = ref(loadNotifySound())

function persistLanguage(lang) {
  prefLanguage.value = lang
  if (lang !== localeStore.locale) localeStore.setLocale(lang)
}

function persistEvents(events) {
  prefEvents.value = events
  saveNotifyEvents(events)
}

function persistSound(value) {
  prefSound.value = value
  saveNotifySound(value)
}

// ── Data export / cache ──────────────────────────────────────────
const exporting = ref({ devices: false, recordings: false })
const backendVersion = ref('')

async function doExportDevices() {
  exporting.value.devices = true
  try {
    const items = devicesStore.items?.length
      ? devicesStore.items
      : (await devicesStore.fetchDevices(), devicesStore.items)
    const headers = [
      t('devices.mac'),
      t('devices.alias'),
      t('devices.deviceType'),
      t('devices.ipAddress'),
      t('devices.vendor'),
      t('common.online'),
    ]
    const rows = (items || []).map((d) => [
      d.mac,
      d.alias || '',
      d.device_type || '',
      d.ip || '',
      d.vendor || '',
      d.is_online ? t('common.online') : t('common.offline'),
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
    const { data } = await api.get('/recordings', { params: { page: 1, page_size: 1000 } })
    const items = data.items || []
    const headers = [
      'ID',
      t('recordings.cameraMac'),
      t('recordings.file'),
      t('recordings.startTime'),
      t('recordings.duration'),
      t('recordings.size'),
      t('recordings.status'),
    ]
    const rows = items.map((r) => [
      r.id,
      r.camera_mac || '',
      r.file_name || '',
      r.started_at || '',
      r.duration || 0,
      r.file_size || 0,
      r.status || '',
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
  } catch {
    return
  }
  const keepLocale = localStorage.getItem('app-locale')
  localStorage.clear()
  if (keepLocale) localStorage.setItem('app-locale', keepLocale)
  ElMessage.success(t('settings.data.cacheCleared'))
  auth.logout()
  router.push('/login')
}

const QUICK_LINKS = computed(() => [
  {
    to: '/devices',
    label: t('layout.devices'),
    desc: t('settings.quickLinks.devices'),
    icon: Connection,
  },
  {
    to: '/schedule',
    label: t('layout.schedule'),
    desc: t('settings.quickLinks.schedule'),
    icon: Calendar,
  },
  {
    to: '/analytics',
    label: t('layout.analytics'),
    desc: t('settings.quickLinks.analytics'),
    icon: DataAnalysis,
  },
])

const headerSummary = computed(() => {
  if (health.value?.status === 'healthy') return t('settings.headerHealthy')
  if (health.value) return t('settings.headerDegraded')
  return t('settings.subtitle')
})

onMounted(() => {
  fetchHealth()
  requestAnimationFrame(() => setupSectionObserver())
})

onUnmounted(() => {
  if (sectionObserver) sectionObserver.disconnect()
})

watch(
  () => localeStore.locale,
  (lang) => {
    prefLanguage.value = lang
  },
)
</script>

<template>
  <div class="settings-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('settings.title') }}</h2>
        <span class="page-sub">{{ headerSummary }}</span>
      </div>
      <div class="header-actions">
        <span
          class="status-chip"
          :class="connected ? 'status-chip--live' : 'status-chip--warn'"
          role="status"
        >
          <span class="status-dot" />
          {{ connected ? $t('layout.connected') : $t('layout.disconnected') }}
        </span>
        <el-button :icon="Refresh" :loading="healthLoading" @click="fetchHealth">
          {{ $t('settings.refresh') }}
        </el-button>
      </div>
    </div>

    <div class="settings-layout">
      <aside class="settings-sidebar">
        <SettingsNav :items="NAV_ITEMS" :active-id="activeSection" @navigate="scrollToSection" />
      </aside>

      <div class="settings-content">
        <!-- Account -->
        <SettingsSection
          id="account"
          :title="$t('settings.user.title')"
          :description="$t('settings.user.accountDesc')"
        >
          <template #icon>
            <el-icon><User /></el-icon>
          </template>

          <div class="account-card">
            <div class="account-avatar" aria-hidden="true">
              {{ (auth.username || '?').charAt(0).toUpperCase() }}
            </div>
            <div class="account-info">
              <div class="account-name-row">
                <h4 class="account-name">{{ auth.username || '—' }}</h4>
                <span class="role-badge" :class="{ 'role-badge--admin': isAdmin }">
                  {{ isAdmin ? $t('settings.user.roleAdmin') : $t('settings.user.roleUser') }}
                </span>
              </div>
              <p class="account-meta">
                {{ $t('settings.user.loginTime') }}：
                {{ loginTime ? loginTime.toLocaleString() : '—' }}
              </p>
            </div>
            <div class="account-actions">
              <el-button :icon="Lock" @click="openChangePassword">
                {{ $t('settings.user.changePassword') }}
              </el-button>
              <el-button type="danger" plain @click="handleLogout">
                {{ $t('settings.user.logout') }}
              </el-button>
            </div>
          </div>
        </SettingsSection>

        <!-- Preferences -->
        <SettingsSection
          id="preferences"
          :title="$t('settings.preferences.title')"
          :description="$t('settings.preferences.panelDesc')"
        >
          <template #icon>
            <el-icon><Bell /></el-icon>
          </template>
          <SettingsPreferencesPanel
            :language="prefLanguage"
            :sound="prefSound"
            :events="prefEvents"
            @update:language="persistLanguage"
            @update:sound="persistSound"
            @update:events="persistEvents"
          />
        </SettingsSection>

        <!-- System -->
        <SettingsSection
          id="system"
          :title="$t('settings.healthStatus')"
          :description="$t('settings.systemDesc')"
        >
          <template #icon>
            <el-icon><Setting /></el-icon>
          </template>
          <SettingsHealthPanel
            :health="health"
            :loading="healthLoading"
            :error="healthError"
            :connected="connected"
            :version="backendVersion"
          />

          <div class="quick-links">
            <h4 class="quick-links-title">{{ $t('settings.quickLinks.title') }}</h4>
            <div class="quick-links-grid">
              <router-link
                v-for="link in QUICK_LINKS"
                :key="link.to"
                :to="link.to"
                class="quick-link"
              >
                <span class="quick-link-icon">
                  <el-icon><component :is="link.icon" /></el-icon>
                </span>
                <span class="quick-link-body">
                  <span class="quick-link-label">{{ link.label }}</span>
                  <span class="quick-link-desc">{{ link.desc }}</span>
                </span>
                <el-icon class="quick-link-arrow"><ArrowRight /></el-icon>
              </router-link>
            </div>
          </div>
        </SettingsSection>

        <!-- Data -->
        <SettingsSection
          id="data"
          :title="$t('settings.data.title')"
          :description="$t('settings.data.panelDesc')"
        >
          <template #icon>
            <el-icon><FolderOpened /></el-icon>
          </template>
          <SettingsDataPanel
            :exporting-devices="exporting.devices"
            :exporting-recordings="exporting.recordings"
            :backend-version="backendVersion"
            @export-devices="doExportDevices"
            @export-recordings="doExportRecordings"
            @clear-cache="clearCache"
          />
        </SettingsSection>
      </div>
    </div>

    <el-dialog
      v-model="changePasswordDialog"
      :title="$t('settings.user.changePasswordTitle')"
      width="440px"
      destroy-on-close
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
.settings-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.settings-layout {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: var(--space-6);
  align-items: start;
}

.settings-sidebar {
  position: sticky;
  top: var(--space-4);
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
}

.status-chip--live {
  border-color: color-mix(in srgb, var(--color-online) 35%, transparent);
  background: color-mix(in srgb, var(--color-online) 10%, transparent);
  color: var(--color-online);
}

.status-chip--warn {
  border-color: color-mix(in srgb, var(--color-warning) 35%, transparent);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  color: var(--color-warning);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.account-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-raised);
}

.account-avatar {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 14%, transparent);
  flex-shrink: 0;
}

.account-info {
  flex: 1;
  min-width: 180px;
}

.account-name-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.account-name {
  margin: 0;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
}

.role-badge {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
}

.role-badge--admin {
  color: var(--color-primary);
  border-color: var(--color-primary-border);
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.account-meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.account-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.quick-links {
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border-subtle);
}

.quick-links-title {
  margin: 0 0 var(--space-3);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.quick-links-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.quick-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
  text-decoration: none;
  color: inherit;
  transition:
    border-color var(--duration-fast) var(--easing-standard),
    transform var(--duration-fast) var(--easing-snap);
}

.quick-link:hover {
  border-color: var(--color-primary-border);
  transform: translateX(2px);
}

.quick-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.quick-link-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  color: var(--color-primary);
  flex-shrink: 0;
}

.quick-link-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quick-link-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.quick-link-desc {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.35;
}

.quick-link-arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

@media (max-width: 1024px) {
  .settings-layout {
    grid-template-columns: 1fr;
  }

  .settings-sidebar {
    position: static;
  }

  .settings-sidebar :deep(.settings-nav) {
    flex-direction: row;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .settings-sidebar :deep(.nav-item) {
    flex-shrink: 0;
  }

  .quick-links-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .account-card {
    flex-direction: column;
    align-items: stretch;
  }

  .account-actions {
    flex-direction: column;
  }

  .account-actions .el-button {
    width: 100%;
  }
}
</style>

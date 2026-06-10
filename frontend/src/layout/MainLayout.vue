<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'

const { t } = useI18n()
const localeStore = useLocaleStore()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const notifications = useNotificationsStore()

const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
const { connected, reconnecting, isStale, staleSeconds, onEvent } = useConnectionStatus({
  wsUrl,
})

// Forward every WS message into the notifications store. We use the explicit
// onEvent subscription (rather than the legacy onMessage option) so multiple
// consumers can share the same singleton connection.
let _unsubEvents = null
onMounted(() => {
  _unsubEvents = onEvent(notifications.handle)
})
onUnmounted(() => {
  if (_unsubEvents) _unsubEvents()
})

// Show a brief success toast when WS comes back from a stale state.
let _wasStale = false
watch([connected, isStale], ([isConnected, stale]) => {
  if (isConnected && _wasStale) {
    ElMessage({
      message: t('layout.wsReconnected'),
      type: 'success',
      duration: 1500,
    })
  }
  if (stale) _wasStale = true
})

const staleMessage = computed(() => {
  if (!isStale.value) return ''
  const base = t('layout.wsDisconnected')
  return `${base}，${t('layout.wsStale', { seconds: staleSeconds.value })}`
})

const showBreadcrumb = computed(() => route.path !== '/dashboard')
const currentPageTitle = computed(() => {
  const key = route.meta.titleKey
  return typeof key === 'string' ? t(key) : ''
})

function switchLang(lang) {
  localeStore.setLocale(lang)
}

function logout() {
  auth.logout()
  router.push('/login')
}

/* ── Responsive state ───────────────────── */
const { matches: isTabletOrBelow } = useMediaQuery('(max-width: 1023.98px)')
const { matches: isMobile } = useMediaQuery('(max-width: 767.98px)')

const drawerOpen = ref(false)

function toggleDrawer() {
  drawerOpen.value = !drawerOpen.value
}

function closeDrawer() {
  drawerOpen.value = false
}

// Auto-close drawer when route changes (mobile UX nicety)
watch(
  () => router.currentRoute.value.fullPath,
  () => {
    if (isTabletOrBelow.value) closeDrawer()
  },
)

// If viewport resizes to desktop, ensure drawer is closed (clean state)
watch(isTabletOrBelow, (v) => {
  if (!v) closeDrawer()
})
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-left">
        <button
          v-if="isTabletOrBelow"
          class="hamburger-btn"
          aria-label="Toggle menu"
          @click="toggleDrawer"
        >
          <el-icon :size="20">
            <component :is="drawerOpen ? 'Close' : 'Menu'" />
          </el-icon>
        </button>
        <div class="header-brand">
          <div class="brand-icon-wrap">
            <el-icon :size="16" class="brand-icon"><House /></el-icon>
          </div>
          <span class="brand-name">{{ $t('layout.brandName') }}</span>
        </div>
      </div>
      <div class="header-right">
        <div class="ws-status">
          <span
            class="ws-dot"
            :class="connected ? 'connected' : reconnecting ? 'reconnecting' : 'disconnected'"
          />
          <span v-if="!isMobile" class="ws-label">{{
            connected
              ? $t('layout.connected')
              : reconnecting
                ? $t('layout.reconnecting')
                : $t('layout.disconnected')
          }}</span>
        </div>
        <button
          class="lang-switch"
          @click="switchLang(localeStore.locale === 'zh-CN' ? 'en' : 'zh-CN')"
        >
          {{ $t('layout.switchLang') }}
        </button>
        <el-dropdown
          @command="
            (cmd) => {
              if (cmd === 'logout') logout()
              else if (cmd === 'settings') router.push('/settings')
            }
          "
        >
          <div
            class="user-trigger"
            :class="{ 'user-trigger--icon-only': isMobile }"
            :title="auth.username"
          >
            <el-icon :size="14"><User /></el-icon>
            <span v-if="!isMobile">{{ auth.username }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="settings">{{ $t('layout.settings') }}</el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                {{ $t('layout.logout') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="app-body">
      <!-- Desktop: persistent sidebar -->
      <nav v-if="!isTabletOrBelow" class="app-sidebar">
        <div class="nav-section">
          <div class="nav-section-label">{{ $t('layout.overview') }}</div>
          <RouterLink
            to="/dashboard"
            class="nav-item"
            :class="{ active: $route.path === '/dashboard' }"
          >
            <el-icon :size="16"><DataAnalysis /></el-icon>
            <span>{{ $t('layout.dashboard') }}</span>
          </RouterLink>
          <RouterLink
            to="/analytics"
            class="nav-item"
            :class="{ active: $route.path === '/analytics' }"
          >
            <el-icon :size="16"><TrendCharts /></el-icon>
            <span>{{ $t('layout.analytics') }}</span>
          </RouterLink>
        </div>

        <div class="nav-section">
          <div class="nav-section-label">{{ $t('layout.devices') }}</div>
          <RouterLink
            to="/devices"
            class="nav-item"
            :class="{ active: $route.path === '/devices' }"
          >
            <el-icon :size="16"><Monitor /></el-icon>
            <span>{{ $t('layout.devices') }}</span>
          </RouterLink>
          <RouterLink
            to="/cameras"
            class="nav-item"
            :class="{ active: $route.path === '/cameras' }"
          >
            <el-icon :size="16"><VideoCameraFilled /></el-icon>
            <span>{{ $t('layout.cameras') }}</span>
          </RouterLink>
          <RouterLink
            to="/topology"
            class="nav-item"
            :class="{ active: $route.path === '/topology' }"
          >
            <el-icon :size="16"><Share /></el-icon>
            <span>{{ $t('layout.topology') }}</span>
          </RouterLink>
        </div>

        <div class="nav-section">
          <div class="nav-section-label">{{ $t('layout.media') }}</div>
          <RouterLink
            to="/recordings"
            class="nav-item"
            :class="{ active: $route.path === '/recordings' }"
          >
            <el-icon :size="16"><Film /></el-icon>
            <span>{{ $t('layout.recordings') }}</span>
          </RouterLink>
          <RouterLink to="/dlna" class="nav-item" :class="{ active: $route.path === '/dlna' }">
            <el-icon :size="16"><Promotion /></el-icon>
            <span>{{ $t('layout.dlna') }}</span>
          </RouterLink>
        </div>

        <div class="nav-section">
          <div class="nav-section-label">{{ $t('layout.system') }}</div>
          <RouterLink
            to="/members"
            class="nav-item"
            :class="{ active: $route.path === '/members' }"
          >
            <el-icon :size="16"><UserFilled /></el-icon>
            <span>{{ $t('layout.members') }}</span>
          </RouterLink>
          <RouterLink
            to="/schedule"
            class="nav-item"
            :class="{ active: $route.path === '/schedule' }"
          >
            <el-icon :size="16"><Clock /></el-icon>
            <span>{{ $t('layout.schedule') }}</span>
          </RouterLink>
          <RouterLink
            to="/settings"
            class="nav-item"
            :class="{ active: $route.path === '/settings' }"
          >
            <el-icon :size="16"><Setting /></el-icon>
            <span>{{ $t('layout.settings') }}</span>
          </RouterLink>
        </div>
      </nav>

      <!-- Mobile/Tablet: drawer + overlay -->
      <Teleport v-if="isTabletOrBelow" to="body">
        <Transition name="overlay">
          <div v-if="drawerOpen" class="drawer-overlay" @click="closeDrawer" aria-hidden="true" />
        </Transition>
        <Transition name="drawer">
          <nav v-if="drawerOpen" class="app-sidebar app-sidebar--drawer">
            <div class="nav-section">
              <div class="nav-section-label">{{ $t('layout.overview') }}</div>
              <RouterLink
                to="/dashboard"
                class="nav-item"
                :class="{ active: $route.path === '/dashboard' }"
              >
                <el-icon :size="16"><DataAnalysis /></el-icon>
                <span>{{ $t('layout.dashboard') }}</span>
              </RouterLink>
              <RouterLink
                to="/analytics"
                class="nav-item"
                :class="{ active: $route.path === '/analytics' }"
              >
                <el-icon :size="16"><TrendCharts /></el-icon>
                <span>{{ $t('layout.analytics') }}</span>
              </RouterLink>
            </div>

            <div class="nav-section">
              <div class="nav-section-label">{{ $t('layout.devices') }}</div>
              <RouterLink
                to="/devices"
                class="nav-item"
                :class="{ active: $route.path === '/devices' }"
              >
                <el-icon :size="16"><Monitor /></el-icon>
                <span>{{ $t('layout.devices') }}</span>
              </RouterLink>
              <RouterLink
                to="/cameras"
                class="nav-item"
                :class="{ active: $route.path === '/cameras' }"
              >
                <el-icon :size="16"><VideoCameraFilled /></el-icon>
                <span>{{ $t('layout.cameras') }}</span>
              </RouterLink>
              <RouterLink
                to="/topology"
                class="nav-item"
                :class="{ active: $route.path === '/topology' }"
              >
                <el-icon :size="16"><Share /></el-icon>
                <span>{{ $t('layout.topology') }}</span>
              </RouterLink>
            </div>

            <div class="nav-section">
              <div class="nav-section-label">{{ $t('layout.media') }}</div>
              <RouterLink
                to="/recordings"
                class="nav-item"
                :class="{ active: $route.path === '/recordings' }"
              >
                <el-icon :size="16"><Film /></el-icon>
                <span>{{ $t('layout.recordings') }}</span>
              </RouterLink>
              <RouterLink to="/dlna" class="nav-item" :class="{ active: $route.path === '/dlna' }">
                <el-icon :size="16"><Promotion /></el-icon>
                <span>{{ $t('layout.dlna') }}</span>
              </RouterLink>
            </div>

            <div class="nav-section">
              <div class="nav-section-label">{{ $t('layout.system') }}</div>
              <RouterLink
                to="/members"
                class="nav-item"
                :class="{ active: $route.path === '/members' }"
              >
                <el-icon :size="16"><UserFilled /></el-icon>
                <span>{{ $t('layout.members') }}</span>
              </RouterLink>
              <RouterLink
                to="/schedule"
                class="nav-item"
                :class="{ active: $route.path === '/schedule' }"
              >
                <el-icon :size="16"><Clock /></el-icon>
                <span>{{ $t('layout.schedule') }}</span>
              </RouterLink>
              <RouterLink
                to="/settings"
                class="nav-item"
                :class="{ active: $route.path === '/settings' }"
              >
                <el-icon :size="16"><Setting /></el-icon>
                <span>{{ $t('layout.settings') }}</span>
              </RouterLink>
            </div>
          </nav>
        </Transition>
      </Teleport>

      <main
        class="app-content"
        :class="{
          'app-content--mobile': isMobile,
          'app-content--tablet': isTabletOrBelow && !isMobile,
        }"
      >
        <Transition name="stale-banner">
          <div v-if="isStale" class="stale-banner" role="status" aria-live="polite">
            <el-icon :size="16" class="stale-banner-icon"><WarningFilled /></el-icon>
            <span class="stale-banner-text">{{ staleMessage }}</span>
          </div>
        </Transition>
        <div v-if="showBreadcrumb" class="content-header">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item to="/dashboard">{{ $t('layout.dashboard') }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentPageTitle">{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <router-view v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg);
}

/* ── Header ────────────────────────────── */
.app-header {
  height: var(--header-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-icon-wrap {
  width: 30px;
  height: 30px;
  background: var(--color-primary-subtle);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.brand-icon {
  color: var(--color-primary);
}
.brand-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.hamburger-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    background var(--duration-fast) ease-out,
    color var(--duration-fast) ease-out,
    border-color var(--duration-fast) ease-out;
}
.hamburger-btn:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
  border-color: var(--color-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

@media (max-width: 767.98px) {
  .app-header {
    padding: 0 12px;
  }

  .header-right {
    gap: 10px;
  }

  .brand-name {
    font-size: 14px;
  }
}

.ws-status {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ws-dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.ws-dot.connected {
  background: var(--color-online);
}
.ws-dot.disconnected {
  background: var(--color-offline);
}
.ws-dot.reconnecting {
  background: var(--color-scanning);
  animation: ws-reconnect-pulse 1s ease-in-out infinite;
}
.ws-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.lang-switch {
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: 12px;
  padding: 3px 10px;
  cursor: pointer;
  transition:
    background var(--duration-fast) ease-out,
    color var(--duration-fast) ease-out,
    border-color var(--duration-fast) ease-out;
}
.lang-switch:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
  border-color: var(--color-primary);
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition:
    background var(--duration-fast) ease-out,
    color var(--duration-fast) ease-out;
}
.user-trigger:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}
.user-trigger--icon-only {
  padding: 6px;
}

/* ── Body ──────────────────────────────── */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* ── Sidebar (desktop) ─────────────────── */
.app-sidebar {
  width: var(--sidebar-width);
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  flex-shrink: 0;
  padding: var(--space-2) 0;
  overflow-y: auto;
}

.nav-section {
  padding: var(--space-1) 0;
}

.nav-section + .nav-section {
  border-top: 1px solid var(--color-border-subtle);
  margin-top: var(--space-2);
  padding-top: var(--space-4);
}

.nav-section:first-child {
  border-top: none;
}

.nav-section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  padding: var(--space-2) var(--space-4);
  margin-bottom: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 36px;
  padding: 0 var(--space-4);
  font-size: 13px;
  color: var(--color-text-secondary);
  text-decoration: none;
  position: relative;
  transition:
    background var(--duration-fast) var(--easing-standard),
    color var(--duration-fast) var(--easing-standard);
}
.nav-item:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}
.nav-item.active {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--color-primary);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
}
.nav-item .el-icon {
  flex-shrink: 0;
  font-size: 16px;
}

/* ── Sidebar (drawer / mobile) ─────────── */
.app-sidebar--drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  height: 100vh;
  z-index: 1000;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);
  padding-top: var(--space-4);
}

.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  backdrop-filter: blur(2px);
}

/* Drawer transitions */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.25s var(--easing-standard, cubic-bezier(0.4, 0, 0.2, 1));
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(-100%);
}

.overlay-enter-active,
.overlay-leave-active {
  transition: opacity 0.2s ease-out;
}
.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}

/* ── Content ───────────────────────────── */
.app-content {
  flex: 1;
  overflow-y: auto;
  background: var(--color-bg);
  padding: var(--space-6);
  min-width: 0;
}

.app-content--tablet {
  padding: 20px;
}

.app-content--mobile {
  padding: 14px;
}

.content-header {
  margin-bottom: var(--space-6);
}

:deep(.el-breadcrumb) {
  font-size: 13px;
}

:deep(.el-breadcrumb__item) {
  color: var(--color-text-muted);
}

:deep(.el-breadcrumb__inner) {
  color: var(--color-text-secondary);
}

:deep(.el-breadcrumb__inner.is-link:hover) {
  color: var(--color-primary);
}

:deep(.el-breadcrumb__separator) {
  color: var(--color-text-muted);
}

/* ── Stale connection banner ───────────── */
.stale-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: var(--space-4);
  background: color-mix(in srgb, var(--color-warning) 14%, var(--color-surface));
  border: 1px solid color-mix(in srgb, var(--color-warning) 50%, transparent);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1.4;
}

.stale-banner-icon {
  color: var(--color-warning);
  flex-shrink: 0;
}

.stale-banner-text {
  flex: 1;
}

.stale-banner-enter-active,
.stale-banner-leave-active {
  transition:
    transform 0.25s var(--easing-standard, cubic-bezier(0.4, 0, 0.2, 1)),
    opacity 0.25s var(--easing-standard, cubic-bezier(0.4, 0, 0.2, 1));
}
.stale-banner-enter-from,
.stale-banner-leave-to {
  transform: translateY(-12px);
  opacity: 0;
}
</style>

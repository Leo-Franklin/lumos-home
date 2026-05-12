<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useWebSocket } from '@/composables/useWebSocket'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'

const { t } = useI18n()
const localeStore = useLocaleStore()

const router = useRouter()
const auth = useAuthStore()
const notifications = useNotificationsStore()

const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
const { connected, reconnecting } = useWebSocket(wsUrl, { onMessage: notifications.handle })

function switchLang(lang) {
  localeStore.setLocale(lang)
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-brand">
        <div class="brand-icon-wrap">
          <el-icon :size="16" class="brand-icon"><House /></el-icon>
        </div>
        <span class="brand-name">{{ $t('layout.brandName') }}</span>
      </div>
      <div class="header-right">
        <div class="ws-status">
          <span
            class="ws-dot"
            :class="connected ? 'connected' : reconnecting ? 'reconnecting' : 'disconnected'"
          />
          <span class="ws-label">{{ connected ? $t('layout.connected') : reconnecting ? $t('layout.reconnecting') : $t('layout.disconnected') }}</span>
        </div>
        <button class="lang-switch" @click="switchLang(localeStore.locale === 'zh-CN' ? 'en' : 'zh-CN')">
          {{ $t('layout.switchLang') }}
        </button>
        <el-dropdown @command="(cmd) => cmd === 'logout' && logout()">
          <div class="user-trigger">
            <el-icon :size="14"><User /></el-icon>
            <span>{{ auth.username }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">{{ $t('layout.logout') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="app-body">
      <nav class="app-sidebar">
        <div class="nav-section">
          <div class="nav-section-label">{{ $t('layout.overview') }}</div>
          <RouterLink to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }">
            <el-icon :size="16"><DataAnalysis /></el-icon>
            <span>{{ $t('layout.dashboard') }}</span>
          </RouterLink>
        </div>

        <div class="nav-section">
          <div class="nav-section-label">{{ $t('layout.devices') }}</div>
          <RouterLink to="/devices" class="nav-item" :class="{ active: $route.path === '/devices' }">
            <el-icon :size="16"><Monitor /></el-icon>
            <span>{{ $t('layout.devices') }}</span>
          </RouterLink>
          <RouterLink to="/cameras" class="nav-item" :class="{ active: $route.path === '/cameras' }">
            <el-icon :size="16"><VideoCameraFilled /></el-icon>
            <span>{{ $t('layout.cameras') }}</span>
          </RouterLink>
          <RouterLink to="/topology" class="nav-item" :class="{ active: $route.path === '/topology' }">
            <el-icon :size="16"><Share /></el-icon>
            <span>{{ $t('layout.topology') }}</span>
          </RouterLink>
        </div>

        <div class="nav-section">
          <div class="nav-section-label">{{ $t('layout.media') }}</div>
          <RouterLink to="/recordings" class="nav-item" :class="{ active: $route.path === '/recordings' }">
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
          <RouterLink to="/members" class="nav-item" :class="{ active: $route.path === '/members' }">
            <el-icon :size="16"><UserFilled /></el-icon>
            <span>{{ $t('layout.members') }}</span>
          </RouterLink>
          <RouterLink to="/schedule" class="nav-item" :class="{ active: $route.path === '/schedule' }">
            <el-icon :size="16"><Clock /></el-icon>
            <span>{{ $t('layout.schedule') }}</span>
          </RouterLink>
          <RouterLink to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
            <el-icon :size="16"><Setting /></el-icon>
            <span>{{ $t('layout.settings') }}</span>
          </RouterLink>
        </div>
      </nav>

      <main class="app-content">
        <div class="content-header">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item to="/dashboard">{{ $t('layout.dashboard') }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title">{{ $route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <router-view />
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

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-icon-wrap {
  width: 30px;
  height: 30px;
  background: rgba(94, 92, 230, 0.12);
  border: 1px solid rgba(94, 92, 230, 0.22);
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

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
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
.ws-dot.connected    { background: var(--color-online); }
.ws-dot.disconnected { background: var(--color-offline); }
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
  transition: background var(--duration-fast) ease-out,
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
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out;
}
.user-trigger:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

/* ── Body ──────────────────────────────── */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Sidebar ───────────────────────────── */
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
  transition: background var(--duration-fast) var(--easing-standard),
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

/* ── Content ───────────────────────────── */
.app-content {
  flex: 1;
  overflow-y: auto;
  background: var(--color-bg);
  padding: var(--space-6);
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
</style>
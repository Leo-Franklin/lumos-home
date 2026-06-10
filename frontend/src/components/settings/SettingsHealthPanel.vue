<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  CircleCheck,
  CircleClose,
  DataLine,
  FolderOpened,
  VideoPlay,
} from '@element-plus/icons-vue'
import { formatAppVersion } from '@/constants/appMeta'

const props = defineProps({
  health: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  connected: { type: Boolean, default: false },
  version: { type: String, default: '' },
})

const { t } = useI18n()

const CHECK_META = [
  { key: 'database', icon: DataLine },
  { key: 'ffmpeg', icon: VideoPlay },
  { key: 'nas_writable', icon: FolderOpened },
]

const statusTone = computed(() => {
  if (!props.health) return 'unknown'
  if (props.health.status === 'healthy') return 'healthy'
  return 'degraded'
})

function formatUptime(s) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return t('settings.uptimeFormat', { h, m })
}
</script>

<template>
  <div class="health-panel">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="health-alert"
    />

    <el-skeleton v-else-if="loading && !health" :rows="4" animated />

    <template v-else-if="health">
      <div class="status-hero" :class="`status-hero--${statusTone}`">
        <div class="status-hero-main">
          <span class="status-pulse" aria-hidden="true" />
          <div>
            <p class="status-hero-label">{{ $t('settings.overallStatus') }}</p>
            <p class="status-hero-value">
              {{
                health.status === 'healthy'
                  ? $t('settings.systemHealthy')
                  : $t('settings.systemUnhealthy')
              }}
            </p>
          </div>
        </div>
        <div class="status-hero-meta">
          <div class="meta-chip">
            <span class="meta-label">{{ $t('settings.uptime') }}</span>
            <span class="meta-value tabular-nums">{{ formatUptime(health.uptime_seconds) }}</span>
          </div>
          <div v-if="version" class="meta-chip">
            <span class="meta-label">{{ $t('settings.data.backendVersion') }}</span>
            <span class="meta-value mono">{{ formatAppVersion(version) }}</span>
          </div>
          <div class="meta-chip">
            <span class="meta-label">{{ $t('settings.realtimeLink') }}</span>
            <span class="meta-value" :class="connected ? 'text-online' : 'text-warn'">
              {{ connected ? $t('layout.connected') : $t('layout.disconnected') }}
            </span>
          </div>
        </div>
      </div>

      <div class="check-grid">
        <div
          v-for="item in CHECK_META"
          :key="item.key"
          class="check-card"
          :class="health.checks?.[item.key] ? 'check-card--ok' : 'check-card--fail'"
        >
          <div class="check-icon-wrap">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
          <div class="check-body">
            <span class="check-name">{{ $t(`settings.checks.${item.key}`) }}</span>
            <span class="check-state">
              <el-icon class="check-state-icon">
                <CircleCheck v-if="health.checks?.[item.key]" />
                <CircleClose v-else />
              </el-icon>
              {{ health.checks?.[item.key] ? $t('settings.checkOk') : $t('settings.checkFail') }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.health-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.health-alert {
  margin: 0;
}

.status-hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-raised);
}

.status-hero--healthy {
  border-color: color-mix(in srgb, var(--color-online) 30%, transparent);
  background: color-mix(in srgb, var(--color-online) 6%, var(--color-surface-raised));
}

.status-hero--degraded {
  border-color: color-mix(in srgb, var(--color-warning) 35%, transparent);
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-surface-raised));
}

.status-hero-main {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.status-pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-online);
  flex-shrink: 0;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-online) 20%, transparent);
}

.status-hero--degraded .status-pulse {
  background: var(--color-warning);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-warning) 20%, transparent);
}

.status-hero-label {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.status-hero-value {
  margin: 4px 0 0;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
}

.status-hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.meta-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  min-width: 120px;
}

.meta-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.meta-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.text-online {
  color: var(--color-online);
}

.text-warn {
  color: var(--color-warning);
}

.check-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.check-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
}

.check-card--ok {
  border-color: color-mix(in srgb, var(--color-online) 25%, transparent);
}

.check-card--fail {
  border-color: color-mix(in srgb, var(--color-error) 30%, transparent);
  background: color-mix(in srgb, var(--color-error) 5%, var(--color-surface));
}

.check-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.check-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.check-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.check-state {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.check-state-icon {
  font-size: 13px;
}

.check-card--ok .check-state {
  color: var(--color-online);
}

.check-card--fail .check-state {
  color: var(--color-error);
}

.mono {
  font-family: var(--font-mono);
  font-size: 12px;
}

@media (max-width: 720px) {
  .check-grid {
    grid-template-columns: 1fr;
  }
}
</style>

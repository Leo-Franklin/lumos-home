<script setup>
import { Cellphone, VideoCamera, Delete, Document } from '@element-plus/icons-vue'
import { APP_VERSION, formatAppVersion } from '@/constants/appMeta'

defineProps({
  exportingDevices: { type: Boolean, default: false },
  exportingRecordings: { type: Boolean, default: false },
  backendVersion: { type: String, default: '' },
})

const emit = defineEmits(['export-devices', 'export-recordings', 'clear-cache'])
</script>

<template>
  <div class="data-panel">
    <div class="action-grid">
      <button
        type="button"
        class="action-card"
        :disabled="exportingDevices"
        @click="emit('export-devices')"
      >
        <span class="action-icon action-icon--devices">
          <el-icon><Cellphone /></el-icon>
        </span>
        <span class="action-body">
          <span class="action-title">{{ $t('settings.data.exportDevices') }}</span>
          <span class="action-desc">{{ $t('settings.data.exportDevicesDesc') }}</span>
        </span>
        <el-icon v-if="exportingDevices" class="action-spinner is-loading"><Document /></el-icon>
      </button>

      <button
        type="button"
        class="action-card"
        :disabled="exportingRecordings"
        @click="emit('export-recordings')"
      >
        <span class="action-icon action-icon--recordings">
          <el-icon><VideoCamera /></el-icon>
        </span>
        <span class="action-body">
          <span class="action-title">{{ $t('settings.data.exportRecordings') }}</span>
          <span class="action-desc">{{ $t('settings.data.exportRecordingsDesc') }}</span>
        </span>
        <el-icon v-if="exportingRecordings" class="action-spinner is-loading"><Document /></el-icon>
      </button>
    </div>

    <div class="danger-zone">
      <div class="danger-head">
        <h4 class="danger-title">{{ $t('settings.data.dangerZone') }}</h4>
        <p class="danger-desc">{{ $t('settings.data.cacheDesc') }}</p>
      </div>
      <el-button type="danger" plain :icon="Delete" @click="emit('clear-cache')">
        {{ $t('settings.data.clearCache') }}
      </el-button>
    </div>

    <div class="version-strip">
      <div class="version-item">
        <span class="version-label">{{ $t('settings.data.frontendVersion') }}</span>
        <span class="version-value mono">{{ formatAppVersion(APP_VERSION) }}</span>
      </div>
      <div class="version-divider" />
      <div class="version-item">
        <span class="version-label">{{ $t('settings.data.backendVersion') }}</span>
        <span class="version-value mono">{{ formatAppVersion(backendVersion) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.data-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.action-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
  cursor: pointer;
  text-align: left;
  transition:
    border-color var(--duration-fast) var(--easing-standard),
    transform var(--duration-fast) var(--easing-snap),
    box-shadow var(--duration-fast) var(--easing-standard);
}

.action-card:hover:not(:disabled) {
  border-color: var(--color-primary-border);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-card:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.action-card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.action-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 18px;
}

.action-icon--devices {
  background: color-mix(in srgb, var(--color-accent-devices) 14%, transparent);
  color: var(--color-accent-devices);
}

.action-icon--recordings {
  background: color-mix(in srgb, var(--color-accent-recordings) 14%, transparent);
  color: var(--color-accent-recordings);
}

.action-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.action-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.action-desc {
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-text-muted);
}

.action-spinner {
  flex-shrink: 0;
  color: var(--color-primary);
}

.danger-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid color-mix(in srgb, var(--color-error) 25%, transparent);
  background: color-mix(in srgb, var(--color-error) 5%, var(--color-surface));
}

.danger-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-error);
}

.danger-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
  max-width: 420px;
}

.version-strip {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
}

.version-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.version-label {
  font-size: 11px;
  color: var(--color-text-muted);
}

.version-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.version-divider {
  width: 1px;
  height: 16px;
  background: var(--color-border-subtle);
}

.mono {
  font-family: var(--font-mono);
}

@media (max-width: 640px) {
  .action-grid {
    grid-template-columns: 1fr;
  }

  .danger-zone {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

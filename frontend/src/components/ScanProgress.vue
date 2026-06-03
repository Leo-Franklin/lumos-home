<script setup>
import { useNotificationsStore } from '@/stores/notifications'
import { computed } from 'vue'
import { useDevicesStore } from '@/stores/devices'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Loading, Close } from '@element-plus/icons-vue'

const { t } = useI18n()
const devicesStore = useDevicesStore()
const notifications = useNotificationsStore()

const lastScan = computed(() => {
  return notifications.messages.find((m) => m.event === 'scan_completed')
})

const progressPct = computed(() => Math.round(devicesStore.scanningProgress ?? 0))

function onCancel() {
  devicesStore.cancelScan()
  ElMessage.info(t('common.scanCancelled'))
}
</script>

<template>
  <div v-if="devicesStore.scanning" class="scan-progress">
    <div class="scan-progress-text">
      <el-icon class="is-loading scan-icon"><Loading /></el-icon>
      <span class="scan-stage">{{ t('common.scanStage', { subnet: devicesStore.scanningStage || '192.168.1.x' }) }}</span>
    </div>
    <el-progress
      :percentage="progressPct"
      :stroke-width="3"
      :show-text="false"
      :duration="200"
      color="var(--color-scanning)"
      class="scan-progress-bar"
    />
    <span class="scan-progress-pct">{{ t('common.scanProgress', { pct: progressPct }) }}</span>
    <el-button
      size="small"
      link
      :icon="Close"
      class="scan-cancel-btn"
      @click="onCancel"
    >
      {{ t('common.cancelScan') }}
    </el-button>
  </div>
  <div v-else-if="lastScan" class="scan-result">
    {{ t('common.scanResult', { found: lastScan.data.found, new: lastScan.data.new }) }}
  </div>
</template>

<style scoped>
.scan-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.scan-progress-text {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.scan-icon {
  color: var(--color-scanning);
  font-size: 14px;
}

.scan-stage {
  font-size: 13px;
  color: var(--color-scanning);
  font-variant-numeric: tabular-nums;
}

.scan-progress-bar {
  flex: 1;
  min-width: 80px;
  max-width: 160px;
}

.scan-progress-pct {
  font-size: 12px;
  color: var(--color-scanning);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
  flex-shrink: 0;
  min-width: 56px;
  text-align: right;
}

.scan-cancel-btn {
  font-size: 12px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.scan-cancel-btn:hover {
  color: var(--color-error);
}

.scan-result {
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>

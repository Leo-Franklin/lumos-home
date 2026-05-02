<script setup>
import { useNotificationsStore } from '@/stores/notifications'
import { computed } from 'vue'
import { useDevicesStore } from '@/stores/devices'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const devicesStore = useDevicesStore()
const notifications = useNotificationsStore()

const lastScan = computed(() => {
  return notifications.messages.find((m) => m.event === 'scan_completed')
})
</script>

<template>
  <div v-if="devicesStore.scanning" class="scan-progress">
    <el-icon class="is-loading scan-icon"><Loading /></el-icon>
    <span class="scan-text">{{ $t('common.scanning') }}</span>
  </div>
  <div v-else-if="lastScan" class="scan-result">
    {{ $t('common.scanResult', { found: lastScan.data.found, new: lastScan.data.new }) }}
  </div>
</template>

<style scoped>
.scan-progress {
  display: flex;
  align-items: center;
  gap: 6px;
}
.scan-icon {
  color: var(--color-scanning);
}
.scan-text {
  font-size: 13px;
  color: var(--color-scanning);
}

.scan-result {
  font-size: 12px;
  color: var(--color-text-muted);
}
.scan-count {
  color: var(--color-online);
  font-weight: 500;
}
</style>

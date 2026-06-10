<!-- src/components/analytics/NetworkOverviewPanel.vue -->
<script setup>
import { computed } from 'vue'
import DonutChart from '@/components/charts/DonutChart.vue'

const props = defineProps({
  typeData: { type: Array, default: () => [] },
  online: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  unknownToday: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
})

const onlineRate = computed(() => {
  if (!props.total) return 0
  return Math.round((props.online / props.total) * 100)
})

const offline = computed(() => Math.max(0, props.total - props.online))
</script>

<template>
  <div class="overview-panel">
    <el-skeleton v-if="loading" :rows="5" animated />
    <template v-else>
      <div class="overview-types">
        <DonutChart v-if="typeData.length" :data="typeData" :size="148" />
        <div v-else class="overview-empty">{{ $t('charts.empty') }}</div>
      </div>

      <div class="overview-status">
        <div class="status-head">
          <span class="status-title">{{ $t('analytics.onlineRate') }}</span>
          <span class="status-pct tabular-nums">{{ onlineRate }}%</span>
        </div>

        <div class="status-bar" role="presentation">
          <div
            class="status-bar-fill status-bar-fill--online"
            :style="{ width: `${onlineRate}%` }"
          />
        </div>

        <div class="status-counts">
          <div class="status-count">
            <span class="status-dot status-dot--online" />
            <span class="status-count-label">{{ $t('common.online') }}</span>
            <span class="status-count-value tabular-nums">{{ online }}</span>
          </div>
          <div class="status-count">
            <span class="status-dot status-dot--offline" />
            <span class="status-count-label">{{ $t('common.offline') }}</span>
            <span class="status-count-value tabular-nums">{{ offline }}</span>
          </div>
          <div class="status-count" :class="{ 'status-count--warn': unknownToday > 0 }">
            <span class="status-dot status-dot--warn" />
            <span class="status-count-label">{{ $t('analytics.unknownToday') }}</span>
            <span class="status-count-value tabular-nums">{{ unknownToday }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.overview-panel {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-6);
  align-items: center;
  min-height: 180px;
}

.overview-types {
  display: flex;
  align-items: center;
  justify-content: center;
}
.overview-empty {
  width: 148px;
  height: 148px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 13px;
}

.overview-status {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.status-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.status-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.status-pct {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1;
}

.status-bar {
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-surface-overlay);
  overflow: hidden;
}
.status-bar-fill {
  height: 100%;
  border-radius: inherit;
  transition: width var(--duration-base) var(--easing-standard);
}
.status-bar-fill--online {
  background: linear-gradient(
    90deg,
    var(--color-online),
    color-mix(in srgb, var(--color-online) 70%, var(--color-primary))
  );
}

.status-counts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}
.status-count {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
}
.status-count--warn {
  border-color: color-mix(in srgb, var(--color-warning) 35%, transparent);
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}
.status-dot--online {
  background: var(--color-online);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
}
.status-dot--offline {
  background: var(--color-offline);
}
.status-dot--warn {
  background: var(--color-warning);
}
.status-count-label {
  font-size: 11px;
  color: var(--color-text-muted);
}
.status-count-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.1;
}

@media (max-width: 767.98px) {
  .overview-panel {
    grid-template-columns: 1fr;
    justify-items: center;
  }
  .overview-status {
    width: 100%;
  }
  .status-counts {
    grid-template-columns: 1fr;
  }
}
</style>

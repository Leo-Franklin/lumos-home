<!-- src/components/analytics/DeviceHealthTable.vue -->
<script setup>
defineProps({
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
defineEmits(['row-click'])
</script>

<template>
  <div class="health-table">
    <div class="health-table-head">
      <span class="col-name">{{ $t('analytics.healthColDevice') }}</span>
      <span class="col-metric">{{ $t('analytics.healthColLatency') }}</span>
      <span class="col-metric">{{ $t('analytics.healthColUptime') }}</span>
      <span class="col-status">{{ $t('analytics.healthColStatus') }}</span>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />

    <div v-else-if="!rows.length" class="health-table-empty">
      {{ $t('analytics.healthAllGood') }}
    </div>

    <button
      v-for="row in rows"
      :key="row.mac"
      type="button"
      class="health-row"
      :class="`health-row--${row.status}`"
      @click="$emit('row-click', row)"
    >
      <span class="col-name">
        <span class="device-name">{{ row.label }}</span>
        <span class="device-mac">{{ row.mac }}</span>
      </span>
      <span class="col-metric tabular-nums">
        {{ row.latency != null ? `${Math.round(row.latency)}ms` : '—' }}
      </span>
      <span class="col-metric tabular-nums">
        {{ row.uptime != null ? `${row.uptime.toFixed(1)}%` : '—' }}
      </span>
      <span class="col-status">
        <span class="status-pill" :class="`status-pill--${row.status}`">
          {{ $t(`analytics.healthStatus.${row.status}`) }}
        </span>
      </span>
    </button>
  </div>
</template>

<style scoped>
.health-table {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-height: 200px;
}

.health-table-head,
.health-row {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) 88px 88px 92px;
  gap: var(--space-3);
  align-items: center;
  padding: 0 var(--space-3);
}

.health-table-head {
  height: 32px;
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--color-border-subtle);
}

.health-row {
  min-height: 48px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast) var(--easing-standard);
}
.health-row:hover {
  background: var(--color-surface-raised);
}
.health-row--critical {
  background: color-mix(in srgb, var(--color-error) 4%, transparent);
}
.health-row--warning {
  background: color-mix(in srgb, var(--color-warning) 4%, transparent);
}

.col-name {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.device-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.device-mac {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.col-metric {
  font-size: 12px;
  color: var(--color-text-secondary);
  text-align: right;
}
.col-status {
  display: flex;
  justify-content: flex-end;
}

.status-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  letter-spacing: 0.02em;
}
.status-pill--good {
  color: var(--color-online);
  background: color-mix(in srgb, var(--color-online) 14%, transparent);
}
.status-pill--warning {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 14%, transparent);
}
.status-pill--critical {
  color: var(--color-error);
  background: color-mix(in srgb, var(--color-error) 14%, transparent);
}

.health-table-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  color: var(--color-online);
  font-size: 13px;
}

@media (max-width: 767.98px) {
  .health-table-head {
    display: none;
  }
  .health-row {
    grid-template-columns: 1fr;
    gap: var(--space-2);
    padding: var(--space-3);
    border: 1px solid var(--color-border-subtle);
    margin-bottom: var(--space-2);
  }
  .col-metric,
  .col-status {
    justify-content: flex-start;
    text-align: left;
  }
}
</style>

<script setup>
defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  total: { type: [String, Number], default: null },
  suffix: { type: String, default: '' },
  description: { type: String, default: '' },
  trend: { type: String, default: null },  // e.g., "+2 vs last week"
  iconColor: { type: String, default: 'var(--color-primary)' },
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'members', 'cameras', 'devices', 'recordings', 'unknown'].includes(v)
  },
  warning: { type: Boolean, default: false },
})
</script>

<template>
  <div
    class="stat-card glass-card"
    :class="[`stat-card--${variant}`, { 'stat-card--warn': warning }]"
  >
    <div class="stat-icon-wrap">
      <div class="stat-icon" :style="{ color: iconColor }">
        <slot name="icon" />
      </div>
    </div>
    <div class="stat-body">
      <div class="stat-header">{{ title }}</div>
      <div class="stat-value-row">
        <span class="stat-value">{{ value }}</span>
        <span v-if="total !== null" class="stat-total">/ {{ total }}</span>
        <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
      </div>
      <div class="stat-desc-row">
        <span class="stat-desc">{{ description }}</span>
        <span v-if="trend" class="stat-trend">{{ trend }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-5);
  transition: transform var(--duration-base) var(--easing-snap),
              box-shadow var(--duration-base) var(--easing-standard);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.stat-card--warn {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.06);
}

.stat-icon-wrap {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.2);
}

.stat-icon {
  width: 22px;
  height: 22px;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--space-2);
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.stat-total {
  font-size: 18px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.stat-suffix {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-left: var(--space-1);
}

.stat-desc-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.stat-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.stat-trend {
  font-size: 11px;
  color: var(--color-success);
  font-weight: 500;
}

/* Variant colors for icon backgrounds */
.stat-card--members .stat-icon-wrap { background: var(--color-primary-subtle); }
.stat-card--cameras .stat-icon-wrap { background: var(--color-primary-subtle); }
.stat-card--devices .stat-icon-wrap { background: var(--color-primary-subtle); }
.stat-card--recordings .stat-icon-wrap { background: var(--color-primary-subtle); }
.stat-card--unknown .stat-icon-wrap { background: var(--color-primary-subtle); }
.stat-card--warn .stat-icon-wrap { background: rgba(245, 158, 11, 0.15); }

/* Animation */
.stat-card {
  animation: fade-up var(--duration-base) var(--easing-snap) both;
}
</style>
<!-- src/components/charts/BaseChart.vue -->
<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  title: String,
  subtitle: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  empty: { type: Boolean, default: false },
  range: { type: String, default: null },
  // [{ label: t('charts.ranges.last7d'), value: '7d' }, ...]  — renders range selector in header when provided
  ranges: { type: Array, default: null },
  featured: { type: Boolean, default: false },
})
const emit = defineEmits(['range-change'])
</script>

<template>
  <div class="chart-card" :class="{ 'chart-card--featured': featured }">
    <div class="chart-header">
      <div class="chart-header-text">
        <span class="chart-title">{{ title }}</span>
        <span v-if="subtitle" class="chart-subtitle">{{ subtitle }}</span>
      </div>
      <el-radio-group
        v-if="ranges"
        :model-value="range"
        size="small"
        class="chart-range"
        @change="emit('range-change', $event)"
      >
        <el-radio-button v-for="r in ranges" :key="r.value" :value="r.value">
          {{ r.label }}
        </el-radio-button>
      </el-radio-group>
    </div>
    <div class="chart-body">
      <el-skeleton v-if="loading" :rows="3" animated />
      <div v-else-if="empty" class="chart-empty">{{ t('charts.empty') }}</div>
      <slot v-else />
    </div>
    <div v-if="$slots.footer && !loading && !empty" class="chart-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.chart-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  transition:
    border-color var(--duration-base) var(--easing-standard),
    background var(--duration-base) var(--easing-standard);
}
.chart-card--featured {
  border-color: var(--color-primary-border);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--color-primary) 5%, var(--color-surface)) 0%,
    var(--color-surface) 48%
  );
}
.chart-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  min-height: 28px;
}
.chart-header-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.chart-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
  line-height: 1.3;
}
.chart-subtitle {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.4;
}
.chart-range {
  flex-shrink: 0;
}
.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 160px;
  color: var(--color-text-muted);
  font-size: 13px;
}
.chart-footer {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
}
</style>

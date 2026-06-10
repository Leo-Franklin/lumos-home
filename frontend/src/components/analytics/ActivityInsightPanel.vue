<!-- src/components/analytics/ActivityInsightPanel.vue -->
<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
    // [{ key, label, value, hint, accent?, warn? }]
  },
  loading: { type: Boolean, default: false },
})
</script>

<template>
  <div class="insight-panel">
    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else>
      <div
        v-for="item in items"
        :key="item.key"
        class="insight-item"
        :class="{ 'insight-item--warn': item.warn }"
      >
        <div class="insight-top">
          <span class="insight-label">{{ item.label }}</span>
          <span v-if="item.accent" class="insight-accent" :style="{ background: item.accent }" />
        </div>
        <div class="insight-value tabular-nums">{{ item.value }}</div>
        <div v-if="item.hint" class="insight-hint">{{ item.hint }}</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.insight-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  height: 100%;
  align-content: start;
}

.insight-item {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
  min-height: 78px;
}
.insight-item--warn {
  border-color: color-mix(in srgb, var(--color-warning) 35%, transparent);
  background: color-mix(in srgb, var(--color-warning) 5%, var(--color-surface-raised));
}

.insight-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}
.insight-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.03em;
}
.insight-accent {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.insight-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
  margin-bottom: 2px;
}
.insight-hint {
  font-size: 11px;
  color: var(--color-text-secondary);
  line-height: 1.35;
}

@media (max-width: 767.98px) {
  .insight-panel {
    grid-template-columns: 1fr;
  }
}
</style>

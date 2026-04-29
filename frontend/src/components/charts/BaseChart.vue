<!-- src/components/charts/BaseChart.vue -->
<script setup>
defineProps({
  title:   String,
  loading: { type: Boolean, default: false },
  empty:   { type: Boolean, default: false },
  range:   { type: String, default: null },
  // [{ label: '近7天', value: '7d' }, ...]  — renders range selector in header when provided
  ranges:  { type: Array, default: null },
})
const emit = defineEmits(['range-change'])
</script>

<template>
  <div class="chart-card">
    <div class="chart-header">
      <span class="chart-title">{{ title }}</span>
      <el-radio-group
        v-if="ranges"
        :model-value="range"
        size="small"
        @change="emit('range-change', $event)"
      >
        <el-radio-button v-for="r in ranges" :key="r.value" :value="r.value">
          {{ r.label }}
        </el-radio-button>
      </el-radio-group>
    </div>
    <div class="chart-body">
      <el-skeleton v-if="loading" :rows="3" animated />
      <div v-else-if="empty" class="chart-empty">暂无数据</div>
      <slot v-else />
    </div>
  </div>
</template>

<style scoped>
.chart-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
}
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  min-height: 28px;
}
.chart-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 160px;
  color: var(--color-text-muted);
  font-size: 13px;
}
</style>

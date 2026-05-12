<script setup>
defineProps({
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
  color: { type: String, default: null },  // hex or CSS var
  count: { type: Number, default: null },
})

defineEmits(['click'])
</script>

<template>
  <button
    class="filter-chip"
    :class="{ active }"
    :style="active && color ? {
      '--chip-color': color,
      '--chip-bg': color + '18',
      '--chip-border': color + '50'
    } : {}"
    @click="$emit('click')"
  >
    <span
      v-if="color"
      class="chip-dot"
      :style="{ background: active ? 'var(--chip-color)' : color }"
    />
    <span class="chip-label">{{ label }}</span>
    <span v-if="count !== null" class="chip-count">{{ count }}</span>
  </button>
</template>

<style scoped>
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--duration-fast) var(--easing-standard);
  white-space: nowrap;
}

.filter-chip:hover:not(.active) {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.filter-chip.active {
  background: var(--chip-bg, var(--color-primary-subtle));
  border-color: var(--chip-border, var(--color-primary-border));
  color: var(--chip-color, var(--color-primary));
  font-weight: 500;
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chip-label {
  line-height: 1;
}

.chip-count {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  opacity: 0.7;
}
</style>
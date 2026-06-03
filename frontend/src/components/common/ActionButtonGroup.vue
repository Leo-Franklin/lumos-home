<script setup>
defineProps({
  actions: {
    type: Array,
    required: true,
    // shape: [{ icon, tooltip, ariaLabel, type, danger, disabled, placement, onClick }]
    // type ∈ undefined | 'primary' | 'record' | 'recording' (mirrors prior CSS modifiers)
  },
  size: { type: String, default: 'small' },
  tooltipShowAfter: { type: Number, default: 400 },
})
</script>

<template>
  <div class="action-group">
    <el-tooltip
      v-for="(action, idx) in actions"
      :key="idx"
      :content="action.tooltip || ''"
      :placement="action.placement || 'top'"
      :show-after="tooltipShowAfter"
    >
      <el-button
        class="action-btn"
        :class="{
          'action-btn--danger': action.danger,
          'action-btn--primary': action.type === 'primary',
          'action-btn--record': action.type === 'record',
          'action-btn--recording': action.type === 'recording',
        }"
        :size="size"
        :icon="action.icon"
        :aria-label="action.ariaLabel || action.tooltip || ''"
        :disabled="action.disabled"
        @click="action.onClick && action.onClick()"
      />
    </el-tooltip>
  </div>
</template>

<style scoped>
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-raised);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--color-text-primary);
  --el-button-active-bg-color: var(--color-surface-overlay);
  --el-button-active-border-color: transparent;
  height: 28px;
  width: 28px;
  padding: 3px;
  border-radius: 5px;
  font-size: 15px;
  transition:
    background var(--duration-fast) ease-out,
    color var(--duration-fast) ease-out;
}

.action-btn--danger {
  --el-button-hover-bg-color: rgba(239, 68, 68, 0.1);
  --el-button-hover-text-color: var(--color-error);
  --el-button-active-bg-color: rgba(239, 68, 68, 0.15);
}
</style>

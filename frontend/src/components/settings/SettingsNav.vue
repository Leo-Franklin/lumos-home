<script setup>
defineProps({
  items: { type: Array, required: true },
  activeId: { type: String, default: '' },
})

const emit = defineEmits(['navigate'])

function onClick(id) {
  emit('navigate', id)
}
</script>

<template>
  <nav class="settings-nav" aria-label="Settings sections">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="nav-item"
      :class="{ 'nav-item--active': activeId === item.id }"
      :aria-current="activeId === item.id ? 'true' : undefined"
      @click="onClick(item.id)"
    >
      <span class="nav-icon" aria-hidden="true">
        <component :is="item.icon" />
      </span>
      <span class="nav-label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.settings-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-2);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px 12px;
  border: none;
  border-radius: var(--radius-lg);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition:
    background var(--duration-fast) var(--easing-standard),
    color var(--duration-fast) var(--easing-standard);
}

.nav-item:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.nav-item--active {
  background: color-mix(in srgb, var(--color-primary) 14%, transparent);
  color: var(--color-primary);
}

.nav-item:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.nav-icon {
  display: flex;
  font-size: 16px;
  opacity: 0.9;
}

.nav-label {
  line-height: 1.2;
}
</style>

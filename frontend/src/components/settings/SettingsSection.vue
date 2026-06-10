<script setup>
defineProps({
  id: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <section :id="id" class="settings-section glass-card">
    <header class="section-head">
      <div v-if="$slots.icon" class="section-icon-wrap">
        <slot name="icon" />
      </div>
      <div class="section-head-text">
        <h3 class="section-title">{{ title }}</h3>
        <p v-if="description" class="section-desc">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="section-head-actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="section-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.settings-section {
  overflow: hidden;
}

.section-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-5) var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}

.section-icon-wrap {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
  font-size: 18px;
}

.section-head-text {
  flex: 1;
  min-width: 0;
}

.section-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
}

.section-desc {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-text-muted);
}

.section-head-actions {
  flex-shrink: 0;
}

.section-body {
  padding: var(--space-5);
}
</style>

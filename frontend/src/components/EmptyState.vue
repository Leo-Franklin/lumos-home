<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: String, default: 'device' },  // 'device' | 'camera' | 'recording' | 'search'
  actionLabel: { type: String, default: null },
})

defineEmits(['action'])
</script>

<template>
  <div class="empty-state">
    <div class="empty-illustration">
      <!-- Device illustration -->
      <svg v-if="icon === 'device'" viewBox="0 0 120 80" fill="none">
        <rect x="30" y="20" width="60" height="40" rx="6" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <rect x="50" y="55" width="20" height="5" rx="2" fill="var(--color-surface-raised)"/>
        <circle cx="60" cy="40" r="10" fill="var(--color-text-muted)" opacity="0.2"/>
        <circle cx="60" cy="40" r="4" fill="var(--color-text-muted)" opacity="0.4"/>
        <circle cx="85" cy="25" r="12" fill="var(--color-surface-raised)" stroke="var(--color-warning)" stroke-width="1.5" stroke-dasharray="3 2"/>
        <path d="M85 19v12M79 25h12" stroke="var(--color-warning)" stroke-width="1.5" stroke-linecap="round"/>
      </svg>

      <!-- Camera illustration -->
      <svg v-else-if="icon === 'camera'" viewBox="0 0 120 80" fill="none">
        <rect x="25" y="25" width="70" height="40" rx="6" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <path d="M60 25v-6a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v6" stroke="var(--color-border)" stroke-width="1.5"/>
        <circle cx="60" cy="45" r="12" fill="var(--color-text-muted)" opacity="0.15"/>
        <circle cx="60" cy="45" r="6" fill="var(--color-text-muted)" opacity="0.3"/>
      </svg>

      <!-- Recording illustration -->
      <svg v-else-if="icon === 'recording'" viewBox="0 0 120 80" fill="none">
        <circle cx="60" cy="40" r="25" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <polygon points="52,32 52,48 68,40" fill="var(--color-text-muted)" opacity="0.4"/>
      </svg>

      <!-- Search illustration -->
      <svg v-else viewBox="0 0 120 80" fill="none">
        <circle cx="50" cy="35" r="18" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <path d="M63 48l20 20" stroke="var(--color-border)" stroke-width="3" stroke-linecap="round"/>
        <path d="M44 35h12M50 29v12" stroke="var(--color-text-muted)" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
      </svg>
    </div>

    <h3 class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>

    <el-button
      v-if="actionLabel"
      type="primary"
      class="empty-action"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </el-button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
}

.empty-illustration {
  width: 120px;
  height: 80px;
  margin-bottom: var(--space-6);
  opacity: 0.8;
}

.empty-illustration svg {
  width: 100%;
  height: 100%;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.empty-description {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-6);
  max-width: 300px;
  line-height: 1.6;
}

.empty-action {
  margin-top: var(--space-2);
}
</style>
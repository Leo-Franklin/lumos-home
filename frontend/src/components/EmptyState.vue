<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: String, default: 'device' },  // 'device' | 'camera' | 'recording' | 'search' | 'dlna' | 'schedule' | 'member' | 'topology'
  actionLabel: { type: String, default: null },
  size: {
    type: String,
    default: 'medium',
    validator: (v) => ['small', 'medium', 'large'].includes(v),
  },
  compact: { type: Boolean, default: false },
})

defineEmits(['action'])

const sizeClass = computed(() => `is-${props.size}`)
const showIllustration = computed(() => !props.compact)
</script>

<template>
  <div class="empty-state" :class="[sizeClass, { 'is-compact': compact }]">
    <div v-if="showIllustration" class="empty-illustration" aria-hidden="true">
      <slot name="illustration">
        <!-- Device illustration -->
        <svg v-if="icon === 'device'" viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <rect x="30" y="20" width="60" height="40" rx="6" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <rect x="50" y="55" width="20" height="5" rx="2" fill="var(--color-surface-raised)"/>
          <circle cx="60" cy="40" r="10" fill="var(--color-text-muted)" opacity="0.2"/>
          <circle cx="60" cy="40" r="4" fill="var(--color-text-muted)" opacity="0.4"/>
          <circle cx="85" cy="25" r="12" fill="var(--color-surface-raised)" stroke="var(--color-warning)" stroke-width="1.5" stroke-dasharray="3 2"/>
          <path d="M85 19v12M79 25h12" stroke="var(--color-warning)" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Camera illustration -->
        <svg v-else-if="icon === 'camera'" viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <rect x="25" y="25" width="70" height="40" rx="6" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <path d="M60 25v-6a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v6" stroke="var(--color-border)" stroke-width="1.5"/>
          <circle cx="60" cy="45" r="12" fill="var(--color-text-muted)" opacity="0.15"/>
          <circle cx="60" cy="45" r="6" fill="var(--color-text-muted)" opacity="0.3"/>
        </svg>

        <!-- Recording illustration -->
        <svg v-else-if="icon === 'recording'" viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <circle cx="60" cy="40" r="25" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <polygon points="52,32 52,48 68,40" fill="var(--color-text-muted)" opacity="0.4"/>
        </svg>

        <!-- DLNA illustration -->
        <svg v-else-if="icon === 'dlna'" viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <rect x="35" y="20" width="50" height="35" rx="4" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <circle cx="48" cy="32" r="2" fill="var(--color-text-muted)"/>
          <circle cx="56" cy="32" r="2" fill="var(--color-text-muted)"/>
          <path d="M44 42h32M44 48h20" stroke="var(--color-text-muted)" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
          <path d="M85 35l8-8M85 40l10 0" stroke="var(--color-primary)" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
          <circle cx="93" cy="27" r="3" fill="var(--color-primary)" opacity="0.4"/>
        </svg>

        <!-- Schedule illustration -->
        <svg v-else-if="icon === 'schedule'" viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <rect x="25" y="22" width="70" height="42" rx="6" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <path d="M25 34h70" stroke="var(--color-border)" stroke-width="1.5"/>
          <circle cx="38" cy="28" r="2" fill="var(--color-text-muted)"/>
          <circle cx="48" cy="28" r="2" fill="var(--color-text-muted)"/>
          <path d="M40 50h20M40 56h14" stroke="var(--color-text-muted)" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Member illustration -->
        <svg v-else-if="icon === 'member'" viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <circle cx="60" cy="32" r="11" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <path d="M40 60c0-11 9-18 20-18s20 7 20 18" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        </svg>

        <!-- Topology illustration -->
        <svg v-else-if="icon === 'topology'" viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <circle cx="60" cy="40" r="6" fill="var(--color-primary)" opacity="0.3"/>
          <circle cx="60" cy="40" r="11" fill="none" stroke="var(--color-primary)" stroke-width="1" opacity="0.4"/>
          <circle cx="30" cy="25" r="4" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <circle cx="90" cy="25" r="4" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <circle cx="30" cy="58" r="4" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <circle cx="90" cy="58" r="4" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <line x1="60" y1="40" x2="30" y2="25" stroke="var(--color-border)" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
          <line x1="60" y1="40" x2="90" y2="25" stroke="var(--color-border)" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
          <line x1="60" y1="40" x2="30" y2="58" stroke="var(--color-border)" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
          <line x1="60" y1="40" x2="90" y2="58" stroke="var(--color-border)" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
        </svg>

        <!-- Search illustration (default) -->
        <svg v-else viewBox="0 0 120 80" fill="none" aria-hidden="true">
          <circle cx="50" cy="35" r="18" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
          <path d="M63 48l20 20" stroke="var(--color-border)" stroke-width="3" stroke-linecap="round"/>
          <path d="M44 35h12M50 29v12" stroke="var(--color-text-muted)" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
        </svg>
      </slot>
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
  padding: var(--space-10) var(--space-6);
  text-align: center;
}

/* ── Sizes ───────────────────────────────── */
.is-small {
  padding: var(--space-4) var(--space-3);
}
.is-small .empty-title {
  font-size: 13px;
  margin: 0 0 var(--space-1);
}
.is-small .empty-description {
  font-size: 12px;
  margin: 0 0 var(--space-2);
  max-width: 220px;
  line-height: 1.5;
}
.is-small :deep(.empty-illustration) {
  width: 64px;
  height: 44px;
  margin-bottom: var(--space-3);
}

.is-medium {
  padding: var(--space-10) var(--space-6);
}
.is-medium .empty-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 var(--space-2);
}
.is-medium .empty-description {
  font-size: 13px;
  margin: 0 0 var(--space-6);
  max-width: 300px;
  line-height: 1.6;
}

.is-large {
  padding: 48px var(--space-6);
}
.is-large .empty-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 var(--space-3);
}
.is-large .empty-description {
  font-size: 14px;
  margin: 0 0 var(--space-8);
  max-width: 360px;
  line-height: 1.6;
}

/* ── Compact (no illustration) ──────────── */
.is-compact.is-small { padding: var(--space-4) var(--space-3); }
.is-compact.is-medium { padding: var(--space-8) var(--space-4); }
.is-compact.is-large { padding: var(--space-10) var(--space-4); }

/* ── Illustration ────────────────────────── */
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

/* ── Text ────────────────────────────────── */
.empty-title {
  color: var(--color-text-primary);
}

.empty-description {
  color: var(--color-text-secondary);
}

.empty-action {
  margin-top: var(--space-2);
}
</style>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  members: { type: Array, default: () => [] },
})

const homeCount = computed(() => props.members.filter((m) => m.is_home).length)
const total = computed(() => props.members.length)

const latestEvent = computed(() => {
  let best = null
  for (const m of props.members) {
    const ts = m.is_home ? m.last_arrived_at : m.last_left_at
    if (!ts) continue
    const time = new Date(ts).getTime()
    if (!best || time > best.time) {
      best = { name: m.name, isHome: m.is_home, time, ts }
    }
  }
  return best
})
</script>

<template>
  <div v-if="total > 0" class="overview-bar">
    <span class="overview-stat">
      <span class="overview-value">{{ homeCount }}/{{ total }}</span>
      <span class="overview-label">{{ $t('members.overviewHome') }}</span>
    </span>
    <span v-if="latestEvent" class="overview-divider" aria-hidden="true" />
    <span v-if="latestEvent" class="overview-recent">
      {{
        latestEvent.isHome
          ? $t('members.overviewRecentArrived', {
              name: latestEvent.name,
              time: $d(latestEvent.ts, 'short'),
            })
          : $t('members.overviewRecentLeft', {
              name: latestEvent.name,
              time: $d(latestEvent.ts, 'short'),
            })
      }}
    </span>
  </div>
</template>

<style scoped>
.overview-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  margin-bottom: 12px;
  flex-shrink: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  font-size: 13px;
}

.overview-stat {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.overview-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}

.overview-label {
  color: var(--color-text-muted);
}

.overview-divider {
  width: 1px;
  height: 16px;
  background: var(--color-border-subtle);
}

.overview-recent {
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

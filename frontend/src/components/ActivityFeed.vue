<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  items: { type: Array, default: () => [] },
  maxHeight: { type: Number, default: 420 },
  showViewAll: { type: Boolean, default: false },
  /** Batching window for incoming items (ms). */
  batchIntervalMs: { type: Number, default: 500 },
})

const emit = defineEmits(['viewAll'])

const EVENT_COLORS = {
  device: 'var(--color-cat-device)',
  camera: 'var(--color-cat-camera)',
  member: 'var(--color-cat-member)',
  system: 'var(--color-cat-system)',
}

function getDotColor(category) {
  return EVENT_COLORS[category] || EVENT_COLORS.system
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return t('dashboard.timeJustNow')
  if (diffMins < 60) return t('dashboard.timeMinutesAgo', { m: diffMins })
  if (diffMins < 1440) return t('dashboard.timeHoursAgo', { h: Math.floor(diffMins / 60) })
  return t('dashboard.timeDaysAgo', { d: Math.floor(diffMins / 1440) })
}

// Batch-merge behaviour: incoming `items` are throttled to one update per
// `batchIntervalMs` ms. Within a 1s window, if N>=3 items arrived, we collapse
// them into a single "+N new events" row at the top instead of N rows.
const RENDER_BULK_THRESHOLD = 3

const renderedItems = ref(props.items.slice())
let _flushTimer = null

function _flush() {
  // Strip the __pending marker from any leftover rows.
  renderedItems.value = renderedItems.value.map((it) => {
    if (it && it.__pending) {
      // eslint-disable-next-line no-unused-vars
      const { __pending, ...rest } = it
      return rest
    }
    return it
  })
}

function _scheduleFlush() {
  if (_flushTimer) return
  _flushTimer = setTimeout(() => {
    _flushTimer = null
    _flush()
  }, props.batchIntervalMs)
}

watch(
  () => props.items,
  (newItems, oldItems) => {
    if (!Array.isArray(newItems)) return
    const oldLen = Array.isArray(oldItems) ? oldItems.length : 0
    const diff = newItems.length - oldLen
    if (diff <= 0) {
      // Parent reset or truncation: just sync the rendered list.
      renderedItems.value = newItems.slice()
      return
    }

    if (diff >= RENDER_BULK_THRESHOLD) {
      // Collapse the burst into a single bulk row at the top.
      const burstRow = {
        __bulk: true,
        count: diff,
        timestamp: newItems[0]?.timestamp || new Date().toISOString(),
      }
      const tail = newItems.slice(diff)
      renderedItems.value = [burstRow, ...tail]
    } else {
      // Small delta — just sync (avoid extra render passes).
      renderedItems.value = newItems.slice()
    }
    _scheduleFlush()
  },
  { deep: true, immediate: false },
)

onUnmounted(() => {
  if (_flushTimer) {
    clearTimeout(_flushTimer)
    _flushTimer = null
  }
})

defineExpose({
  flush: _flush,
})
</script>

<template>
  <div class="activity-panel glass-card">
    <div class="activity-header">
      <div class="activity-header-left">
        <span class="activity-title">{{ $t('dashboard.recentActivity') }}</span>
        <span v-if="renderedItems.length > 0" class="activity-count">{{
          renderedItems.length
        }}</span>
      </div>
      <el-button v-if="showViewAll" link size="small" class="view-all-btn" @click="emit('viewAll')">
        {{ $t('common.viewAll') }}
      </el-button>
    </div>

    <div class="activity-list" :style="{ maxHeight: maxHeight + 'px' }">
      <div v-if="renderedItems.length === 0" class="activity-empty">
        <div class="activity-empty-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 8v4l3 2" />
            <circle cx="12" cy="12" r="9" />
          </svg>
        </div>
        <span class="activity-empty-text">{{ $t('dashboard.noRecentActivity') }}</span>
      </div>
      <template v-else>
        <div
          v-for="(item, index) in renderedItems"
          :key="item.__bulk ? 'bulk-' + item.count + '-' + item.timestamp : 'row-' + index"
          class="activity-item"
          :class="{ 'activity-item--bulk': item.__bulk }"
          :style="{ animationDelay: Math.min(index * 30, 200) + 'ms' }"
        >
          <span
            v-if="!item.__bulk"
            class="activity-dot"
            :style="{ background: getDotColor(item.category) }"
          />
          <span v-else class="activity-dot activity-dot--bulk" />
          <span class="activity-label">
            <template v-if="item.__bulk">
              {{ t('dashboard.bulkEvents', { count: item.count }) }}
            </template>
            <template v-else>
              {{ item.label }}
            </template>
          </span>
          <span v-if="item.timestamp" class="activity-time">
            {{ formatTime(item.timestamp) }}
          </span>
        </div>
      </template>
    </div>

    <div v-if="renderedItems.length > 0" class="activity-fade" />
  </div>
</template>

<style scoped>
.activity-panel {
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
}

.activity-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.activity-header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.activity-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-full);
  padding: 1px 7px;
  font-variant-numeric: tabular-nums;
}

.activity-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.view-all-btn {
  font-size: 12px;
  color: var(--color-primary);
}

.activity-list {
  overflow-y: auto;
  flex: 1;
  position: relative;
  padding-right: var(--space-2);
}

.activity-list::-webkit-scrollbar {
  width: 4px;
}

.activity-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-full);
}

.activity-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  font-size: 13px;
  color: var(--color-text-primary);
  animation: fade-up var(--duration-base) var(--easing-snap) both;
}

.activity-item + .activity-item {
  border-top: 1px solid var(--color-border-subtle);
}

.activity-item--bulk {
  font-weight: 600;
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  border-radius: var(--radius-sm);
  padding-left: var(--space-3);
  padding-right: var(--space-3);
  margin: 2px 0;
}

.activity-item--bulk + .activity-item {
  border-top: none;
}

.activity-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.activity-dot--bulk {
  background: var(--color-primary);
  opacity: 0.6;
}

.activity-label {
  flex: 1;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-time {
  font-size: 11px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.activity-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-text-muted);
  font-size: 13px;
  padding: var(--space-10) var(--space-4);
}

.activity-empty-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
  color: var(--color-text-muted);
  opacity: 0.7;
}

.activity-empty-icon svg {
  width: 20px;
  height: 20px;
}

.activity-empty-text {
  text-align: center;
  line-height: 1.5;
}

.activity-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: var(--space-2);
  height: 40px;
  background: linear-gradient(to top, var(--color-surface), transparent);
  pointer-events: none;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
</style>

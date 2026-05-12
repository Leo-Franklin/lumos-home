<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  items: { type: Array, default: () => [] },
  maxHeight: { type: Number, default: 420 },
  showViewAll: { type: Boolean, default: false },
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

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="activity-panel glass-card">
    <div class="activity-header">
      <span class="activity-title">{{ $t('dashboard.recentActivity') }}</span>
      <el-button
        v-if="showViewAll"
        link
        size="small"
        class="view-all-btn"
        @click="emit('viewAll')"
      >
        {{ $t('common.viewAll') }}
      </el-button>
    </div>

    <div class="activity-list" :style="{ maxHeight: maxHeight + 'px' }">
      <div v-if="items.length === 0" class="activity-empty">
        <span>{{ $t('dashboard.noRecentActivity') }}</span>
      </div>
      <div
        v-else
        v-for="(item, index) in items"
        :key="index"
        class="activity-item"
        :style="{ animationDelay: Math.min(index * 30, 200) + 'ms' }"
      >
        <span
          class="activity-dot"
          :style="{ background: getDotColor(item.category) }"
        />
        <span class="activity-label">{{ item.label }}</span>
        <span v-if="item.timestamp" class="activity-time">
          {{ formatTime(item.timestamp) }}
        </span>
      </div>
    </div>

    <div v-if="items.length > 0" class="activity-fade" />
  </div>
</template>

<style scoped>
.activity-panel {
  padding: var(--space-5);
  max-height: v-bind('maxHeight + 60 + "px"');
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

.activity-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
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
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: var(--space-8) 0;
}

.activity-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: var(--space-2);
  height: 40px;
  background: linear-gradient(to top, rgba(24, 24, 28, 0.9), transparent);
  pointer-events: none;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
</style>
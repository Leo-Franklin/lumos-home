<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  member: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  deviceCount: { type: Number, default: 0 },
})

defineEmits(['select'])

const { d } = useI18n()

const statusTime = computed(() => {
  const ts = props.member.is_home ? props.member.last_arrived_at : props.member.last_left_at
  if (!ts) return null
  return d(ts, 'short')
})

const needsSetup = computed(() => props.deviceCount === 0)
</script>

<template>
  <button
    type="button"
    class="member-card"
    :class="{
      'member-card--selected': selected,
      'member-card--home': member.is_home,
      'member-card--warn': needsSetup,
    }"
    :aria-pressed="selected"
    @click="$emit('select', member)"
  >
    <div class="card-top">
      <div class="avatar-wrap">
        <el-avatar v-if="member.avatar_url" :src="member.avatar_url" :size="36" />
        <el-avatar v-else :size="36">{{ member.name.charAt(0) }}</el-avatar>
        <span
          class="status-dot"
          :class="member.is_home ? 'status-dot--home' : 'status-dot--away'"
          role="status"
          :aria-label="member.is_home ? $t('members.home') : $t('members.away')"
        />
      </div>
      <div class="card-info">
        <div class="card-name">{{ member.name }}</div>
        <div class="card-status">
          <span :class="member.is_home ? 'tag-home' : 'tag-away'">
            {{ member.is_home ? $t('members.home') : $t('members.away') }}
          </span>
          <span v-if="statusTime" class="card-time">{{ statusTime }}</span>
        </div>
      </div>
    </div>

    <div class="card-meta">
      <span class="meta-item">
        {{
          deviceCount > 0
            ? $t('members.boundDeviceCount', { n: deviceCount })
            : $t('members.noBoundDevices')
        }}
      </span>
      <span v-if="needsSetup" class="meta-warn">{{ $t('members.setupNeeded') }}</span>
    </div>
  </button>
</template>

<style scoped>
.member-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding: 14px;
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) ease-out,
    background var(--duration-fast) ease-out,
    box-shadow var(--duration-fast) ease-out;
}

.member-card:hover {
  background: var(--color-surface-raised);
  border-color: var(--color-border);
}

.member-card--selected {
  border-color: var(--color-primary-border);
  background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface));
  box-shadow: 0 0 0 1px var(--color-primary-subtle);
}

.member-card--warn:not(.member-card--selected) {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--color-border-subtle));
}

.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-wrap {
  position: relative;
  flex-shrink: 0;
}

.status-dot {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--color-surface);
}

.status-dot--home {
  background: var(--color-online);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.45);
}

.status-dot--away {
  background: var(--color-offline);
}

.card-info {
  min-width: 0;
  flex: 1;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
}

.tag-home,
.tag-away {
  font-size: 11px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.tag-home {
  color: var(--color-online);
  background: color-mix(in srgb, var(--color-online) 12%, transparent);
}

.tag-away {
  color: var(--color-text-muted);
  background: var(--color-surface-raised);
}

.card-time {
  font-size: 11px;
  color: var(--color-text-muted);
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 11px;
  color: var(--color-text-muted);
}

.meta-warn {
  font-size: 11px;
  color: var(--color-warning);
}
</style>

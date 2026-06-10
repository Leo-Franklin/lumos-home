<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Connection,
  User,
  Moon,
  Camera as CameraIcon,
  Film,
  Failed,
  Refresh,
} from '@element-plus/icons-vue'

const props = defineProps({
  language: { type: String, required: true },
  sound: { type: Boolean, required: true },
  events: { type: Object, required: true },
})

const emit = defineEmits(['update:language', 'update:sound', 'update:events'])

const { t } = useI18n()

const EVENT_ICONS = {
  unknown_device_detected: Connection,
  camera_online: CameraIcon,
  camera_offline: CameraIcon,
  recording_completed: Film,
  recording_failed: Failed,
  member_arrived: User,
  member_left: User,
  scan_completed: Refresh,
}

const EVENT_GROUPS = computed(() => [
  {
    id: 'security',
    label: t('settings.groups.security'),
    desc: t('settings.groups.securityDesc'),
    events: ['unknown_device_detected'],
  },
  {
    id: 'camera',
    label: t('settings.groups.camera'),
    desc: t('settings.groups.cameraDesc'),
    events: ['camera_online', 'camera_offline', 'recording_completed', 'recording_failed'],
  },
  {
    id: 'member',
    label: t('settings.groups.member'),
    desc: t('settings.groups.memberDesc'),
    events: ['member_arrived', 'member_left'],
  },
  {
    id: 'system',
    label: t('settings.groups.system'),
    desc: t('settings.groups.systemDesc'),
    events: ['scan_completed'],
  },
])

const LANGUAGE_OPTIONS = [
  { value: 'zh-CN', labelKey: 'login.langChinese', native: '简体中文' },
  { value: 'en', labelKey: 'login.langEnglish', native: 'English' },
]

function setLanguage(value) {
  emit('update:language', value)
}

function setSound(value) {
  emit('update:sound', value)
}

function toggleEvent(key, value) {
  emit('update:events', { ...props.events, [key]: value })
}

function groupEnabled(events) {
  return events.every((key) => props.events[key])
}

function groupIndeterminate(events) {
  const enabled = events.filter((key) => props.events[key]).length
  return enabled > 0 && enabled < events.length
}

function toggleGroup(events, enabled) {
  const next = { ...props.events }
  events.forEach((key) => {
    next[key] = enabled
  })
  emit('update:events', next)
}
</script>

<template>
  <div class="prefs-panel">
    <div class="pref-block">
      <div class="pref-block-head">
        <h4 class="pref-block-title">{{ $t('settings.preferences.language') }}</h4>
        <p class="pref-block-desc">{{ $t('settings.preferences.languageDesc') }}</p>
      </div>
      <div class="lang-grid">
        <button
          v-for="opt in LANGUAGE_OPTIONS"
          :key="opt.value"
          type="button"
          class="lang-card"
          :class="{ 'lang-card--active': language === opt.value }"
          @click="setLanguage(opt.value)"
        >
          <span class="lang-native">{{ opt.native }}</span>
          <span class="lang-label">{{ $t(opt.labelKey) }}</span>
        </button>
      </div>
    </div>

    <div class="pref-block">
      <div class="pref-row-head">
        <div>
          <h4 class="pref-block-title">{{ $t('settings.preferences.notifications') }}</h4>
          <p class="pref-block-desc">{{ $t('settings.preferences.notificationsDesc') }}</p>
        </div>
        <div class="sound-toggle">
          <span class="sound-label">{{ $t('settings.preferences.notifySound') }}</span>
          <el-switch :model-value="sound" @change="setSound" />
        </div>
      </div>

      <div class="notify-groups">
        <div v-for="group in EVENT_GROUPS" :key="group.id" class="notify-group">
          <div class="notify-group-head">
            <el-checkbox
              :model-value="groupEnabled(group.events)"
              :indeterminate="groupIndeterminate(group.events)"
              @change="(v) => toggleGroup(group.events, v)"
            >
              <span class="notify-group-title">{{ group.label }}</span>
            </el-checkbox>
            <p class="notify-group-desc">{{ group.desc }}</p>
          </div>
          <div class="notify-tiles">
            <label
              v-for="key in group.events"
              :key="key"
              class="notify-tile"
              :class="{ 'notify-tile--on': events[key] }"
            >
              <input
                type="checkbox"
                class="notify-tile-input"
                :checked="events[key]"
                @change="toggleEvent(key, $event.target.checked)"
              />
              <el-icon class="notify-tile-icon"><component :is="EVENT_ICONS[key]" /></el-icon>
              <span class="notify-tile-label">{{ $t(`settings.notificationEvents.${key}`) }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <p class="theme-note">
      <el-icon><Moon /></el-icon>
      {{ $t('settings.preferences.themeNote') }}
    </p>
  </div>
</template>

<style scoped>
.prefs-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.pref-block-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.pref-block-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.lang-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.lang-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--easing-standard),
    background var(--duration-fast) var(--easing-standard);
}

.lang-card:hover {
  border-color: var(--color-primary-border);
  background: var(--color-surface-raised);
}

.lang-card--active {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
  box-shadow: 0 0 0 1px var(--color-primary-border);
}

.lang-card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.lang-native {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.lang-label {
  font-size: 11px;
  color: var(--color-text-muted);
}

.pref-row-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.sound-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 8px 12px;
  border-radius: var(--radius-lg);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
}

.sound-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.notify-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  margin-top: var(--space-5);
}

.notify-group {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
}

.notify-group-head {
  margin-bottom: var(--space-3);
}

.notify-group-title {
  font-size: 13px;
  font-weight: 600;
}

.notify-group-desc {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--color-text-muted);
}

.notify-tiles {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.notify-tile {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-raised);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--easing-standard),
    background var(--duration-fast) var(--easing-standard);
}

.notify-tile:hover {
  border-color: var(--color-primary-border);
}

.notify-tile--on {
  border-color: color-mix(in srgb, var(--color-primary) 40%, transparent);
  background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface-raised));
}

.notify-tile-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.notify-tile-icon {
  font-size: 14px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.notify-tile-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.3;
}

.theme-note {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--color-text-muted);
  background: var(--color-surface-raised);
  border: 1px dashed var(--color-border-subtle);
}

@media (max-width: 640px) {
  .lang-grid,
  .notify-tiles {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup>
import {
  VideoCameraFilled, Monitor, Iphone, Cpu, QuestionFilled,
  Connection, Grid, Film, Printer, Microphone, Trophy, Box, Watch,
} from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  device: { type: Object, required: true },
})
defineEmits(['edit', 'delete', 'detail'])

const TYPE_CONFIG = {
  camera:        { label: 'Camera',        color: 'var(--color-type-camera)',        hex: 'var(--color-type-camera)' },
  computer:      { label: 'Computer',      color: 'var(--color-type-computer)',      hex: 'var(--color-type-computer)' },
  phone:         { label: 'Phone',         color: 'var(--color-type-phone)',         hex: 'var(--color-type-phone)' },
  iot:           { label: 'IoT',           color: 'var(--color-type-iot)',           hex: 'var(--color-type-iot)' },
  router:        { label: 'Router',        color: 'var(--color-type-router)',        hex: 'var(--color-type-router)' },
  tablet:        { label: 'Tablet',        color: 'var(--color-type-tablet)',        hex: 'var(--color-type-tablet)' },
  tv:            { label: 'TV',            color: 'var(--color-type-tv)',            hex: 'var(--color-type-tv)' },
  printer:       { label: 'Printer',       color: 'var(--color-type-printer)',       hex: 'var(--color-type-printer)' },
  smart_speaker: { label: 'Smart Speaker', color: 'var(--color-type-smart-speaker)', hex: 'var(--color-type-smart-speaker)' },
  game_console:  { label: 'Game Console',  color: 'var(--color-type-game-console)',  hex: 'var(--color-type-game-console)' },
  nas:           { label: 'NAS',           color: 'var(--color-type-nas)',           hex: 'var(--color-type-nas)' },
  wearable:      { label: 'Wearable',      color: 'var(--color-type-wearable)',      hex: 'var(--color-type-wearable)' },
  unknown:       { label: 'Unknown',       color: 'var(--color-type-unknown)',       hex: 'var(--color-type-unknown)' },
}

function typeIcon(t) {
  const icons = {
    camera: VideoCameraFilled,
    computer: Monitor,
    phone: Iphone,
    iot: Cpu,
    router: Connection,
    tablet: Grid,
    tv: Film,
    printer: Printer,
    smart_speaker: Microphone,
    game_console: Trophy,
    nas: Box,
    wearable: Watch,
  }
  return icons[t] || QuestionFilled
}

function typeIconStyle(t) {
  const cfg = TYPE_CONFIG[t] || TYPE_CONFIG.unknown
  return { color: cfg.hex, background: `color-mix(in srgb, ${cfg.hex} 10%, transparent)` }
}

function typeBadgeStyle(t) {
  const cfg = TYPE_CONFIG[t] || TYPE_CONFIG.unknown
  return { color: cfg.hex, background: `color-mix(in srgb, ${cfg.hex} 10%, transparent)` }
}

function formatLastSeen(timestamp) {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return t('common.justNow')
  if (diffMins < 60) return t('common.minutesAgo', { n: diffMins })
  if (diffMins < 1440) return t('common.hoursAgo', { n: Math.floor(diffMins / 60) })
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="device-card glass-card" :class="{ 'device-card--offline': !device.is_online }">
    <div class="card-header">
      <span class="status-indicator" :class="device.is_online ? 'online' : 'offline'" />
      <div class="type-badge" :style="typeIconStyle(device.device_type)">
        <el-icon :size="14">
          <component :is="typeIcon(device.device_type)" />
        </el-icon>
      </div>
    </div>

    <div class="card-body">
      <h3 class="device-name">{{ device.alias || device.hostname || $t('devices.unnamed') }}</h3>
      <p class="device-vendor" v-if="device.vendor">{{ device.vendor }}</p>

      <div class="device-meta">
        <div class="meta-item">
          <span class="meta-label">{{ $t('devices.ipAddress') }}</span>
          <span class="meta-value mono">{{ device.ip || '—' }}</span>
        </div>
        <div class="meta-item" v-if="device.last_seen">
          <span class="meta-label">{{ $t('devices.lastSeen') }}</span>
          <span class="meta-value">{{ formatLastSeen(device.last_seen) }}</span>
        </div>
      </div>
    </div>

    <div class="card-footer">
      <span class="type-badge-pill" :style="typeBadgeStyle(device.device_type)">
        {{ $t(`common.deviceTypes.${device.device_type}`) }}
      </span>
    </div>

    <div class="card-actions">
      <el-button size="small" @click="$emit('detail', device)">{{ $t('common.detail') }}</el-button>
      <el-button size="small" @click="$emit('edit', device)">{{ $t('common.edit') }}</el-button>
      <el-button size="small" type="danger" @click="$emit('delete', device)">{{ $t('common.delete') }}</el-button>
    </div>
  </div>
</template>

<style scoped>
.device-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  gap: var(--space-4);
  transition: transform var(--duration-base) var(--easing-snap),
              box-shadow var(--duration-base) var(--easing-standard);
}

.device-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.device-card--offline {
  opacity: 0.7;
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-indicator.online {
  background: var(--color-online);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
  animation: pulse-glow 2s ease-in-out infinite;
}

.status-indicator.offline {
  background: var(--color-offline);
}

.type-badge {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-body {
  flex: 1;
}

.device-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-vendor {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-3);
  font-family: var(--font-mono);
}

.device-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.meta-label {
  font-size: 11px;
  color: var(--color-text-muted);
  min-width: 50px;
}

.meta-value {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.meta-value.mono {
  font-family: var(--font-mono);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.type-badge-pill {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  letter-spacing: 0.01em;
}

.card-actions {
  display: flex;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
}

.card-actions .el-button {
  flex: 1;
  font-size: 12px;
}
</style>
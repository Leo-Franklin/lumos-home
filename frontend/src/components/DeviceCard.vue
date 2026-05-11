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

function typeConfig(t) {
  return TYPE_CONFIG[t] || { label: t || 'Unknown', color: 'var(--color-type-unknown)', hex: 'var(--color-type-unknown)' }
}

function typeBadgeStyle(t) {
  const cfg = typeConfig(t)
  return { color: cfg.hex, background: `color-mix(in srgb, ${cfg.hex} 10%, transparent)` }
}

function typeIconStyle(t) {
  const cfg = typeConfig(t)
  return { color: cfg.hex, background: `color-mix(in srgb, ${cfg.hex} 10%, transparent)` }
}
</script>

<template>
  <div class="device-row">
    <span class="status-dot" :class="device.is_online ? 'online' : 'offline'" />

    <div class="type-icon" :style="typeIconStyle(device.device_type)">
      <el-icon :size="14">
        <VideoCameraFilled v-if="device.device_type === 'camera'" />
        <Monitor          v-else-if="device.device_type === 'computer'" />
        <Iphone           v-else-if="device.device_type === 'phone'" />
        <Cpu              v-else-if="device.device_type === 'iot'" />
        <Connection       v-else-if="device.device_type === 'router'" />
        <Grid             v-else-if="device.device_type === 'tablet'" />
        <Film             v-else-if="device.device_type === 'tv'" />
        <Printer          v-else-if="device.device_type === 'printer'" />
        <Microphone       v-else-if="device.device_type === 'smart_speaker'" />
        <Trophy           v-else-if="device.device_type === 'game_console'" />
        <Box              v-else-if="device.device_type === 'nas'" />
        <Watch            v-else-if="device.device_type === 'wearable'" />
        <QuestionFilled   v-else />
      </el-icon>
    </div>

    <div class="device-main">
      <span class="device-name">{{ device.alias || device.hostname || $t('devices.unnamed') }}</span>
      <span class="device-meta" v-if="device.vendor">{{ device.vendor }}</span>
    </div>

    <span class="device-ip-list">{{ device.ip || '—' }}</span>

    <span class="type-badge" :style="typeBadgeStyle(device.device_type)">
      {{ $t(`common.deviceTypes.${device.device_type}`) }}
    </span>

    <div class="device-actions">
      <button class="btn-ghost" @click="$emit('detail', device)">{{ $t('common.detail') }}</button>
      <button class="btn-ghost" @click="$emit('edit', device)">{{ $t('common.edit') }}</button>
      <button class="btn-ghost btn-danger" @click="$emit('delete', device)">{{ $t('common.delete') }}</button>
    </div>
  </div>
</template>

<style scoped>
.device-row {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 52px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  font-family: var(--font-sans);
  transition: background var(--duration-fast) ease-out;
}
.device-row:hover {
  background: var(--color-surface-raised);
}
.device-row:last-child {
  border-bottom: none;
}

/* Status dot */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.status-dot.online {
  background: var(--color-online);
  box-shadow: 0 0 6px rgba(38, 194, 129, 0.5);
  animation: breathe 2s ease-in-out infinite;
}
.status-dot.offline {
  background: var(--color-offline);
}

@keyframes breathe {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(38, 194, 129, 0.5); }
  50% { opacity: 0.4; box-shadow: 0 0 12px rgba(38, 194, 129, 0.8); }
}

/* Type icon */
.type-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Main info */
.device-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.device-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.01em;
}
.device-meta {
  font-size: 12px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* IP in list */
.device-ip-list {
  font-size: 11px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  white-space: nowrap;
  flex-shrink: 0;
}

/* Type badge */
.type-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex-shrink: 0;
  letter-spacing: 0.01em;
}

/* Action buttons */
.device-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--duration-fast) ease-out;
}
.device-row:hover .device-actions {
  opacity: 1;
}

.btn-ghost {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-family: var(--font-sans);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  line-height: 1.5;
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out,
              border-color var(--duration-fast) ease-out;
}
.btn-ghost:hover {
  background: var(--color-surface-overlay);
  color: var(--color-text-primary);
  border-color: var(--color-border);
}
.btn-ghost.btn-danger:hover {
  background: rgba(240, 82, 82, 0.1);
  color: var(--color-error);
  border-color: rgba(240, 82, 82, 0.25);
}
</style>

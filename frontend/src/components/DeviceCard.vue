<script setup>
import {
  VideoCameraFilled, Monitor, Iphone, Cpu, QuestionFilled,
  Connection, Grid, Film, Printer, Microphone, Trophy, Box, Watch,
} from '@element-plus/icons-vue'

defineProps({
  device: { type: Object, required: true },
})
defineEmits(['edit', 'delete', 'detail'])

const TYPE_CONFIG = {
  camera:        { label: 'Camera',        hex: 'var(--color-type-camera)' },
  computer:      { label: 'Computer',      hex: 'var(--color-type-computer)' },
  phone:         { label: 'Phone',         hex: 'var(--color-type-phone)' },
  iot:           { label: 'IoT',           hex: 'var(--color-type-iot)' },
  router:        { label: 'Router',        hex: 'var(--color-type-router)' },
  tablet:        { label: 'Tablet',        hex: 'var(--color-type-tablet)' },
  tv:            { label: 'TV',            hex: 'var(--color-type-tv)' },
  printer:       { label: 'Printer',       hex: 'var(--color-type-printer)' },
  smart_speaker: { label: 'Smart Speaker', hex: 'var(--color-type-smart-speaker)' },
  game_console:  { label: 'Game Console',  hex: 'var(--color-type-game-console)' },
  nas:           { label: 'NAS',           hex: 'var(--color-type-nas)' },
  wearable:      { label: 'Wearable',      hex: 'var(--color-type-wearable)' },
  unknown:       { label: 'Unknown',       hex: 'var(--color-type-unknown)' },
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
</script>

<template>
  <div class="device-row" :class="{ 'device-row--offline': !device.is_online }">
    <!-- 状态点 -->
    <span
      class="status-dot"
      :class="device.is_online ? 'online' : 'offline'"
      role="status"
      :aria-label="device.is_online ? $t('common.online') : $t('common.offline')"
    />

    <!-- 类型图标 -->
    <div class="type-icon" :style="typeIconStyle(device.device_type)">
      <el-icon :size="16">
        <component :is="typeIcon(device.device_type)" />
      </el-icon>
    </div>

    <!-- 设备名 + vendor -->
    <div class="name-block">
      <div class="device-name">{{ device.alias || device.hostname || $t('devices.unnamed') }}</div>
      <div class="device-vendor" v-if="device.vendor">{{ device.vendor }}</div>
    </div>

    <!-- 弹性占位 -->
    <div class="spacer" />

    <!-- IP 地址 mono -->
    <span class="device-ip">{{ device.ip || '—' }}</span>

    <!-- 类型徽章 -->
    <span class="type-badge" :style="typeBadgeStyle(device.device_type)">
      {{ $t(`common.deviceTypes.${device.device_type}`) }}
    </span>

    <!-- 操作按钮 -->
    <div class="row-actions">
      <el-button size="small" link @click="$emit('detail', device)">{{ $t('common.detail') }}</el-button>
      <el-button size="small" link @click="$emit('edit', device)">{{ $t('common.edit') }}</el-button>
      <el-button size="small" link type="danger" @click="$emit('delete', device)">{{ $t('common.delete') }}</el-button>
    </div>
  </div>
</template>

<style scoped>
.device-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 52px;
  padding: 0 var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background var(--duration-fast) var(--easing-standard);
  cursor: default;
}

.device-row:hover {
  background: var(--color-surface-raised);
}

.device-row--offline {
  opacity: 0.65;
}

/* 状态指示点 8px */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.online {
  background: var(--color-online);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.45);
  transition: box-shadow var(--duration-base) var(--easing-standard);
}

.status-dot.offline {
  background: var(--color-offline);
}

.device-row:hover .status-dot.online {
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.7);
}

/* 类型图标 32x32 */
.type-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 设备名 + vendor */
.name-block {
  min-width: 0;
  max-width: 280px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 1;
}

.device-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.2;
}

.device-vendor {
  font-size: 11px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.2;
}

/* 弹性占位 */
.spacer {
  flex: 1;
}

/* IP mono */
.device-ip {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
  min-width: 110px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* 类型徽章 */
.type-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  letter-spacing: 0.01em;
  flex-shrink: 0;
  min-width: 80px;
  text-align: center;
}

/* 操作按钮 */
.row-actions {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--easing-standard);
}

.device-row:hover .row-actions,
.device-row:focus-within .row-actions {
  opacity: 1;
}

.row-actions .el-button {
  font-size: 12px;
  padding: 4px 8px;
}
</style>

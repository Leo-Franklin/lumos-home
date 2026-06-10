<script setup>
import { computed } from 'vue'
import {
  VideoCameraFilled,
  Monitor,
  Iphone,
  Cpu,
  QuestionFilled,
  Connection,
  Grid,
  Film,
  Printer,
  Microphone,
  Trophy,
  Box,
  Watch,
} from '@element-plus/icons-vue'

const props = defineProps({
  device: { type: Object, required: true },
})
defineEmits(['edit', 'delete', 'detail'])

const TYPE_CONFIG = {
  camera: { label: 'Camera', hex: 'var(--color-type-camera)' },
  computer: { label: 'Computer', hex: 'var(--color-type-computer)' },
  phone: { label: 'Phone', hex: 'var(--color-type-phone)' },
  iot: { label: 'IoT', hex: 'var(--color-type-iot)' },
  router: { label: 'Router', hex: 'var(--color-type-router)' },
  tablet: { label: 'Tablet', hex: 'var(--color-type-tablet)' },
  tv: { label: 'TV', hex: 'var(--color-type-tv)' },
  printer: { label: 'Printer', hex: 'var(--color-type-printer)' },
  smart_speaker: { label: 'Smart Speaker', hex: 'var(--color-type-smart-speaker)' },
  game_console: { label: 'Game Console', hex: 'var(--color-type-game-console)' },
  nas: { label: 'NAS', hex: 'var(--color-type-nas)' },
  wearable: { label: 'Wearable', hex: 'var(--color-type-wearable)' },
  unknown: { label: 'Unknown', hex: 'var(--color-type-unknown)' },
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

function parseScanMetadata(raw) {
  if (!raw) return null
  try {
    const meta = JSON.parse(raw)
    return meta && typeof meta === 'object' ? meta : null
  } catch {
    return null
  }
}

const typeConfidence = computed(() => {
  const confidence = parseScanMetadata(props.device.scan_metadata)?.type_confidence
  if (confidence === undefined || confidence === null) return null
  const value = Number(confidence)
  return Number.isFinite(value) ? Math.round(value * 100) : null
})

const confidenceLevel = computed(() => {
  const pct = typeConfidence.value
  if (pct === null) return null
  if (pct >= 80) return 'high'
  if (pct >= 50) return 'medium'
  return 'low'
})
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

    <!-- 类型徽章 + 置信度 -->
    <div class="type-block">
      <span class="type-badge" :style="typeBadgeStyle(device.device_type)">
        {{ $t(`common.deviceTypes.${device.device_type}`) }}
      </span>
      <span
        v-if="typeConfidence !== null"
        class="confidence-badge"
        :class="`confidence-badge--${confidenceLevel}`"
        :title="$t('devices.typeConfidence')"
      >
        {{ typeConfidence }}%
      </span>
    </div>

    <!-- 操作按钮 -->
    <div class="row-actions">
      <el-button size="small" link @click="$emit('detail', device)">{{
        $t('common.detail')
      }}</el-button>
      <el-button size="small" link @click="$emit('edit', device)">{{
        $t('common.edit')
      }}</el-button>
      <el-button size="small" link type="danger" @click="$emit('delete', device)">{{
        $t('common.delete')
      }}</el-button>
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

/* 类型徽章 + 置信度 */
.type-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  min-width: 80px;
}

.type-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  letter-spacing: 0.01em;
  text-align: center;
}

.confidence-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.confidence-badge--high {
  color: var(--color-online);
}

.confidence-badge--medium {
  color: var(--color-text-secondary);
}

.confidence-badge--low {
  color: var(--color-text-muted);
}

/* 操作按钮：触屏设备始终可见，鼠标设备悬停显示 */
.row-actions {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
  opacity: 1;
}

@media (hover: hover) and (pointer: fine) {
  .row-actions {
    opacity: 0;
    transition: opacity var(--duration-fast) var(--easing-standard);
  }

  .device-row:hover .row-actions,
  .device-row:focus-within .row-actions {
    opacity: 1;
  }
}

@media (max-width: 767.98px) {
  .device-row {
    flex-wrap: wrap;
    height: auto;
    min-height: 52px;
    padding: var(--space-3) var(--space-4);
    gap: var(--space-2);
  }

  .device-ip,
  .type-block {
    display: none;
  }

  .name-block {
    max-width: none;
    flex: 1;
    min-width: 0;
  }

  .row-actions {
    width: 100%;
    justify-content: flex-end;
    padding-top: var(--space-1);
    border-top: 1px solid var(--color-border-subtle);
    margin-top: var(--space-1);
  }
}

.row-actions .el-button {
  font-size: 12px;
  padding: 4px 8px;
}
</style>

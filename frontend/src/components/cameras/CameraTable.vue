<script setup>
import {
  Edit,
  Delete,
  Search,
  VideoPlay,
  Camera,
  VideoCamera,
  VideoPause,
  VideoCameraFilled,
  ArrowDown,
  Setting,
  MoreFilled,
} from '@element-plus/icons-vue'

defineProps({
  cameras: { type: Array, required: true },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['edit', 'record', 'preview', 'more'])
</script>

<template>
  <el-table v-loading="loading" :data="cameras" style="width: 100%">
    <el-table-column :label="$t('cameras.deviceMac')" prop="device_mac" width="160" />
    <el-table-column :label="$t('cameras.onvifHost')" width="170">
      <template #default="{ row }">{{ row.onvif_host }}:{{ row.onvif_port }}</template>
    </el-table-column>
    <el-table-column :label="$t('cameras.rtspUrl')" min-width="200">
      <template #default="{ row }">
        <span class="rtsp-url">{{ row.rtsp_url || '—' }}</span>
      </template>
    </el-table-column>
    <el-table-column :label="$t('cameras.streamProfile')" prop="stream_profile" width="110" />
    <el-table-column :label="$t('cameras.online')" width="80" align="center">
      <template #default="{ row }">
        <el-tag :type="row.is_online ? 'success' : 'info'" size="small">
          {{ row.is_online ? $t('cameras.online') : $t('cameras.offline') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('cameras.recording')" width="90" align="center">
      <template #default="{ row }">
        <el-tag :type="row.is_recording ? 'danger' : 'info'" size="small">
          {{ row.is_recording ? $t('cameras.recording') : $t('cameras.idle') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('cameras.lastProbe')" width="160">
      <template #default="{ row }">{{ $d(row.last_probe_at, 'short') }}</template>
    </el-table-column>
    <el-table-column :label="$t('cameras.actions')" min-width="220" align="center">
      <template #default="{ row }">
        <div class="action-group">
          <el-tooltip :content="$t('cameras.edit')" :show-after="400">
            <el-button
              class="action-btn"
              size="small"
              :icon="Edit"
              :aria-label="$t('cameras.edit')"
              @click="emit('edit', row)"
            />
          </el-tooltip>
          <el-tooltip
            :content="row.is_recording ? $t('cameras.stopRecord') : $t('cameras.startRecord')"
            :show-after="400"
          >
            <el-button
              class="action-btn"
              :class="row.is_recording ? 'action-btn--recording' : 'action-btn--record'"
              size="small"
              :icon="row.is_recording ? VideoPause : VideoCameraFilled"
              :aria-label="row.is_recording ? $t('cameras.stopRecord') : $t('cameras.startRecord')"
              @click="emit('record', row)"
            />
          </el-tooltip>
          <el-dropdown trigger="click" @command="(cmd) => emit('preview', cmd, row)">
            <el-button
              class="action-btn action-btn--primary"
              size="small"
              :aria-label="$t('cameras.livePreview')"
            >
              <VideoPlay />
              <el-icon class="el-icon--right" aria-hidden="true"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="live">
                  <el-icon aria-hidden="true"><VideoPlay /></el-icon>{{ $t('cameras.livePreview') }}
                </el-dropdown-item>
                <el-dropdown-item command="snapshot">
                  <el-icon aria-hidden="true"><Camera /></el-icon>{{ $t('cameras.snapshot') }}
                </el-dropdown-item>
                <el-dropdown-item command="hls">
                  <el-icon aria-hidden="true"><VideoCamera /></el-icon>{{ $t('cameras.hlsLive') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-dropdown trigger="click" @command="(cmd) => emit('more', cmd, row)">
            <el-button class="action-btn" size="small" :aria-label="$t('cameras.managePresets')">
              <el-icon aria-hidden="true"><MoreFilled /></el-icon>
              <el-icon class="el-icon--right" aria-hidden="true"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="probe">
                  <el-icon aria-hidden="true"><Search /></el-icon>{{ $t('cameras.onvifProbe') }}
                </el-dropdown-item>
                <el-dropdown-item command="presets">
                  <el-icon aria-hidden="true"><Setting /></el-icon>{{ $t('cameras.managePresets') }}
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <el-icon aria-hidden="true"><Delete /></el-icon>
                  <span class="text-danger">{{ $t('cameras.delete') }}</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<style scoped>
.rtsp-url {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--color-text-secondary);
  word-break: break-all;
}

.text-danger {
  color: var(--color-error);
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-header-text-color: var(--color-text-muted);
  --el-table-border-color: var(--color-border-subtle);
  --el-table-row-hover-bg-color: var(--color-surface-raised);
  background: transparent;
}

:deep(.el-table__header th.el-table__cell) {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 0;
}

:deep(.el-table__body td.el-table__cell) {
  padding: 10px 0;
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}

.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  flex-wrap: nowrap;
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-raised);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--color-text-primary);
  --el-button-active-bg-color: var(--color-surface-overlay);
  --el-button-active-border-color: transparent;
  height: 28px;
  width: 28px;
  padding: 3px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--easing-standard),
    color var(--duration-fast) var(--easing-standard);
  flex-shrink: 0;
}

.action-btn:hover:not(:disabled) {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-btn--primary {
  width: auto;
  padding: 0 var(--space-3);
  gap: var(--space-1);
  color: var(--color-primary);
}

.action-btn--primary:hover {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}

.action-btn--record {
  color: var(--color-primary);
  background: var(--color-primary-subtle);
  border-color: var(--color-primary);
}

.action-btn--record:hover {
  background: var(--color-primary);
  color: #fff;
}

.action-btn--recording {
  color: var(--color-error);
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--color-error);
  animation: recording-pulse 1.5s ease-in-out infinite;
}

.action-btn--recording:hover {
  background: var(--color-error);
  color: #fff;
}

@keyframes recording-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(239, 68, 68, 0);
  }
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
}
</style>

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
  Setting,
  MoreFilled,
  QuestionFilled,
} from '@element-plus/icons-vue'

defineProps({
  cameras: { type: Array, required: true },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['edit', 'record', 'preview', 'more'])

function isMediaReady(row) {
  return Boolean(row.rtsp_url)
}

function isRecordDisabled(row) {
  return !isMediaReady(row) && !row.is_recording
}
</script>

<template>
  <div class="table-scroll">
    <el-table v-loading="loading" :data="cameras" style="width: 100%">
      <el-table-column :label="$t('cameras.deviceMac')" prop="device_mac" width="160" />
      <el-table-column width="170">
        <template #header>
          <span class="col-header">
            {{ $t('cameras.colCameraAddress') }}
            <el-tooltip
              :content="$t('cameras.colCameraAddressTip')"
              placement="top"
              :show-after="300"
            >
              <el-icon class="col-header-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <template #default="{ row }">{{ row.onvif_host }}:{{ row.onvif_port }}</template>
      </el-table-column>
      <el-table-column min-width="180">
        <template #header>
          <span class="col-header">
            {{ $t('cameras.colStreamUrl') }}
            <el-tooltip :content="$t('cameras.colStreamUrlTip')" placement="top" :show-after="300">
              <el-icon class="col-header-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
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
      <el-table-column
        :label="$t('cameras.actions')"
        min-width="200"
        align="center"
        class-name="action-cell"
        label-class-name="action-cell"
      >
        <template #default="{ row }">
          <div class="action-group">
            <el-tooltip
              :content="isMediaReady(row) ? $t('cameras.onvifProbe') : $t('cameras.probeFirstStep')"
              :show-after="400"
            >
              <el-button
                class="action-btn"
                :class="{ 'action-btn--setup-required': !isMediaReady(row) }"
                size="small"
                :icon="Search"
                :aria-label="
                  isMediaReady(row) ? $t('cameras.onvifProbe') : $t('cameras.probeFirstStep')
                "
                @click="emit('more', 'probe', row)"
              />
            </el-tooltip>
            <el-tooltip :content="$t('cameras.edit')" :show-after="400">
              <el-button
                class="action-btn"
                size="small"
                :icon="Edit"
                :aria-label="$t('cameras.edit')"
                @click="emit('edit', row)"
              />
            </el-tooltip>
            <span class="action-divider" aria-hidden="true" />
            <el-tooltip
              :content="
                isRecordDisabled(row)
                  ? $t('cameras.noRtspWarning')
                  : row.is_recording
                    ? $t('cameras.stopRecord')
                    : $t('cameras.startRecord')
              "
              :show-after="400"
            >
              <span class="action-btn-trigger">
                <el-button
                  class="action-btn"
                  :class="row.is_recording ? 'action-btn--recording' : 'action-btn--record'"
                  size="small"
                  :icon="row.is_recording ? VideoPause : VideoCameraFilled"
                  :aria-label="
                    row.is_recording ? $t('cameras.stopRecord') : $t('cameras.startRecord')
                  "
                  :disabled="isRecordDisabled(row)"
                  @click="emit('record', row)"
                />
              </span>
            </el-tooltip>
            <el-tooltip
              :content="isMediaReady(row) ? $t('cameras.livePreview') : $t('cameras.noRtspWarning')"
              :show-after="400"
            >
              <span class="action-btn-trigger">
                <el-button
                  class="action-btn action-btn--live"
                  size="small"
                  :icon="VideoPlay"
                  :aria-label="$t('cameras.livePreview')"
                  :disabled="!isMediaReady(row)"
                  @click="emit('preview', 'live', row)"
                />
              </span>
            </el-tooltip>
            <el-tooltip :content="$t('cameras.moreActions')" :show-after="400">
              <span class="action-btn-trigger">
                <el-dropdown trigger="click" @command="(cmd) => emit('more', cmd, row)">
                  <el-button
                    class="action-btn"
                    size="small"
                    :aria-label="$t('cameras.moreActions')"
                  >
                    <el-icon aria-hidden="true"><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="snapshot" :disabled="!isMediaReady(row)">
                        <el-icon aria-hidden="true"><Camera /></el-icon>
                        {{ $t('cameras.snapshot') }}
                      </el-dropdown-item>
                      <el-dropdown-item command="hls" :disabled="!isMediaReady(row)">
                        <el-icon aria-hidden="true"><VideoCamera /></el-icon>
                        {{ $t('cameras.hlsLive') }}
                      </el-dropdown-item>
                      <el-dropdown-item command="presets" divided :disabled="!isMediaReady(row)">
                        <el-icon aria-hidden="true"><Setting /></el-icon>
                        {{ $t('cameras.managePresets') }}
                      </el-dropdown-item>
                      <el-dropdown-item command="delete" divided>
                        <el-icon aria-hidden="true"><Delete /></el-icon>
                        <span class="text-danger">{{ $t('cameras.delete') }}</span>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </span>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.table-scroll :deep(.el-table) {
  min-width: 960px;
}
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

:deep(.el-table__body td.action-cell.el-table__cell) {
  overflow: visible;
  padding-top: 12px;
  padding-bottom: 12px;
}

:deep(.el-table__header th.action-cell.el-table__cell) {
  overflow: visible;
}

:deep(td.action-cell .cell),
:deep(th.action-cell .cell) {
  overflow: visible;
  padding-left: 10px;
  padding-right: 10px;
}

.col-header {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.col-header-tip {
  font-size: 12px;
  color: var(--color-text-muted);
  cursor: help;
  vertical-align: middle;
}

.col-header-tip:hover {
  color: var(--color-text-secondary);
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}

.action-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: nowrap;
  padding: 4px 2px;
  max-width: 100%;
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

.action-divider {
  width: 1px;
  height: 16px;
  background: var(--color-border-subtle);
  flex-shrink: 0;
  margin: 0 2px;
}

.action-btn-trigger {
  display: inline-flex;
  line-height: 0;
}

.action-btn--setup-required {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 14%, var(--color-surface));
  border-color: color-mix(in srgb, var(--color-warning) 50%, transparent);
  animation: setup-pulse 2s ease-in-out infinite;
}

.action-btn--setup-required:hover {
  background: color-mix(in srgb, var(--color-warning) 22%, var(--color-surface));
  border-color: var(--color-warning);
  color: var(--color-warning);
}

@keyframes setup-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-warning) 35%, transparent);
  }
  50% {
    box-shadow: 0 0 0 4px transparent;
  }
}

.action-btn--live {
  color: var(--color-primary);
}

.action-btn--live:hover {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}

.action-btn--record {
  color: var(--color-primary);
}

.action-btn--record:hover {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
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

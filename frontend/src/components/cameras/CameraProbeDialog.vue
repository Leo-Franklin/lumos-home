<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
import { isStreamSelectable, resolveInitialStreamIndex } from '@/utils/probeStream'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  loading: { type: Boolean, default: false },
  applying: { type: Boolean, default: false },
  result: { type: Object, default: null },
  currentRtspUrl: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'apply'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const selectedIndex = ref(null)

const DEVICE_INFO_FIELDS = [
  { key: 'manufacturer', labelKey: 'deviceManufacturer' },
  { key: 'model', labelKey: 'deviceModel' },
  { key: 'firmware', labelKey: 'deviceFirmware' },
  { key: 'serial', labelKey: 'deviceSerial' },
]

const STREAM_NAME_KEYS = {
  mainStream: 'streamNameMain',
  minorStream: 'streamNameSub',
  subStream: 'streamNameSub',
}

watch(
  () => [props.result, props.currentRtspUrl],
  () => {
    if (!props.result?.profiles?.length) {
      selectedIndex.value = null
      return
    }
    selectedIndex.value = resolveInitialStreamIndex(props.result.profiles, {
      currentRtspUrl: props.currentRtspUrl || null,
      autoSetRtspUrl: props.result.auto_set_rtsp_url,
    })
  },
  { immediate: true },
)

const activeProfile = computed(() => {
  if (selectedIndex.value == null || !props.result?.profiles) return null
  return props.result.profiles.find((p) => p.index === selectedIndex.value) ?? null
})

const deviceInfoItems = computed(() => {
  const info = props.result?.device_info
  if (!info) return []
  return DEVICE_INFO_FIELDS.filter((f) => info[f.key]).map((f) => ({
    label: t(`cameras.${f.labelKey}`),
    value: info[f.key],
  }))
})

function friendlyStreamName(name) {
  const key = STREAM_NAME_KEYS[name]
  return key ? t(`cameras.${key}`) : t('cameras.streamNameRaw', { name })
}

function selectStream(row) {
  if (!isStreamSelectable(row)) return
  selectedIndex.value = row.index
}

function applySelection() {
  const profile = activeProfile.value
  if (!isStreamSelectable(profile)) return
  emit('apply', {
    rtsp_url: profile.rtsp_url,
    stream_profile: profile.name,
    stream_label: friendlyStreamName(profile.name),
  })
}
</script>

<template>
  <el-dialog
    v-model="visible"
    width="600px"
    class="probe-dialog"
    :destroy-on-close="true"
    align-center
  >
    <template #header>
      <div class="probe-header">
        <span class="probe-title">{{ t('cameras.probeResult') }}</span>
        <span class="probe-hint">{{ t('cameras.probeResultHintShort') }}</span>
      </div>
    </template>

    <div v-if="loading" class="probe-loading">
      <el-icon class="probe-loading-icon" aria-hidden="true"><Loading /></el-icon>
      <el-text>{{ t('cameras.probing') }}</el-text>
    </div>

    <template v-else-if="result">
      <div v-if="deviceInfoItems.length" class="device-grid">
        <div v-for="item in deviceInfoItems" :key="item.label" class="device-kv">
          <span class="device-k">{{ item.label }}</span>
          <el-tooltip
            :content="item.value"
            placement="top"
            :show-after="300"
            :disabled="String(item.value).length < 28"
          >
            <span class="device-v">{{ item.value }}</span>
          </el-tooltip>
        </div>
      </div>

      <div class="streams-panel">
        <div class="streams-panel-head">
          <span class="streams-panel-title">{{ t('cameras.availableStreams') }}</span>
          <span class="streams-panel-count">{{ result.profiles?.length || 0 }}</span>
        </div>
        <div class="stream-list" role="radiogroup" :aria-label="t('cameras.availableStreams')">
          <div
            v-for="row in result.profiles"
            :key="row.index"
            class="stream-item"
            :class="{
              'stream-item--selected': row.index === selectedIndex,
              'stream-item--disabled': !isStreamSelectable(row),
            }"
            role="radio"
            :aria-checked="row.index === selectedIndex"
            :aria-disabled="!isStreamSelectable(row)"
            :tabindex="isStreamSelectable(row) ? 0 : -1"
            @click="selectStream(row)"
            @keydown.enter.prevent="selectStream(row)"
            @keydown.space.prevent="selectStream(row)"
          >
            <span class="stream-radio" aria-hidden="true" />
            <div class="stream-item-body">
              <div class="stream-item-top">
                <span class="stream-label">{{ friendlyStreamName(row.name) }}</span>
                <el-tag v-if="!isStreamSelectable(row)" type="info" size="small" effect="plain">
                  {{ t('cameras.streamUnavailable') }}
                </el-tag>
              </div>
              <el-tooltip
                v-if="row.rtsp_url"
                :content="row.rtsp_url"
                placement="top"
                :show-after="300"
              >
                <span class="stream-url">{{ row.rtsp_url }}</span>
              </el-tooltip>
              <span v-else class="stream-url stream-url--empty">{{
                t('cameras.streamNoUrl')
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <p v-if="activeProfile && isStreamSelectable(activeProfile)" class="stream-selection-hint">
        {{ t('cameras.probeCurrentSelection', { stream: friendlyStreamName(activeProfile.name) }) }}
      </p>

      <el-alert
        v-else-if="result.profiles?.length && !result.profiles.some(isStreamSelectable)"
        type="warning"
        class="probe-result-alert"
        :closable="false"
        show-icon
        :title="t('cameras.probeNoStreamUrl')"
      />
    </template>

    <template #footer>
      <el-button @click="visible = false">{{ t('common.close') }}</el-button>
      <el-button
        type="primary"
        :loading="applying"
        :disabled="!isStreamSelectable(activeProfile)"
        @click="applySelection"
      >
        {{ t('cameras.probeApplyStream') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.probe-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-right: 24px;
}

.probe-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.3;
}

.probe-hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.probe-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 20px 0;
  color: var(--color-text-secondary);
}

.probe-loading-icon {
  font-size: 18px;
  animation: probe-spin 1s linear infinite;
}

@keyframes probe-spin {
  to {
    transform: rotate(360deg);
  }
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 14px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-raised);
}

.device-kv {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
  font-size: 12px;
  line-height: 1.35;
}

.device-k {
  flex-shrink: 0;
  width: 52px;
  color: var(--color-text-muted);
}

.device-v {
  min-width: 0;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.streams-panel {
  margin-top: 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.streams-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--color-surface-raised);
  border-bottom: 1px solid var(--color-border-subtle);
}

.streams-panel-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.streams-panel-count {
  font-size: 11px;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

.stream-list {
  display: flex;
  flex-direction: column;
}

.stream-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-subtle);
  cursor: pointer;
  transition: background var(--duration-fast) var(--easing-standard);
}

.stream-item:last-child {
  border-bottom: none;
}

.stream-item:hover:not(.stream-item--disabled) {
  background: var(--color-surface-raised);
}

.stream-item--selected {
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
}

.stream-item--selected:hover {
  background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
}

.stream-item--disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.stream-radio {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  margin-top: 2px;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  background: transparent;
  transition:
    border-color var(--duration-fast) var(--easing-standard),
    background var(--duration-fast) var(--easing-standard);
}

.stream-item--selected .stream-radio {
  border-color: var(--color-primary);
  background: var(--color-primary);
  box-shadow: inset 0 0 0 2px var(--color-surface);
}

.stream-item-body {
  min-width: 0;
  flex: 1;
}

.stream-item-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.stream-label {
  font-size: 13px;
  color: var(--color-text-primary);
}

.stream-url {
  display: block;
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.35;
}

.stream-url--empty {
  color: var(--color-text-muted);
}

.stream-selection-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.probe-result-alert {
  margin-top: 12px;
}

.probe-result-alert :deep(.el-alert__title) {
  font-size: 12px;
  line-height: 1.45;
}

.probe-dialog :deep(.el-dialog__body) {
  padding: 14px 20px;
}

.probe-dialog :deep(.el-dialog__footer) {
  padding: 10px 20px;
}
</style>

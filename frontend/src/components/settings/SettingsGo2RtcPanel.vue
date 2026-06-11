<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CircleCheck, CircleClose, VideoCamera } from '@element-plus/icons-vue'
import { updateGo2RtcSettings } from '@/api/system'
import { useApiError } from '@/composables/useApiError'

const props = defineProps({
  status: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['updated'])

const { t } = useI18n()
const handleError = useApiError()

const saving = ref(false)
const candidatesText = ref('')

watch(
  () => props.status?.webrtc_candidates,
  (list) => {
    candidatesText.value = Array.isArray(list) ? list.join('\n') : ''
  },
  { immediate: true },
)

const connectionLabel = computed(() => {
  if (!props.status?.enabled) return t('settings.go2rtc.stateDisabled')
  return props.status.connected
    ? t('settings.go2rtc.stateConnected')
    : t('settings.go2rtc.stateUnreachable')
})

const connectionTone = computed(() => {
  if (!props.status?.enabled) return 'muted'
  return props.status.connected ? 'ok' : 'warn'
})

function parseCandidates(raw) {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

async function onToggle(enabled) {
  saving.value = true
  try {
    const { data } = await updateGo2RtcSettings({ enabled })
    emit('updated', data)
  } catch (e) {
    handleError(e)
  } finally {
    saving.value = false
  }
}

async function saveCandidates() {
  saving.value = true
  try {
    const { data } = await updateGo2RtcSettings({
      webrtc_candidates: parseCandidates(candidatesText.value),
    })
    emit('updated', data)
  } catch (e) {
    handleError(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="go2rtc-panel">
    <el-skeleton v-if="loading && !status" :rows="3" animated />

    <template v-else-if="status">
      <div class="go2rtc-header">
        <div class="go2rtc-title-row">
          <span class="go2rtc-icon" aria-hidden="true">
            <el-icon><VideoCamera /></el-icon>
          </span>
          <div>
            <p class="go2rtc-title">{{ $t('settings.go2rtc.title') }}</p>
            <p class="go2rtc-desc">{{ $t('settings.go2rtc.desc') }}</p>
          </div>
        </div>
        <el-switch
          :model-value="status.enabled"
          :loading="saving"
          :active-text="$t('settings.go2rtc.enabled')"
          :inactive-text="$t('settings.go2rtc.disabled')"
          @change="onToggle"
        />
      </div>

      <div class="go2rtc-meta">
        <div class="meta-chip">
          <span class="meta-label">{{ $t('settings.go2rtc.connection') }}</span>
          <span class="meta-value" :class="`meta-value--${connectionTone}`">
            <el-icon class="state-icon">
              <CircleCheck v-if="connectionTone === 'ok'" />
              <CircleClose v-else-if="connectionTone === 'warn'" />
            </el-icon>
            {{ connectionLabel }}
          </span>
        </div>
        <div class="meta-chip">
          <span class="meta-label">{{ $t('settings.go2rtc.apiUrl') }}</span>
          <span class="meta-value mono">{{ status.api_url }}</span>
        </div>
        <div class="meta-chip">
          <span class="meta-label">{{ $t('settings.go2rtc.rtspUrl') }}</span>
          <span class="meta-value mono">{{ status.rtsp_url }}</span>
        </div>
        <div v-if="status.has_embedded_binary" class="meta-chip">
          <span class="meta-label">{{ $t('settings.go2rtc.embeddedRunner') }}</span>
          <span
            class="meta-value"
            :class="status.embedded_runner ? 'meta-value--ok' : 'meta-value--muted'"
          >
            {{
              status.embedded_runner
                ? $t('settings.go2rtc.runnerActive')
                : $t('settings.go2rtc.runnerIdle')
            }}
          </span>
        </div>
      </div>

      <div class="candidates-block">
        <label class="candidates-label" for="go2rtc-candidates">
          {{ $t('settings.go2rtc.candidatesLabel') }}
        </label>
        <p class="candidates-hint">{{ $t('settings.go2rtc.candidatesHint') }}</p>
        <el-input
          id="go2rtc-candidates"
          v-model="candidatesText"
          type="textarea"
          :rows="4"
          :placeholder="$t('settings.go2rtc.candidatesPlaceholder')"
        />
        <div class="candidates-actions">
          <el-button type="primary" :loading="saving" @click="saveCandidates">
            {{ $t('settings.go2rtc.saveCandidates') }}
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.go2rtc-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
}

.go2rtc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.go2rtc-title-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.go2rtc-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
  flex-shrink: 0;
}

.go2rtc-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.go2rtc-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
  max-width: 420px;
}

.go2rtc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.meta-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
  min-width: 140px;
}

.meta-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.meta-value {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.meta-value--ok {
  color: var(--color-online);
}

.meta-value--warn {
  color: var(--color-warning);
}

.meta-value--muted {
  color: var(--color-text-muted);
}

.state-icon {
  font-size: 14px;
}

.mono {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  word-break: break-all;
}

.candidates-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.candidates-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.candidates-hint {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-muted);
}

.candidates-actions {
  display: flex;
  justify-content: flex-end;
}
</style>

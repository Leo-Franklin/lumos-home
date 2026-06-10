<script setup>
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { QuestionFilled } from '@element-plus/icons-vue'
import { useDevicesStore } from '@/stores/devices'
import { useDLNAStore } from '@/stores/dlna'

const props = defineProps({
  mode: { type: String, default: 'add' }, // 'add' | 'edit'
  submitting: { type: Boolean, default: false },
})
const emit = defineEmits(['submit', 'cancel'])

const visible = defineModel({ type: Boolean, required: true })
const form = defineModel('form', { type: Object, required: true })

const { t } = useI18n()
const devicesStore = useDevicesStore()
const dlnaStore = useDLNAStore()

const title = computed(() =>
  props.mode === 'add' ? t('cameras.addCamera') : t('cameras.editCamera'),
)
const isAdd = computed(() => props.mode === 'add')
const formHint = computed(() =>
  isAdd.value ? t('cameras.formHintAdd') : t('cameras.formHintEdit'),
)

watch(
  () => form.value.device_mac,
  (mac) => {
    if (!isAdd.value || !mac) return
    const device = devicesStore.items.find((d) => d.mac === mac)
    if (device?.ip) form.value.onvif_host = device.ip
  },
)

function onSubmit() {
  emit('submit')
}
function onCancel() {
  emit('cancel')
}
</script>

<template>
  <el-dialog
    v-model="visible"
    width="520px"
    class="camera-form-dialog"
    :close-on-press-escape="!submitting"
    :destroy-on-close="true"
    align-center
    @close="onCancel"
  >
    <template #header>
      <div class="form-header">
        <span class="form-title">{{ title }}</span>
        <span class="form-hint">{{ formHint }}</span>
      </div>
    </template>

    <el-form :model="form" label-width="128px" class="camera-form">
      <template v-if="isAdd">
        <div class="form-section-label">{{ t('cameras.sectionDevice') }}</div>
        <el-form-item>
          <template #label>
            <span class="form-label">
              {{ t('cameras.deviceMac') }}
              <el-tooltip :content="t('cameras.deviceMacTip')" placement="top" :show-after="300">
                <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-select
            v-model="form.device_mac"
            :placeholder="t('cameras.selectDevice')"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="d in devicesStore.items"
              :key="d.mac"
              :label="`${d.alias || d.hostname || d.mac} (${d.ip})`"
              :value="d.mac"
            />
          </el-select>
        </el-form-item>
      </template>

      <el-divider content-position="left">{{ t('cameras.sectionOnvif') }}</el-divider>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('cameras.onvifHost') }}
            <el-tooltip :content="t('cameras.onvifHostTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input v-model="form.onvif_host" :placeholder="t('cameras.onvifPlaceholder')" />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('cameras.onvifPort') }}
            <el-tooltip :content="t('cameras.onvifPortTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input-number
          v-model="form.onvif_port"
          :min="1"
          :max="65535"
          controls-position="right"
          class="port-input"
        />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('cameras.onvifUser') }}
            <el-tooltip :content="t('cameras.onvifUserTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input v-model="form.onvif_user" :placeholder="t('cameras.onvifUserPlaceholder')" />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('cameras.onvifPassword') }}
            <el-tooltip :content="t('cameras.onvifPasswordTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input
          v-model="form.onvif_password"
          type="password"
          show-password
          :placeholder="
            isAdd ? t('cameras.onvifPasswordHintAdd') : t('cameras.passwordPlaceholder')
          "
        />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('cameras.rtspPort') }}
            <el-tooltip :content="t('cameras.rtspPortTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input-number
          v-model="form.rtsp_port"
          :min="1"
          :max="65535"
          controls-position="right"
          class="port-input"
        />
      </el-form-item>

      <template v-if="!isAdd">
        <el-divider content-position="left">{{ t('cameras.sectionStream') }}</el-divider>

        <el-form-item>
          <template #label>
            <span class="form-label">
              {{ t('cameras.rtspUrl') }}
              <el-tooltip :content="t('cameras.colStreamUrlTip')" placement="top" :show-after="300">
                <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-input v-model="form.rtsp_url" :placeholder="t('cameras.rtspUrlPlaceholder')" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <span class="form-label">
              {{ t('cameras.streamProfile') }}
              <el-tooltip
                :content="t('cameras.streamProfileTip')"
                placement="top"
                :show-after="300"
              >
                <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-select v-model="form.stream_profile" style="width: 100%">
            <el-option value="mainStream" :label="t('cameras.mainStream')" />
            <el-option value="subStream" :label="t('cameras.subStream')" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">{{ t('cameras.sectionAdvanced') }}</el-divider>

        <el-form-item>
          <template #label>
            <span class="form-label">
              {{ t('cameras.dlnaAutoCast') }}
              <el-tooltip :content="t('cameras.dlnaAutoCastTip')" placement="top" :show-after="300">
                <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-select
            v-model="form.auto_cast_dlna"
            clearable
            :placeholder="t('cameras.dlnaPlaceholder')"
            style="width: 100%"
          >
            <el-option
              v-for="d in dlnaStore.devices"
              :key="d.udn"
              :label="d.friendly_name || d.udn"
              :value="d.udn"
            />
          </el-select>
        </el-form-item>
      </template>

      <el-alert
        v-if="isAdd"
        class="form-probe-reminder"
        type="info"
        :closable="false"
        show-icon
        :title="t('cameras.formProbeReminder')"
      />
    </el-form>

    <template #footer>
      <el-button :disabled="submitting" @click="onCancel">{{ t('cameras.cancel') }}</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmit">
        {{ isAdd ? t('cameras.add') : t('cameras.save') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.form-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 24px;
}

.form-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.3;
}

.form-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.form-section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
  letter-spacing: 0.02em;
}

.form-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.form-label-tip {
  font-size: 12px;
  color: var(--color-text-muted);
  cursor: help;
  vertical-align: middle;
}

.form-label-tip:hover {
  color: var(--color-text-secondary);
}

.camera-form :deep(.el-divider) {
  margin: 8px 0 16px;
}

.camera-form :deep(.el-divider__text) {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-surface-overlay);
}

.port-input {
  width: 160px;
}

.form-probe-reminder {
  margin-top: 4px;
}

.form-probe-reminder :deep(.el-alert__title) {
  font-size: 12px;
  line-height: 1.45;
}
</style>

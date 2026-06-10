<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import RecordingPresetPicker from '@/components/recording/RecordingPresetPicker.vue'
import RecordingParamOverrides from '@/components/recording/RecordingParamOverrides.vue'

const props = defineProps({
  camera: { type: Object, default: null },
  presets: { type: Array, required: true },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['start'])

const visible = defineModel({ type: Boolean, required: true })
const selectedPresetId = defineModel('selectedPresetId', { type: [String, null], default: null })
const overrides = defineModel('overrides', { type: Object, required: true })

const { t } = useI18n()

const title = computed(() =>
  props.camera
    ? t('cameras.startRecordingTitle', { host: props.camera.onvif_host })
    : t('cameras.startRecording'),
)
</script>

<template>
  <el-dialog v-model="visible" :title="title" width="860px" :destroy-on-close="true">
    <el-scrollbar style="padding-right: 8px">
      <RecordingPresetPicker v-model="selectedPresetId" :presets="presets" mode="cards" />
      <RecordingParamOverrides v-model="overrides" label-position="right" />
    </el-scrollbar>
    <template #footer>
      <el-button :disabled="saving" @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="emit('start')">
        {{ t('cameras.startRecording') }}
      </el-button>
    </template>
  </el-dialog>
</template>

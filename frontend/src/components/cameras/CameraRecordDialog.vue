<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  camera: { type: Object, default: null },
  presets: { type: Array, required: true },
  selectedPresetId: { type: [Number, null], default: null },
  overrides: { type: Object, required: true },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits([
  'update:modelValue',
  'update:selectedPresetId',
  'update:overrides',
  'start',
])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const title = computed(() =>
  props.camera
    ? t('cameras.startRecordingTitle', { host: props.camera.onvif_host })
    : t('cameras.startRecording'),
)

function togglePreset(id) {
  emit('update:selectedPresetId', props.selectedPresetId === id ? null : id)
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="860px"
    :destroy-on-close="true"
  >
    <el-scrollbar style="padding-right: 8px">
      <template v-if="presets.length">
        <p style="margin: 0 0 12px; color: var(--color-text-muted); font-size: 13px">
          {{ t('cameras.selectPresetOptional') }}
        </p>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px">
          <el-card
            v-for="p in presets"
            :key="p.id"
            shadow="hover"
            :class="['preset-card', { 'preset-card--selected': selectedPresetId === p.id }]"
            @click="togglePreset(p.id)"
          >
            <div class="preset-card__name">{{ p.name }}</div>
            <div class="preset-card__meta">{{ p.resolution }} &middot; {{ p.segment_duration }}s &middot; {{ p.bitrate }}k</div>
            <div class="preset-card__fps">{{ p.fps }} fps</div>
          </el-card>
        </div>
      </template>
      <el-empty v-else :description="t('cameras.noPresetsAvailable')" :image-size="50" />

      <el-divider content-position="left">{{ t('cameras.parameterOverrides') }}</el-divider>
      <el-form label-width="140px">
        <el-form-item :label="t('cameras.segmentSec')">
          <el-input-number
            v-model="overrides.segment_duration"
            :min="60"
            :max="3600"
            :placeholder="t('cameras.segmentSecPlaceholder')"
            style="width: 160px"
            clearable
          />
        </el-form-item>
        <el-form-item :label="t('cameras.bitrateKbps')">
          <el-input-number
            v-model="overrides.bitrate"
            :min="256"
            :max="20000"
            :step="256"
            :placeholder="t('cameras.bitrateKbpsPlaceholder')"
            style="width: 160px"
            clearable
          />
        </el-form-item>
        <el-form-item :label="t('cameras.frameRate')">
          <el-input-number
            v-model="overrides.fps"
            :min="5"
            :max="60"
            :placeholder="t('cameras.frameRatePlaceholder')"
            style="width: 160px"
            clearable
          />
        </el-form-item>
        <el-form-item :label="t('cameras.resolution')">
          <el-select
            v-model="overrides.resolution"
            :placeholder="t('cameras.selectResolution')"
            style="width: 160px"
            clearable
          >
            <el-option value="1920x1080" :label="t('cameras.res1920x1080')" />
            <el-option value="1280x720" :label="t('cameras.res1280x720')" />
            <el-option value="640x360" :label="t('cameras.res640x360')" />
          </el-select>
        </el-form-item>
      </el-form>
      <div style="margin-top: 8px; color: var(--color-text-muted); font-size: 12px">
        {{ t('cameras.useDefaultsOrEnterBelow') }}
      </div>
    </el-scrollbar>
    <template #footer>
      <el-button :disabled="saving" @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="emit('start')">
        {{ t('cameras.startRecording') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.preset-card {
  width: 130px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--easing-standard);
  border: 1px solid var(--color-border-subtle);
}

.preset-card:hover {
  border-color: var(--color-primary);
}

.preset-card--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-subtle);
}

.preset-card__name {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
}

.preset-card__meta {
  font-size: 11px;
  color: var(--color-text-muted);
}

.preset-card__fps {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}
</style>

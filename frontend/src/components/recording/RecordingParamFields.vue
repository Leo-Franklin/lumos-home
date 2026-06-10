<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { QuestionFilled } from '@element-plus/icons-vue'
import { useRecordingParams } from '@/composables/useRecordingParams'
import {
  SEGMENT_MIN,
  SEGMENT_MAX,
  BITRATE_MIN,
  BITRATE_MAX,
  BITRATE_STEP,
  FPS_MIN,
  FPS_MAX,
} from '@/constants/recordingParams'

defineProps({
  showName: { type: Boolean, default: true },
  showTemplates: { type: Boolean, default: false },
  labelPosition: { type: String, default: 'top' },
})

const model = defineModel({ type: Object, required: true })

const { t } = useI18n()
const {
  segmentQuickOptions,
  bitrateQuickOptions,
  fpsQuickOptions,
  presetTemplates,
  recommendedBitrate,
} = useRecordingParams()

const recBitrate = computed(() => recommendedBitrate(model.value.resolution))

function applyTemplate(tpl) {
  model.value.resolution = tpl.resolution
  model.value.segment_duration = tpl.segment_duration
  model.value.bitrate = tpl.bitrate
  model.value.fps = tpl.fps
}

function useRecommendedBitrate() {
  model.value.bitrate = recBitrate.value
}
</script>

<template>
  <div class="param-fields">
    <p v-if="showTemplates" class="param-fields__hint">{{ t('recording.presetFormHint') }}</p>

    <div v-if="showTemplates" class="param-templates">
      <span class="param-templates__label">{{ t('recording.presetTemplates') }}</span>
      <div class="param-templates__chips">
        <el-button
          v-for="tpl in presetTemplates"
          :key="tpl.key"
          size="small"
          plain
          @click="applyTemplate(tpl)"
        >
          {{ tpl.label }}
        </el-button>
      </div>
    </div>

    <el-form :model="model" :label-position="labelPosition" class="param-form">
      <el-form-item v-if="showName">
        <template #label>
          <span class="form-label">
            {{ t('recording.presetName') }}
            <el-tooltip :content="t('recording.presetNameTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input v-model="model.name" :placeholder="t('recording.presetNamePlaceholder')" />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('recording.resolution') }}
            <el-tooltip :content="t('recording.resolutionTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-select v-model="model.resolution" style="width: 100%">
          <el-option value="1920x1080" :label="t('recording.res1920x1080')">
            <span>{{ t('recording.res1920x1080') }}</span>
            <span class="option-hint">{{ t('recording.res1080Hint') }}</span>
          </el-option>
          <el-option value="1280x720" :label="t('recording.res1280x720')">
            <span>{{ t('recording.res1280x720') }}</span>
            <span class="option-hint">{{ t('recording.res720Hint') }}</span>
          </el-option>
          <el-option value="640x360" :label="t('recording.res640x360')">
            <span>{{ t('recording.res640x360') }}</span>
            <span class="option-hint">{{ t('recording.res360Hint') }}</span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('recording.segmentSec') }}
            <el-tooltip :content="t('recording.segmentSecTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <div class="quick-picks">
          <el-button
            v-for="opt in segmentQuickOptions"
            :key="opt.value"
            size="small"
            :type="model.segment_duration === opt.value ? 'primary' : 'default'"
            :plain="model.segment_duration !== opt.value"
            @click="model.segment_duration = opt.value"
          >
            {{ opt.label }}
          </el-button>
        </div>
        <el-input-number
          v-model="model.segment_duration"
          :min="SEGMENT_MIN"
          :max="SEGMENT_MAX"
          :step="60"
          controls-position="right"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('recording.bitrateKbps') }}
            <el-tooltip :content="t('recording.bitrateTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <div class="quick-picks">
          <el-button
            v-for="opt in bitrateQuickOptions"
            :key="opt.value"
            size="small"
            :type="model.bitrate === opt.value ? 'primary' : 'default'"
            :plain="model.bitrate !== opt.value"
            @click="model.bitrate = opt.value"
          >
            {{ opt.label }}
          </el-button>
        </div>
        <el-input-number
          v-model="model.bitrate"
          :min="BITRATE_MIN"
          :max="BITRATE_MAX"
          :step="BITRATE_STEP"
          controls-position="right"
          style="width: 100%"
        />
        <p class="field-hint">
          {{ t('recording.bitrateRecommended', { value: recBitrate }) }}
          <el-button
            v-if="model.bitrate !== recBitrate"
            link
            type="primary"
            size="small"
            @click="useRecommendedBitrate"
          >
            {{ t('recording.applyRecommended') }}
          </el-button>
        </p>
      </el-form-item>

      <el-form-item>
        <template #label>
          <span class="form-label">
            {{ t('recording.frameRate') }}
            <el-tooltip :content="t('recording.fpsTip')" placement="top" :show-after="300">
              <el-icon class="form-label-tip" aria-hidden="true"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <div class="quick-picks">
          <el-button
            v-for="opt in fpsQuickOptions"
            :key="opt.value"
            size="small"
            :type="model.fps === opt.value ? 'primary' : 'default'"
            :plain="model.fps !== opt.value"
            @click="model.fps = opt.value"
          >
            {{ opt.label }} fps
          </el-button>
        </div>
        <el-input-number
          v-model="model.fps"
          :min="FPS_MIN"
          :max="FPS_MAX"
          controls-position="right"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.param-fields__hint {
  margin: 0 0 var(--space-3);
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.param-templates {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border-subtle);
}

.param-templates__label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.param-templates__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
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
}

.option-hint {
  float: right;
  font-size: 11px;
  color: var(--color-text-muted);
}

.quick-picks {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.field-hint {
  margin: var(--space-1) 0 0;
  font-size: 11px;
  color: var(--color-text-muted);
}

.param-form :deep(.el-form-item) {
  margin-bottom: var(--space-3);
}

.param-form :deep(.el-form-item__label) {
  padding-bottom: var(--space-1);
  font-size: 12px;
  color: var(--color-text-secondary);
}
</style>

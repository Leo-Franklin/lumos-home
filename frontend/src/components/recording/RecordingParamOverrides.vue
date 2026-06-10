<script setup>
import { ref } from 'vue'
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

const props = defineProps({
  /** Show collapsible toggle (schedule). When false, always expanded (record dialog). */
  collapsible: { type: Boolean, default: false },
  /** Include segment_duration in override fields */
  showSegment: { type: Boolean, default: true },
  labelWidth: { type: String, default: '140px' },
  labelPosition: { type: String, default: 'right' },
  defaultExpanded: { type: Boolean, default: false },
})

const model = defineModel({ type: Object, required: true })

const { t } = useI18n()
const { segmentQuickOptions, bitrateQuickOptions, fpsQuickOptions, recommendedBitrate } =
  useRecordingParams()

const expanded = ref(props.defaultExpanded || !props.collapsible)

function useRecommendedBitrate() {
  model.value.bitrate = recommendedBitrate(model.value.resolution)
}
</script>

<template>
  <div class="param-overrides">
    <el-form-item v-if="collapsible" class="override-toggle">
      <el-button text type="primary" @click="expanded = !expanded">
        {{ expanded ? t('recording.hideOverrides') : t('recording.showOverrides') }}
        <span class="toggle-arrow" :class="{ open: expanded }" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M4 6l4 4 4-4"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
      </el-button>
    </el-form-item>

    <template v-if="!collapsible || expanded">
      <el-divider v-if="!collapsible" content-position="left">
        {{ t('recording.parameterOverrides') }}
      </el-divider>

      <el-form :label-width="labelWidth" :label-position="labelPosition" class="override-form">
        <el-form-item v-if="showSegment">
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
            :placeholder="t('recording.segmentSecPlaceholder')"
            style="width: 100%"
            clearable
          />
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
          <el-select
            v-model="model.resolution"
            :placeholder="t('recording.selectResolution')"
            style="width: 100%"
            clearable
          >
            <el-option value="1920x1080" :label="t('recording.res1920x1080')" />
            <el-option value="1280x720" :label="t('recording.res1280x720')" />
            <el-option value="640x360" :label="t('recording.res640x360')" />
          </el-select>
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
            :placeholder="t('recording.bitrateKbpsPlaceholder')"
            style="width: 100%"
            clearable
          />
          <p class="field-hint">
            {{ t('recording.bitrateRecommended', { value: recommendedBitrate(model.resolution) }) }}
            <el-button
              v-if="model.bitrate !== recommendedBitrate(model.resolution)"
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
            :placeholder="t('recording.frameRatePlaceholder')"
            style="width: 100%"
            clearable
          />
        </el-form-item>
      </el-form>

      <p v-if="!collapsible" class="override-hint">{{ t('recording.useDefaultsOrEnterBelow') }}</p>
    </template>
  </div>
</template>

<style scoped>
.override-toggle {
  margin-bottom: 0;
}

.toggle-arrow {
  display: inline-flex;
  margin-left: 4px;
  transition: transform var(--duration-fast) var(--easing-standard);
}

.toggle-arrow svg {
  width: 14px;
  height: 14px;
}

.toggle-arrow.open {
  transform: rotate(180deg);
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

.quick-picks {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.field-hint,
.override-hint {
  margin: var(--space-1) 0 0;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.override-hint {
  margin-top: var(--space-2);
}
</style>

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  SEGMENT_QUICK_VALUES,
  BITRATE_QUICK_VALUES,
  FPS_QUICK_VALUES,
  PRESET_TEMPLATE_KEYS,
  recommendedBitrate as calcRecommendedBitrate,
} from '@/constants/recordingParams'

/** i18n-aware helpers for recording parameter UI. */
export function useRecordingParams() {
  const { t } = useI18n()

  const resolutionLabelMap = computed(() => ({
    '1920x1080': t('recording.res1920x1080'),
    '1280x720': t('recording.res1280x720'),
    '640x360': t('recording.res640x360'),
  }))

  const segmentQuickOptions = computed(() =>
    SEGMENT_QUICK_VALUES.map((value) => ({
      value,
      label: t(`recording.segment${value}`),
    })),
  )

  const bitrateQuickOptions = computed(() =>
    BITRATE_QUICK_VALUES.map((value) => ({ value, label: String(value) })),
  )

  const fpsQuickOptions = computed(() =>
    FPS_QUICK_VALUES.map((value) => ({ value, label: String(value) })),
  )

  const presetTemplates = computed(() =>
    PRESET_TEMPLATE_KEYS.map((tpl) => ({
      ...tpl,
      label: t(tpl.labelKey),
    })),
  )

  function formatResolution(res) {
    return resolutionLabelMap.value[res] || res
  }

  function recommendedBitrate(resolution) {
    return calcRecommendedBitrate(resolution)
  }

  return {
    resolutionLabels: resolutionLabelMap,
    segmentQuickOptions,
    bitrateQuickOptions,
    fpsQuickOptions,
    presetTemplates,
    formatResolution,
    recommendedBitrate,
  }
}

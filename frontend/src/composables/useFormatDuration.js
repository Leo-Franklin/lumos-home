// src/composables/useFormatDuration.js
import { useI18n } from 'vue-i18n'

export function useFormatDuration() {
  const { t } = useI18n()

  function formatDuration(seconds) {
    if (!seconds) return `0 ${t('common.minute')}`
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h} ${t('common.hour')} ${m} ${t('common.minute')}`
    return `${m} ${t('common.minute')}`
  }

  return { formatDuration }
}

import { describe, it, expect, vi } from 'vitest'
import { useFormatDuration } from '@/composables/useFormatDuration'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key) => {
      const translations = {
        'common.minute': '分钟',
        'common.hour': '小时',
      }
      return translations[key] || key
    },
  }),
}))

describe('useFormatDuration', () => {
  const { formatDuration, formatDurationLong } = useFormatDuration()

  it('returns "0 分钟" for 0 seconds', () => {
    expect(formatDuration(0)).toBe('0 分钟')
  })

  it('returns "0 分钟" for null/undefined', () => {
    expect(formatDuration(null)).toBe('0 分钟')
    expect(formatDuration(undefined)).toBe('0 分钟')
  })

  it('returns minutes only for less than an hour', () => {
    expect(formatDuration(30)).toBe('0 分钟')
    expect(formatDuration(60)).toBe('1 分钟')
    expect(formatDuration(120)).toBe('2 分钟')
    expect(formatDuration(3599)).toBe('59 分钟')
  })

  it('returns hours and minutes for more than an hour', () => {
    expect(formatDuration(3600)).toBe('1 小时 0 分钟')
    expect(formatDuration(3660)).toBe('1 小时 1 分钟')
    expect(formatDuration(7200)).toBe('2 小时 0 分钟')
    expect(formatDuration(7261)).toBe('2 小时 1 分钟')
  })

  it('formatDurationLong is the same as formatDuration', () => {
    expect(formatDurationLong).toBe(formatDuration)
  })
})

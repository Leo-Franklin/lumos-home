import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import SettingsGo2RtcPanel from '@/components/settings/SettingsGo2RtcPanel.vue'
import en from '@/locales/en/settings.js'

vi.mock('@/api/system', () => ({
  updateGo2RtcSettings: vi.fn(),
}))

vi.mock('@/composables/useApiError', () => ({
  useApiError: () => vi.fn(),
}))

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: { en: { settings: en } },
})

describe('SettingsGo2RtcPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows connected state when enabled and reachable', () => {
    const wrapper = mount(SettingsGo2RtcPanel, {
      props: {
        status: {
          enabled: true,
          connected: true,
          api_url: 'http://127.0.0.1:1984',
          rtsp_url: 'rtsp://127.0.0.1:8554',
          embedded_runner: false,
          has_embedded_binary: false,
          webrtc_candidates: ['stun:8555'],
        },
      },
      global: { plugins: [i18n] },
    })
    expect(wrapper.text()).toContain('Reachable')
    expect(wrapper.text()).toContain('http://127.0.0.1:1984')
  })

  it('shows disabled state when go2rtc is off', () => {
    const wrapper = mount(SettingsGo2RtcPanel, {
      props: {
        status: {
          enabled: false,
          connected: false,
          api_url: 'http://127.0.0.1:1984',
          rtsp_url: 'rtsp://127.0.0.1:8554',
          embedded_runner: false,
          has_embedded_binary: false,
          webrtc_candidates: [],
        },
      },
      global: { plugins: [i18n] },
    })
    expect(wrapper.text()).toContain('Disabled')
  })
})

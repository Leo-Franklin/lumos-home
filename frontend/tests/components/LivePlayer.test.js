import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import LivePlayer from '@/components/LivePlayer.vue'
import zhCameras from '@/locales/zh-CN/cameras.js'
import zhCommon from '@/locales/zh-CN/common.js'

vi.mock('@/api/cameras', () => ({
  getLiveInfo: vi.fn(),
}))

vi.mock('@/lib/Go2RtcPlayer', () => ({
  Go2RtcPlayer: vi.fn().mockImplementation(() => ({
    start: vi.fn(),
    stop: vi.fn(),
  })),
}))

import { getLiveInfo } from '@/api/cameras'
import { Go2RtcPlayer } from '@/lib/Go2RtcPlayer'

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  messages: { 'zh-CN': { cameras: zhCameras, common: zhCommon } },
})

describe('LivePlayer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('token', 'test-token')
  })

  it('uses Go2RtcPlayer when backend returns mse mode', async () => {
    getLiveInfo.mockResolvedValue({
      data: {
        mode: 'mse',
        mse_ws_url: '/api/v1/cameras/AA:BB:CC:DD:EE:01/live/ws',
        mjpeg_url: '/api/v1/cameras/AA:BB:CC:DD:EE:01/stream/mjpeg',
      },
    })

    mount(LivePlayer, {
      props: { mac: 'AA:BB:CC:DD:EE:01' },
      global: { plugins: [i18n] },
    })
    await flushPromises()

    expect(getLiveInfo).toHaveBeenCalledWith('AA:BB:CC:DD:EE:01')
    expect(Go2RtcPlayer).toHaveBeenCalled()
  })

  it('falls back to MJPEG img when backend returns mjpeg_fallback', async () => {
    getLiveInfo.mockResolvedValue({
      data: {
        mode: 'mjpeg_fallback',
        mjpeg_url: '/api/v1/cameras/AA:BB:CC:DD:EE:01/stream/mjpeg',
      },
    })

    const wrapper = mount(LivePlayer, {
      props: { mac: 'AA:BB:CC:DD:EE:01' },
      global: { plugins: [i18n] },
    })
    await flushPromises()

    expect(Go2RtcPlayer).not.toHaveBeenCalled()
    const img = wrapper.find('img.live-player__video')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toContain('stream/mjpeg')
  })
})

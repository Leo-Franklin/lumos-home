import { describe, it, expect } from 'vitest'
import { withStreamToken, wsUrlFromApiPath, pickLiveMode, pickMjpegUrl } from '@/utils/livePlayer'

describe('livePlayer utils', () => {
  it('withStreamToken appends token query param', () => {
    expect(withStreamToken('/api/v1/cameras/X/live/ws', 'abc')).toBe(
      '/api/v1/cameras/X/live/ws?token=abc',
    )
  })

  it('pickLiveMode prefers mse when available', () => {
    expect(
      pickLiveMode({
        mode: 'mse',
        mse_ws_url: '/api/v1/cameras/X/live/ws',
      }),
    ).toBe('mse')
  })

  it('pickLiveMode falls back to mjpeg', () => {
    expect(pickLiveMode({ mode: 'mjpeg_fallback' })).toBe('mjpeg')
    expect(pickLiveMode({ mode: 'mse', mse_ws_url: null })).toBe('mjpeg')
  })

  it('pickMjpegUrl adds token', () => {
    expect(pickMjpegUrl({ mjpeg_url: '/api/v1/cameras/X/stream/mjpeg' }, 'tok')).toBe(
      '/api/v1/cameras/X/stream/mjpeg?token=tok',
    )
  })

  it('wsUrlFromApiPath builds ws URL from API path', () => {
    const url = wsUrlFromApiPath('/api/v1/cameras/X/live/ws', 'tok')
    expect(url).toMatch(/^wss?:\/\//)
    expect(url).toContain('/api/v1/cameras/X/live/ws?token=tok')
  })
})

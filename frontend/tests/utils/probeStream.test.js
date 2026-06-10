import { describe, expect, it } from 'vitest'
import { isStreamSelectable, resolveInitialStreamIndex } from '@/utils/probeStream'

const profiles = [
  { index: 0, name: 'mainStream', rtsp_url: 'rtsp://cam/main' },
  { index: 1, name: 'minorStream', rtsp_url: 'rtsp://cam/sub' },
]

describe('resolveInitialStreamIndex', () => {
  it('prefers currently saved rtsp url', () => {
    expect(
      resolveInitialStreamIndex(profiles, {
        currentRtspUrl: 'rtsp://cam/sub',
        autoSetRtspUrl: 'rtsp://cam/main',
      }),
    ).toBe(1)
  })

  it('falls back to auto detected url', () => {
    expect(resolveInitialStreamIndex(profiles, { autoSetRtspUrl: 'rtsp://cam/main' })).toBe(0)
  })

  it('falls back to first profile with rtsp url', () => {
    const partial = [
      { index: 0, name: 'mainStream', rtsp_url: null },
      { index: 1, name: 'minorStream', rtsp_url: 'rtsp://cam/sub' },
    ]
    expect(resolveInitialStreamIndex(partial, {})).toBe(1)
  })

  it('returns null when profiles are empty', () => {
    expect(resolveInitialStreamIndex([], {})).toBeNull()
  })
})

describe('isStreamSelectable', () => {
  it('returns true only when rtsp url exists', () => {
    expect(isStreamSelectable(profiles[0])).toBe(true)
    expect(isStreamSelectable({ index: 2, name: 'x', rtsp_url: null })).toBe(false)
  })
})

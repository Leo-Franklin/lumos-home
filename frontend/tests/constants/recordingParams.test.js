import { describe, it, expect } from 'vitest'
import {
  recommendedBitrate,
  normalizeOverrides,
  buildOverridesPayload,
  emptyOverrides,
} from '@/constants/recordingParams'

describe('recordingParams', () => {
  it('recommendedBitrate scales with resolution width', () => {
    expect(recommendedBitrate('1920x1080')).toBe(2048)
    expect(recommendedBitrate('1280x720')).toBe(1024)
    expect(recommendedBitrate('640x360')).toBe(512)
  })

  it('normalizeOverrides maps legacy frame_rate to fps', () => {
    expect(normalizeOverrides({ frame_rate: 30, bitrate: 1024 })).toMatchObject({
      fps: 30,
      bitrate: 1024,
    })
    expect(normalizeOverrides({ frame_rate: 30 }).frame_rate).toBeUndefined()
  })

  it('buildOverridesPayload uses segment_seconds for camera API', () => {
    const payload = buildOverridesPayload(
      { ...emptyOverrides(), segment_duration: 300, fps: 25 },
      { target: 'camera' },
    )
    expect(payload).toEqual({ segment_seconds: 300, fps: 25 })
  })

  it('buildOverridesPayload uses segment_duration for schedule storage', () => {
    const payload = buildOverridesPayload(
      { ...emptyOverrides(), segment_duration: 600 },
      { target: 'schedule' },
    )
    expect(payload).toEqual({ segment_duration: 600 })
  })
})

/** Shared recording parameter constants (resolution, segment, bitrate, fps). */

export const RESOLUTIONS = ['1920x1080', '1280x720', '640x360']

export const SEGMENT_QUICK_VALUES = [60, 300, 600, 1800]

export const BITRATE_QUICK_VALUES = [512, 1024, 2048, 4096, 8192]

export const FPS_QUICK_VALUES = [15, 25, 30]

export const PRESET_TEMPLATE_KEYS = [
  {
    key: 'highQuality',
    labelKey: 'recording.tplHighQuality',
    resolution: '1920x1080',
    segment_duration: 600,
    bitrate: 4096,
    fps: 25,
  },
  {
    key: 'standard',
    labelKey: 'recording.tplStandard',
    resolution: '1280x720',
    segment_duration: 300,
    bitrate: 2048,
    fps: 25,
  },
  {
    key: 'compact',
    labelKey: 'recording.tplCompact',
    resolution: '640x360',
    segment_duration: 300,
    bitrate: 1024,
    fps: 15,
  },
]

export const SEGMENT_MIN = 60
export const SEGMENT_MAX = 3600
export const BITRATE_MIN = 256
export const BITRATE_MAX = 20000
export const BITRATE_STEP = 256
export const FPS_MIN = 5
export const FPS_MAX = 60

export function recommendedBitrate(resolution) {
  const w = parseInt(String(resolution || '1920x1080').split('x')[0], 10)
  if (w >= 1920) return 2048
  if (w >= 1280) return 1024
  return 512
}

export function emptyOverrides() {
  return {
    segment_duration: null,
    bitrate: null,
    fps: null,
    resolution: null,
  }
}

export function emptyPresetForm() {
  return {
    name: '',
    resolution: '1920x1080',
    segment_duration: 300,
    bitrate: 4096,
    fps: 25,
  }
}

/** Normalize legacy schedule override keys (frame_rate → fps). */
export function normalizeOverrides(raw) {
  if (!raw || typeof raw !== 'object') return emptyOverrides()
  const o = { ...emptyOverrides(), ...raw }
  if (o.frame_rate != null && o.fps == null) {
    o.fps = o.frame_rate
  }
  delete o.frame_rate
  return o
}

/**
 * Build API overrides payload. Camera start-recording uses segment_seconds;
 * schedule storage uses segment_duration.
 */
export function buildOverridesPayload(overrides, { target = 'camera' } = {}) {
  const out = {}
  if (!overrides) return out
  if (overrides.segment_duration != null && overrides.segment_duration !== '') {
    out[target === 'schedule' ? 'segment_duration' : 'segment_seconds'] = overrides.segment_duration
  }
  if (overrides.bitrate != null && overrides.bitrate !== '') out.bitrate = overrides.bitrate
  if (overrides.fps != null && overrides.fps !== '') out.fps = overrides.fps
  if (overrides.resolution) out.resolution = overrides.resolution
  return out
}

/** Compact one-line summary for preset cards / list rows. */
export function formatPresetSummary(preset, formatResolution) {
  const res = formatResolution ? formatResolution(preset.resolution) : preset.resolution
  return `${res} · ${preset.segment_duration}s · ${preset.bitrate} kbps · ${preset.fps} fps`
}

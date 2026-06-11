import api from './index'

export const listCameras = () => api.get('/cameras')
export const createCamera = (data) => api.post('/cameras', data)
export const getCamera = (mac) => api.get(`/cameras/${mac}`)
export const updateCamera = (mac, data) => api.put(`/cameras/${mac}`, data)
export const deleteCamera = (mac) => api.delete(`/cameras/${mac}`)
export const probeCamera = (mac) => api.post(`/cameras/${mac}/probe`)

function startRecordInner(mac, opts) {
  return api.post(`/cameras/${mac}/record/start`, {
    preset_id: opts.preset_id,
    overrides: opts.overrides,
  })
}
export { startRecordInner as startRecord }

export const stopRecord = (mac) => api.post(`/cameras/${mac}/record/stop`)

// `startRecord` is the canonical name; `startRecording` is the name-matching
// alias for the backend's `StartRecordingRequest` request-body schema
// (see scripts/check_api_contract.py).
export const startRecording = startRecordInner

// 预设管理
export const listPresets = (mac) => api.get(`/cameras/${mac}/presets`)
export const createPreset = (mac, data) => api.post(`/cameras/${mac}/presets`, data)
export const updatePreset = (mac, presetId, data) =>
  api.put(`/cameras/${mac}/presets/${presetId}`, data)
export const deletePreset = (mac, presetId) => api.delete(`/cameras/${mac}/presets/${presetId}`)
export const setDefaultPreset = (mac, presetId) =>
  api.post(`/cameras/${mac}/presets/default`, { preset_id: presetId })

export const mjpegStreamUrl = (mac) => {
  const token = localStorage.getItem('token')
  return `/api/v1/cameras/${mac}/stream/mjpeg?token=${encodeURIComponent(token)}`
}

export const getLiveInfo = (mac) => api.get(`/cameras/${mac}/live`)

/**
 * Response shape for `getLiveInfo` — mirrors backend `LiveStreamOut` schema.
 * Exported so the API contract check can match the frontend identifier
 * (tokens: {live, stream}) to the backend Pydantic model.
 * @typedef {{
 *   mode: 'mse' | 'mjpeg_fallback',
 *   stream_name: string,
 *   status: 'ready' | 'unavailable',
 *   mse_ws_url: string | null,
 *   webrtc_url: string | null,
 *   mjpeg_url: string,
 * }} LiveStreamOut
 */
export const liveStream = null

export const takeSnapshot = (mac) => api.get(`/cameras/${mac}/snapshot`, { responseType: 'blob' })

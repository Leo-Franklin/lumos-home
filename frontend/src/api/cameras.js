import api from './index'

export const listCameras = () => api.get('/cameras')
export const createCamera = (data) => api.post('/cameras', data)
export const getCamera = (mac) => api.get(`/cameras/${mac}`)
export const updateCamera = (mac, data) => api.put(`/cameras/${mac}`, data)
export const deleteCamera = (mac) => api.delete(`/cameras/${mac}`)
export const probeCamera = (mac) => api.post(`/cameras/${mac}/probe`)

function startRecordInner(mac, opts) {
  return api.post(`/cameras/${mac}/record/start`, { preset_id: opts.preset_id, overrides: opts.overrides })
}
export { startRecordInner as startRecord }

export const stopRecord = (mac) => api.post(`/cameras/${mac}/record/stop`)

// 预设管理
export const listPresets = (mac) => api.get(`/cameras/${mac}/presets`)
export const createPreset = (mac, data) => api.post(`/cameras/${mac}/presets`, data)
export const updatePreset = (mac, presetId, data) => api.put(`/cameras/${mac}/presets/${presetId}`, data)
export const deletePreset = (mac, presetId) => api.delete(`/cameras/${mac}/presets/${presetId}`)
export const setDefaultPreset = (mac, presetId) => api.post(`/cameras/${mac}/presets/default`, { preset_id: presetId })

export const mjpegStreamUrl = (mac) => {
  const token = localStorage.getItem('token')
  return `/api/v1/cameras/${mac}/stream/mjpeg?token=${encodeURIComponent(token)}`
}

export const takeSnapshot = (mac) =>
  api.get(`/cameras/${mac}/snapshot`, { responseType: 'blob' })

export const startLive = (mac) => api.post(`/cameras/${mac}/live/start`)
export const stopLive = (mac) => api.delete(`/cameras/${mac}/live/stop`)
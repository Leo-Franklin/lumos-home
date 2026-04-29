import api from './index'

export const listCameras = () => api.get('/cameras')
export const createCamera = (data) => api.post('/cameras', data)
export const getCamera = (mac) => api.get(`/cameras/${mac}`)
export const updateCamera = (mac, data) => api.put(`/cameras/${mac}`, data)
export const deleteCamera = (mac) => api.delete(`/cameras/${mac}`)
export const probeCamera = (mac) => api.post(`/cameras/${mac}/probe`)
export const startRecord = (mac) => api.post(`/cameras/${mac}/record/start`)
export const stopRecord = (mac) => api.post(`/cameras/${mac}/record/stop`)

export const mjpegStreamUrl = (mac) => {
  const token = localStorage.getItem('token')
  return `/api/v1/cameras/${mac}/stream/mjpeg?token=${encodeURIComponent(token)}`
}

export const takeSnapshot = (mac) =>
  api.get(`/cameras/${mac}/snapshot`, { responseType: 'blob' })

export const startLive = (mac) => api.post(`/cameras/${mac}/live/start`)
export const stopLive = (mac) => api.delete(`/cameras/${mac}/live/stop`)
export const hlsLiveUrl = (mac) => `/hls/${mac}/index.m3u8`

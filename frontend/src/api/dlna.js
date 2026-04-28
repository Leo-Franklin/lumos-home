import api from './index'

export const discoverDLNA = () => api.post('/dlna/discover')
export const listDLNADevices = () => api.get('/dlna')
export const castURL = (data) => api.post('/dlna/cast', data)
export const castFile = (formData) => api.post('/dlna/cast/file', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 120000,
})
export const playDevice = (deviceId) => api.post(`/dlna/${deviceId}/play`)
export const pauseDevice = (deviceId) => api.post(`/dlna/${deviceId}/pause`)
export const stopDevice = (deviceId) => api.post(`/dlna/${deviceId}/stop`)
export const getDeviceStatus = (deviceId) => api.get(`/dlna/${deviceId}/status`)

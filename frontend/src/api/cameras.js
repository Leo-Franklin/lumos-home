import api from './index'

export const listCameras = () => api.get('/cameras')
export const createCamera = (data) => api.post('/cameras', data)
export const getCamera = (mac) => api.get(`/cameras/${mac}`)
export const updateCamera = (mac, data) => api.put(`/cameras/${mac}`, data)
export const deleteCamera = (mac) => api.delete(`/cameras/${mac}`)
export const probeCamera = (mac) => api.post(`/cameras/${mac}/probe`)
export const startRecord = (mac) => api.post(`/cameras/${mac}/record/start`)
export const stopRecord = (mac) => api.post(`/cameras/${mac}/record/stop`)

import api from './index'

export const createCamera = (data) => api.post('/cameras', data)
export const getCamera = (mac) => api.get(`/cameras/${mac}`)
export const listCameras = () => api.get('/cameras')

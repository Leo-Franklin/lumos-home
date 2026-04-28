import api from './index'

export const listDevices = (params) => api.get('/devices', { params })
export const triggerScan = () => api.post('/devices/scan')
export const getDevice = (mac) => api.get(`/devices/${mac}`)
export const updateDevice = (mac, data) => api.patch(`/devices/${mac}`, data)
export const deleteDevice = (mac) => api.delete(`/devices/${mac}`)
export const getTopology = () => api.get('/devices/topology')

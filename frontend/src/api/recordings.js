import api from './index'

export const listRecordings = (params) => api.get('/recordings', { params })
export const getRecording = (id) => api.get(`/recordings/${id}`)
export const deleteRecording = (id) => api.delete(`/recordings/${id}`)
export const streamUrl = (id) => `/api/v1/recordings/${id}/stream`
export const downloadUrl = (id) => `/api/v1/recordings/${id}/download`

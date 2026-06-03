import api from './index'

export const listRecordings = (params) => api.get('/recordings', { params })
export const getRecording = (id) => api.get(`/recordings/${id}`)
export const deleteRecording = (id) => api.delete(`/recordings/${id}`)
export const streamUrl = (id) => {
  const token = localStorage.getItem('token')
  return `/api/v1/recordings/${id}/stream?token=${encodeURIComponent(token || '')}`
}
export const downloadUrl = (id) => `/api/v1/recordings/${id}/download`

export const getRecordingStats = (params) => api.get('/recordings/stats', { params })
export const openRecordingFolder = (id) => api.post(`/recordings/${id}/open-folder`)

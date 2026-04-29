import api from './index'

export const listRecordings = (params) => api.get('/recordings', { params })
export const getRecording = (id) => api.get(`/recordings/${id}`)
export const deleteRecording = (id) => api.delete(`/recordings/${id}`)
export const streamUrl = (id) => `/api/v1/recordings/${id}/stream`
export const downloadUrl = (id) => `/api/v1/recordings/${id}/download`

export const requestRecordingHls = (id) => api.get(`/recordings/${id}/hls/index.m3u8`)
export const recordingHlsUrl = (id) => {
  const token = localStorage.getItem('token')
  return `/api/v1/recordings/${id}/hls/index.m3u8?token=${encodeURIComponent(token)}`
}

export const getRecordingStats = (params) => api.get('/recordings/stats', { params })

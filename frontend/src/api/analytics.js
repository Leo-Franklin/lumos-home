import api from './index'

export const getOnlineTrend     = (params) => api.get('/analytics/online-trend',        { params })
export const getDeviceTypeStats = ()        => api.get('/analytics/device-type-stats')
export const getResponseTime    = ()        => api.get('/analytics/response-time')
export const getRecordingCalendar = (params) => api.get('/analytics/recording-calendar', { params })
export const getNewDevices      = (params) => api.get('/analytics/new-devices',          { params })
export const getDeviceStability = (params) => api.get('/analytics/device-stability',     { params })
export const getTypeActivity    = (params) => api.get('/analytics/type-activity',        { params })

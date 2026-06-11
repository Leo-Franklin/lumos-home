import api from './index'

export const getDashboard = () => api.get('/dashboard')

export const getGo2RtcStatus = () => api.get('/go2rtc')

export const updateGo2RtcSettings = (body) => api.put('/go2rtc', body)

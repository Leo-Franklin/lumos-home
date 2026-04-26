import api from './index'

export const listSchedules = () => api.get('/schedules')
export const createSchedule = (data) => api.post('/schedules', data)
export const updateSchedule = (id, data) => api.patch(`/schedules/${id}`, data)
export const deleteSchedule = (id) => api.delete(`/schedules/${id}`)

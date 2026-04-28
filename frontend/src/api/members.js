import api from './index'

export const listMembers = () => api.get('/members')
export const createMember = (data) => api.post('/members', data)
export const updateMember = (id, data) => api.patch(`/members/${id}`, data)
export const deleteMember = (id) => api.delete(`/members/${id}`)

export const listMemberDevices = (id) => api.get(`/members/${id}/devices`)
export const bindDevice = (id, data) => api.post(`/members/${id}/devices`, data)
export const unbindDevice = (id, mac) => api.delete(`/members/${id}/devices/${mac}`)

export const listPresenceLogs = (id, params) => api.get(`/members/${id}/logs`, { params })

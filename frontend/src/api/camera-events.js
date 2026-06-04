import api from './index'

// Camera events — unified timeline entries shared by the timeline UI,
// retention policy, and Frigate bridge. See backend/app/api/camera_events.py.
export const listCameraEvents = (params) => api.get('/camera-events', { params })
export const getCameraEvent = (id) => api.get(`/camera-events/${id}`)
export const patchCameraEvent = (id, data) => api.patch(`/camera-events/${id}`, data)
export const deleteCameraEvent = (id) => api.delete(`/camera-events/${id}`)

import api from './index'

// User profile — currently just language. See backend/app/api/user.py.
// (stores/locale.js was calling these endpoints via the raw `api` instance;
// this module is the contract-canonical export so the contract check
// recognises the user-profile schema pair.)
export const getUserProfile = () => api.get('/user/profile')
export const updateUserProfile = (data) => api.put('/user/profile', data)

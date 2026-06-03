import api from './index'

export async function login(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  return data
}

export async function register(email, password) {
  await api.post('/auth/register', { email, password })
}

export async function changePassword(currentPassword, newPassword) {
  await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export async function forgotPassword(email) {
  await api.post('/auth/forgot-password', { email })
}

export async function resetPassword(token, newPassword) {
  await api.post('/auth/reset-password', { token, new_password: newPassword })
}

export async function verifyEmail(token) {
  await api.get('/auth/verify-email', { params: { token } })
}

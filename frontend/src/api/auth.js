import api from './index'

export async function login(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  return data
}

export async function register(email, password) {
  await api.post('/auth/register', { email, password })
}

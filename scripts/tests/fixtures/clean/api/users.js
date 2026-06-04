import axios from 'axios'

export async function createUser(payload) {
  return axios.post('/api/users', payload)
}

export async function getUser(id) {
  return axios.get(`/api/users/${id}`)
}

export const userCreate = { email: '', password: '' }

export const userRead = { id: 0, email: '', is_active: true }

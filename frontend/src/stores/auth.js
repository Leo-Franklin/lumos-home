import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/index'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')

  async function login(user, pass) {
    const params = new URLSearchParams()
    params.append('username', user)
    params.append('password', pass)
    const { data } = await api.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    token.value = data.access_token
    username.value = user
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('username', user)
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
  }

  return { token, username, login, logout }
})

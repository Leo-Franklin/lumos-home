import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/index'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')

  async function login(email, pass) {
    const { data } = await api.post('/auth/login', {
      email: email,
      password: pass,
    })
    token.value = data.access_token
    username.value = email
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('username', email)
  }

  async function register(email, pass) {
    await api.post('/auth/register', {
      email: email,
      password: pass,
    })
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
  }

  return { token, username, login, logout, register }
})

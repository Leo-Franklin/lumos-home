import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('LoginView - Auth Store Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('auth store has required properties and methods', () => {
    const store = useAuthStore()
    expect(store).toHaveProperty('token')
    expect(store).toHaveProperty('username')
    expect(store).toHaveProperty('login')
    expect(store).toHaveProperty('logout')
    expect(store).toHaveProperty('register')
  })

  it('login stores token and username in localStorage', async () => {
    api.post.mockResolvedValue({ data: { access_token: 'token123' } })
    const store = useAuthStore()
    await store.login('test@example.com', 'password')
    expect(localStorage.getItem('token')).toBe('token123')
    expect(localStorage.getItem('username')).toBe('test@example.com')
  })

  it('logout clears localStorage', async () => {
    api.post.mockResolvedValue({ data: { access_token: 'token' } })
    const store = useAuthStore()
    await store.login('test@example.com', 'password')
    store.logout()
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('username')).toBeNull()
  })
})

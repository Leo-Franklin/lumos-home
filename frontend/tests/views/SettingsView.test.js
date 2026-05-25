import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

describe('SettingsView - Auth Store Integration', () => {
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

  it('token is empty by default', () => {
    const store = useAuthStore()
    expect(store.token).toBe('')
  })

  it('login sets access token', async () => {
    api.post.mockResolvedValue({ data: { access_token: 'token123' } })
    const store = useAuthStore()
    await store.login('test@example.com', 'password')
    expect(store.token).toBe('token123')
  })

  it('logout clears token', async () => {
    api.post.mockResolvedValue({ data: { access_token: 'token' } })
    const store = useAuthStore()
    await store.login('test@example.com', 'password')
    store.logout()
    expect(store.token).toBe('')
  })
})

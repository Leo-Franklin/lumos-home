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

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useAuthStore()
    expect(store).toHaveProperty('token')
    expect(store).toHaveProperty('username')
    expect(store).toHaveProperty('login')
    expect(store).toHaveProperty('logout')
    expect(store).toHaveProperty('register')
  })

  it('login sets token and username', async () => {
    const mockResponse = { data: { access_token: 'test-token-123' } }
    api.post.mockResolvedValue(mockResponse)
    const store = useAuthStore()
    await store.login('test@example.com', 'password')
    expect(store.token).toBe('test-token-123')
    expect(store.username).toBe('test@example.com')
    expect(localStorage.getItem('token')).toBe('test-token-123')
    expect(localStorage.getItem('username')).toBe('test@example.com')
  })

  it('login calls API with correct params', async () => {
    api.post.mockResolvedValue({ data: { access_token: 'token' } })
    const store = useAuthStore()
    await store.login('user@test.com', 'secret')
    expect(api.post).toHaveBeenCalledWith('/auth/login', {
      email: 'user@test.com',
      password: 'secret',
    })
  })

  it('logout clears token and username', async () => {
    api.post.mockResolvedValue({ data: { access_token: 'token' } })
    const store = useAuthStore()
    await store.login('test@example.com', 'password')
    store.logout()
    expect(store.token).toBe('')
    expect(store.username).toBe('')
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('username')).toBeNull()
  })

  it('register calls API with correct params', async () => {
    api.post.mockResolvedValue({})
    const store = useAuthStore()
    await store.register('newuser@test.com', 'newpass')
    expect(api.post).toHaveBeenCalledWith('/auth/register', {
      email: 'newuser@test.com',
      password: 'newpass',
    })
  })
})

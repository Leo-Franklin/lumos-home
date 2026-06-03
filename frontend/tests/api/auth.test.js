import { describe, it, expect, vi, beforeEach } from 'vitest'
import { login, register, changePassword } from '@/api/auth'

const mockPost = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: mockPost,
      get: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('login sends POST /auth/login with email and password', async () => {
    const mockResponse = { data: { token: 'test-token' } }
    mockPost.mockResolvedValue(mockResponse)

    const result = await login('test@example.com', 'password123')

    expect(mockPost).toHaveBeenCalledWith('/auth/login', {
      email: 'test@example.com',
      password: 'password123',
    })
    expect(result).toEqual(mockResponse.data)
  })

  it('register sends POST /auth/register with email and password', async () => {
    mockPost.mockResolvedValue({})

    await register('test@example.com', 'password123')

    expect(mockPost).toHaveBeenCalledWith('/auth/register', {
      email: 'test@example.com',
      password: 'password123',
    })
  })

  it('changePassword sends POST /auth/change-password with current_password and new_password', async () => {
    mockPost.mockResolvedValue({})

    await changePassword('OldPass123!', 'NewPass456!')

    expect(mockPost).toHaveBeenCalledWith('/auth/change-password', {
      current_password: 'OldPass123!',
      new_password: 'NewPass456!',
    })
  })
})

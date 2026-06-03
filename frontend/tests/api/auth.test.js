import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  login, register, changePassword, forgotPassword, resetPassword, verifyEmail,
} from '@/api/auth'

const mockPost = vi.hoisted(() => vi.fn())
const mockGet = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: mockPost,
      get: mockGet,
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

  it('forgotPassword sends POST /auth/forgot-password with email', async () => {
    mockPost.mockResolvedValue({})

    await forgotPassword('user@example.com')

    expect(mockPost).toHaveBeenCalledWith('/auth/forgot-password', { email: 'user@example.com' })
  })

  it('resetPassword sends POST /auth/reset-password with token and new_password', async () => {
    mockPost.mockResolvedValue({})

    await resetPassword('abc-token', 'NewPass456!')

    expect(mockPost).toHaveBeenCalledWith('/auth/reset-password', {
      token: 'abc-token',
      new_password: 'NewPass456!',
    })
  })

  it('verifyEmail sends GET /auth/verify-email with token query param', async () => {
    mockGet.mockResolvedValue({})

    await verifyEmail('abc-token')

    expect(mockGet).toHaveBeenCalledWith('/auth/verify-email', { params: { token: 'abc-token' } })
  })
})

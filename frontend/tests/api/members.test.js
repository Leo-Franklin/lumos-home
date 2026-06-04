import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listMembers,
  createMember,
  updateMember,
  deleteMember,
  listMemberDevices,
  bindDevice,
  unbindDevice,
  listPresenceLogs,
  getMemberStats,
} from '@/api/members'

const mockGet = vi.hoisted(() => vi.fn())
const mockPost = vi.hoisted(() => vi.fn())
const mockPatch = vi.hoisted(() => vi.fn())
const mockDelete = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      patch: mockPatch,
      delete: mockDelete,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('members API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listMembers sends GET /members', async () => {
    const mockResponse = { data: [{ id: 1, name: 'John' }] }
    mockGet.mockResolvedValue(mockResponse)

    const result = await listMembers()

    expect(mockGet).toHaveBeenCalledWith('/members')
    expect(result).toEqual(mockResponse)
  })

  it('createMember sends POST /members', async () => {
    const data = { name: 'John', email: 'john@example.com' }
    const mockResponse = { data: { id: 1, ...data } }
    mockPost.mockResolvedValue(mockResponse)

    const result = await createMember(data)

    expect(mockPost).toHaveBeenCalledWith('/members', data)
    expect(result).toEqual(mockResponse)
  })

  it('updateMember sends PATCH /members/:id', async () => {
    const id = 1
    const data = { name: 'John Updated' }
    const mockResponse = { data: { id, ...data } }
    mockPatch.mockResolvedValue(mockResponse)

    const result = await updateMember(id, data)

    expect(mockPatch).toHaveBeenCalledWith(`/members/${id}`, data)
    expect(result).toEqual(mockResponse)
  })

  it('deleteMember sends DELETE /members/:id', async () => {
    const id = 1
    mockDelete.mockResolvedValue({ data: { success: true } })

    await deleteMember(id)

    expect(mockDelete).toHaveBeenCalledWith(`/members/${id}`)
  })

  it('listMemberDevices sends GET /members/:id/devices', async () => {
    const id = 1
    const mockResponse = { data: [{ mac: '00:11:22:33:44:55' }] }
    mockGet.mockResolvedValue(mockResponse)

    const result = await listMemberDevices(id)

    expect(mockGet).toHaveBeenCalledWith(`/members/${id}/devices`)
    expect(result).toEqual(mockResponse)
  })

  it('bindDevice sends POST /members/:id/devices', async () => {
    const id = 1
    const data = { mac: '00:11:22:33:44:55' }
    const mockResponse = { data: { success: true } }
    mockPost.mockResolvedValue(mockResponse)

    const result = await bindDevice(id, data)

    expect(mockPost).toHaveBeenCalledWith(`/members/${id}/devices`, data)
    expect(result).toEqual(mockResponse)
  })

  it('unbindDevice sends DELETE /members/:id/devices/:mac', async () => {
    const id = 1
    const mac = '00:11:22:33:44:55'
    mockDelete.mockResolvedValue({ data: { success: true } })

    await unbindDevice(id, mac)

    expect(mockDelete).toHaveBeenCalledWith(`/members/${id}/devices/${mac}`)
  })

  it('listPresenceLogs sends GET /members/:id/logs with params', async () => {
    const id = 1
    const params = { start: '2024-01-01', end: '2024-01-31' }
    const mockResponse = { data: [{ timestamp: '2024-01-15' }] }
    mockGet.mockResolvedValue(mockResponse)

    const result = await listPresenceLogs(id, params)

    expect(mockGet).toHaveBeenCalledWith(`/members/${id}/logs`, { params })
    expect(result).toEqual(mockResponse)
  })

  it('getMemberStats sends GET /members/:id/stats with params', async () => {
    const id = 1
    const params = { period: 'weekly' }
    const mockResponse = { data: { count: 42 } }
    mockGet.mockResolvedValue(mockResponse)

    const result = await getMemberStats(id, params)

    expect(mockGet).toHaveBeenCalledWith(`/members/${id}/stats`, { params })
    expect(result).toEqual(mockResponse)
  })
})

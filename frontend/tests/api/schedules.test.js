import { describe, it, expect, vi, beforeEach } from 'vitest'
import { listSchedules, createSchedule, updateSchedule, deleteSchedule } from '@/api/schedules'

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

describe('schedules API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listSchedules sends GET /schedules', async () => {
    const mockResponse = { data: [] }
    mockGet.mockResolvedValue(mockResponse)

    const result = await listSchedules()

    expect(mockGet).toHaveBeenCalledWith('/schedules')
    expect(result).toEqual(mockResponse)
  })

  it('createSchedule sends POST /schedules', async () => {
    const scheduleData = { name: 'Test Schedule', camera_id: 1 }
    const mockResponse = { data: { id: 1, ...scheduleData } }
    mockPost.mockResolvedValue(mockResponse)

    const result = await createSchedule(scheduleData)

    expect(mockPost).toHaveBeenCalledWith('/schedules', scheduleData)
    expect(result).toEqual(mockResponse)
  })

  it('updateSchedule sends PATCH /schedules/:id', async () => {
    const scheduleData = { name: 'Updated Schedule' }
    const mockResponse = { data: { id: 1, ...scheduleData } }
    mockPatch.mockResolvedValue(mockResponse)

    const result = await updateSchedule(1, scheduleData)

    expect(mockPatch).toHaveBeenCalledWith('/schedules/1', scheduleData)
    expect(result).toEqual(mockResponse)
  })

  it('deleteSchedule sends DELETE /schedules/:id', async () => {
    mockDelete.mockResolvedValue({ data: null })

    await deleteSchedule(1)

    expect(mockDelete).toHaveBeenCalledWith('/schedules/1')
  })
})

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMembersStore } from '@/stores/members'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: { get: vi.fn() },
}))

describe('useMembersStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useMembersStore()
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('fetchMembers sets items', async () => {
    const mockMembers = [
      { id: 1, name: 'Alice', is_home: false },
      { id: 2, name: 'Bob', is_home: true },
    ]
    api.get.mockResolvedValue({ data: mockMembers })

    const store = useMembersStore()
    await store.fetchMembers()

    expect(store.items).toEqual(mockMembers)
    expect(api.get).toHaveBeenCalledWith('/members')
  })

  it('fetchMembers sets loading true while fetching', async () => {
    let loadingDuringFetch = null
    api.get.mockImplementation(() => {
      loadingDuringFetch = useMembersStore().loading
      return Promise.resolve({ data: [] })
    })

    const store = useMembersStore()
    const fetchPromise = store.fetchMembers()

    expect(store.loading).toBe(true)
    expect(loadingDuringFetch).toBe(true)

    await fetchPromise
    expect(store.loading).toBe(false)
  })

  it('onPresenceEvent with member_arrived sets is_home true and last_arrived_at', () => {
    const store = useMembersStore()
    store.items = [
      { id: 1, name: 'Alice', is_home: false, last_arrived_at: null, last_left_at: null },
    ]

    store.onPresenceEvent(1, 'member_arrived')

    expect(store.items[0].is_home).toBe(true)
    expect(store.items[0].last_arrived_at).toBeTruthy()
    expect(store.items[0].last_arrived_at).not.toBeNull()
  })

  it('onPresenceEvent with member_left sets is_home false and last_left_at', () => {
    const store = useMembersStore()
    store.items = [
      { id: 1, name: 'Alice', is_home: true, last_arrived_at: null, last_left_at: null },
    ]

    store.onPresenceEvent(1, 'member_left')

    expect(store.items[0].is_home).toBe(false)
    expect(store.items[0].last_left_at).toBeTruthy()
    expect(store.items[0].last_left_at).not.toBeNull()
  })

  it('onPresenceEvent does nothing if member not found', () => {
    const store = useMembersStore()
    store.items = [
      { id: 1, name: 'Alice', is_home: false },
    ]

    store.onPresenceEvent(999, 'member_arrived')

    expect(store.items[0].is_home).toBe(false)
    expect(store.items[0].last_arrived_at).toBeUndefined()
  })
})

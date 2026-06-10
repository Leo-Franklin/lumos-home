import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, watch } from 'vue'

/** Mirrors DevicesView route ↔ store sync. */
function applyRouteMacFilter(mac, { store, searchInput }) {
  const q = mac ? String(mac) : ''
  searchInput.value = q
  if (q) {
    if (store.search === q) return
    store.search = q
    store.page = 1
    store.fetchDevices()
    return
  }
  if (store.search) {
    store.clearSearch()
    return
  }
  if (!store.items.length) {
    store.fetchDevices()
  }
}

describe('DevicesView route mac filter sync', () => {
  let store
  let searchInput
  let routeMac

  beforeEach(() => {
    routeMac = ref(undefined)
    searchInput = ref('')
    store = {
      search: '',
      page: 1,
      items: [],
      fetchDevices: vi.fn(),
      clearSearch: vi.fn(function () {
        this.search = ''
        this.page = 1
        this.fetchDevices()
      }),
    }
    watch(routeMac, (mac) => applyRouteMacFilter(mac, { store, searchInput }), { immediate: true })
  })

  it('applies mac filter when route query is set', () => {
    routeMac.value = 'aa:bb:cc:dd:ee:ff'
    expect(searchInput.value).toBe('aa:bb:cc:dd:ee:ff')
    expect(store.search).toBe('aa:bb:cc:dd:ee:ff')
    expect(store.fetchDevices).toHaveBeenCalled()
  })

  it('clears stale store search when route query is removed (browser back)', () => {
    routeMac.value = 'aa:bb:cc:dd:ee:ff'
    vi.clearAllMocks()

    routeMac.value = undefined

    expect(store.clearSearch).toHaveBeenCalled()
    expect(searchInput.value).toBe('')
  })
})

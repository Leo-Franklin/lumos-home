import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLocaleStore } from '@/stores/locale'
import api from '@/api/index'

vi.mock('@/locales', () => ({
  default: { global: { locale: { value: 'zh-CN' } } },
}))

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

describe('useLocaleStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('has correct initial state from localStorage', () => {
    localStorage.setItem('app-locale', 'en')
    const store = useLocaleStore()
    expect(store.locale).toBe('en')
  })

  it('defaults to zh-CN if no localStorage value', () => {
    const store = useLocaleStore()
    expect(store.locale).toBe('zh-CN')
  })

  it('setLocale updates locale and localStorage', () => {
    const store = useLocaleStore()
    store.setLocale('en')
    expect(store.locale).toBe('en')
    expect(localStorage.getItem('app-locale')).toBe('en')
  })

  it('setLocale calls API to update profile', async () => {
    const store = useLocaleStore()
    await store.setLocale('en')
    expect(api.put).toHaveBeenCalledWith('/user/profile', { language: 'en' })
  })

  it('setLocale does not throw if API fails', () => {
    api.put.mockRejectedValue(new Error('API error'))
    const store = useLocaleStore()
    expect(() => store.setLocale('en')).not.toThrow()
  })

  it('initLocale syncs locale from server', async () => {
    api.get.mockResolvedValue({ data: { language: 'en' } })
    const store = useLocaleStore()
    await store.initLocale()
    expect(store.locale).toBe('en')
  })

  it('initLocale does nothing if server language matches', async () => {
    api.get.mockResolvedValue({ data: { language: 'zh-CN' } })
    const store = useLocaleStore()
    await store.initLocale()
    expect(store.locale).toBe('zh-CN')
  })

  it('initLocale does not throw on API error', async () => {
    api.get.mockRejectedValue(new Error('API error'))
    const store = useLocaleStore()
    await expect(store.initLocale()).resolves.toBeUndefined()
  })
})
// src/composables/useMediaQuery.js
import { ref, onMounted, onUnmounted, readonly } from 'vue'

/**
 * Reactive media query hook. Returns a readonly ref that updates whenever
 * the media query match state changes.
 *
 * @param {string} query - A valid CSS media query string, e.g. '(max-width: 1023.98px)'
 * @returns {{ matches: import('vue').Ref<boolean> }}
 */
export function useMediaQuery(query) {
  const matches = ref(false)
  let mql = null
  let handler = null

  onMounted(() => {
    if (typeof window === 'undefined' || !window.matchMedia) {
      // SSR / no matchMedia: default to no match
      return
    }
    mql = window.matchMedia(query)
    matches.value = mql.matches
    // Modern API (Safari 14+, all evergreen)
    if (mql.addEventListener) {
      handler = (e) => {
        matches.value = e.matches
      }
      mql.addEventListener('change', handler)
    } else if (mql.addListener) {
      // Legacy fallback
      handler = (e) => {
        matches.value = e.matches
      }
      mql.addListener(handler)
    }
  })

  onUnmounted(() => {
    if (!mql) return
    if (mql.removeEventListener && handler) {
      mql.removeEventListener('change', handler)
    } else if (mql.removeListener && handler) {
      mql.removeListener(handler)
    }
    mql = null
    handler = null
  })

  return { matches: readonly(matches) }
}

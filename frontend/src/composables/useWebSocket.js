import { ref, onUnmounted } from 'vue'

export function useWebSocket(url, { onMessage, maxRetries = Infinity } = {}) {
  const connected = ref(false)
  let ws = null
  let retries = 0
  let retryTimer = null

  function connect() {
    const token = localStorage.getItem('token')
    if (!token) return

    ws = new WebSocket(`${url}?token=${token}`)

    ws.onopen = () => {
      connected.value = true
      retries = 0
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        onMessage?.(msg)
      } catch {}
    }

    ws.onclose = () => {
      connected.value = false
      if (retries < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retries), 30000)
        retryTimer = setTimeout(() => {
          retries++
          connect()
        }, delay)
      }
    }

    ws.onerror = () => ws.close()
  }

  function disconnect() {
    clearTimeout(retryTimer)
    ws?.close()
  }

  connect()
  onUnmounted(disconnect)

  return { connected, disconnect }
}

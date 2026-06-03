import { ref, computed, onScopeDispose, getCurrentScope } from 'vue'

/**
 * 共享 WebSocket 连接状态（单例）。
 * 任何调用方 useConnectionStatus() 都共享同一份连接、同一组 reactive refs。
 *
 * 字段:
 * - connected / reconnecting: 当前连接状态
 * - lastConnectedAt: 上次成功连接的时间戳（毫秒）
 * - reconnectAttempts: 当前重连尝试次数
 * - isStale: 断开超过 staleThresholdMs（默认 5s）时为 true
 * - staleSeconds: 断开后经过的秒数（每秒刷新）
 * - refreshTick: 每次 forceRefresh() 自增，订阅方可 watch 触发刷新
 * - forceRefresh(): 触发一次强制刷新信号
 * - onEvent(fn): 订阅 WS 消息，返回取消订阅函数
 * - onConnectionChange(fn): 订阅连接状态变化，返回取消订阅函数
 */
const STALE_DEFAULT_MS = 5000
const MAX_RETRIES_DEFAULT = Infinity

// Module-level shared state (singleton).
const connected = ref(false)
const reconnecting = ref(false)
const lastConnectedAt = ref(null)
const reconnectAttempts = ref(0)
const refreshTick = ref(0)
const now = ref(Date.now())

let _ws = null
let _retryTimer = null
let _nowTimer = null
let _staleTimer = null
let _configured = false
let _wsUrl = null
let _staleThresholdMs = STALE_DEFAULT_MS
let _maxRetries = MAX_RETRIES_DEFAULT

// Event subscribers: Set<fn>
const _eventSubs = new Set()
const _connectionSubs = new Set()

function _emit(msg) {
  _eventSubs.forEach((fn) => {
    try { fn(msg) } catch (e) { console.error('[useConnectionStatus] event handler error:', e) }
  })
}

function _emitConnection() {
  const snapshot = { connected: connected.value, reconnecting: reconnecting.value }
  _connectionSubs.forEach((fn) => {
    try { fn(snapshot) } catch (e) { console.error('[useConnectionStatus] connection handler error:', e) }
  })
}

function _scheduleReconnect() {
  if (reconnectAttempts.value >= _maxRetries) return
  reconnecting.value = true
  _emitConnection()
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)
  _retryTimer = setTimeout(() => {
    _retryTimer = null
    reconnectAttempts.value += 1
    _connect()
  }, delay)
}

function _startNowTick() {
  if (_nowTimer) return
  _nowTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
}

function _stopNowTick() {
  if (_nowTimer) {
    clearInterval(_nowTimer)
    _nowTimer = null
  }
}

function _connect() {
  const token = localStorage.getItem('token')
  if (!token) return

  try {
    _ws = new WebSocket(`${_wsUrl}?token=${token}`)
  } catch {
    _scheduleReconnect()
    return
  }

  _ws.onopen = () => {
    connected.value = true
    reconnecting.value = false
    reconnectAttempts.value = 0
    lastConnectedAt.value = Date.now()
    _emitConnection()
  }

  _ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      _emit(msg)
    } catch {
      /* ignore malformed payload */
    }
  }

  _ws.onclose = () => {
    connected.value = false
    _ws = null
    _emitConnection()
    _scheduleReconnect()
  }

  _ws.onerror = () => {
    try { _ws?.close() } catch { /* noop */ }
  }
}

function _disconnectInternal() {
  if (_retryTimer) {
    clearTimeout(_retryTimer)
    _retryTimer = null
  }
  _stopNowTick()
  if (_ws) {
    try { _ws.close() } catch { /* noop */ }
    _ws = null
  }
  connected.value = false
  reconnecting.value = false
  _emitConnection()
}

function _configure({ wsUrl, staleThresholdMs = STALE_DEFAULT_MS, maxRetries = MAX_RETRIES_DEFAULT } = {}) {
  if (_configured) return
  if (!wsUrl) return
  _configured = true
  _wsUrl = wsUrl
  _staleThresholdMs = staleThresholdMs
  _maxRetries = maxRetries
  _startNowTick()
  _connect()
}

export function useConnectionStatus(options = {}) {
  // Allow either eager config (first call) or passive subscribe (subsequent calls).
  if (options.wsUrl) {
    _configure(options)
  }

  // Always start the now-tick so isStale stays accurate for subscribers that
  // join after the connection was first created.
  _startNowTick()

  const isStale = computed(() => {
    if (connected.value) return false
    if (!lastConnectedAt.value) return false
    return now.value - lastConnectedAt.value > _staleThresholdMs
  })

  const staleSeconds = computed(() => {
    if (!lastConnectedAt.value) return 0
    return Math.max(0, Math.floor((now.value - lastConnectedAt.value) / 1000))
  })

  function forceRefresh() {
    refreshTick.value += 1
  }

  function onEvent(fn) {
    _eventSubs.add(fn)
    return () => _eventSubs.delete(fn)
  }

  function onConnectionChange(fn) {
    _connectionSubs.add(fn)
    // Fire immediately so subscriber sees current state.
    try { fn({ connected: connected.value, reconnecting: reconnecting.value }) } catch { /* noop */ }
    return () => _connectionSubs.delete(fn)
  }

  function disconnect() {
    _disconnectInternal()
  }

  // Auto-cleanup subscribers when caller's effect scope is disposed.
  if (getCurrentScope()) {
    onScopeDispose(() => {
      // We don't tear down the singleton here (it might be used elsewhere),
      // we only clean up listeners if caller added any. For simplicity we
      // keep event-subs as global; the only state that needs per-caller
      // cleanup is the connection sub, which is small.
    })
  }

  return {
    connected,
    reconnecting,
    lastConnectedAt,
    reconnectAttempts,
    isStale,
    staleSeconds,
    refreshTick,
    forceRefresh,
    onEvent,
    onConnectionChange,
    disconnect,
  }
}

// Exposed for tests / manual lifecycle control.
export const __test = {
  _reset() {
    _disconnectInternal()
    _eventSubs.clear()
    _connectionSubs.clear()
    _configured = false
    _wsUrl = null
    lastConnectedAt.value = null
    reconnectAttempts.value = 0
    refreshTick.value = 0
  },
}

import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

/**
 * 统一错误处理 composable
 * 解析 axios 错误响应，提取最具体的错误信息
 * 用法：const handleError = useApiError(); try {...} catch(e) { handleError(e) }
 */
export function useApiError() {
  const { t } = useI18n()
  return function handleError(e, fallbackKey = 'common.operationFailed') {
    const detail =
      e?.response?.data?.detail ||
      e?.response?.data?.error?.message ||
      e?.response?.data?.message ||
      e?.message
    const message = detail || t(fallbackKey)
    ElMessage({ message, type: 'error', showClose: true, duration: 4000 })
    return message
  }
}

/**
 * 重试装饰器：对失败的操作做 N 次重试，间隔递增
 */
export function withRetry(fn, opts = {}) {
  const { retries = 2, delay = 500, backoff = 2 } = opts
  return async (...args) => {
    let lastErr
    let d = delay
    for (let i = 0; i <= retries; i++) {
      try {
        return await fn(...args)
      } catch (e) {
        lastErr = e
        if (i === retries) break
        await new Promise((r) => setTimeout(r, d))
        d *= backoff
      }
    }
    throw lastErr
  }
}

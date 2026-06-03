import api from './index'

export const getDashboard = () => api.get('/dashboard')

/**
 * 获取后端版本信息
 * 后端通常在 /health 或 /version 端点暴露版本
 */
export async function getBackendVersion() {
  // 尝试从 /health 端点推断版本（如果存在）
  const { data } = await api.get('/health')
  return data
}

/**
 * 通用导出 API
 */
export const exportDevicesCsv = (params) =>
  api.get('/devices/export', { params, responseType: 'blob' })

export const exportRecordingsCsv = (params) =>
  api.get('/recordings/export', { params, responseType: 'blob' })

/**
 * CSV 导出工具
 * - 自动转义双引号、换行、逗号
 * - BOM 前缀让 Excel 正确识别 UTF-8
 */

function escapeCell(value) {
  if (value === null || value === undefined) return ''
  const s = String(value)
  // 强制引用：包含逗号、双引号、换行、回车
  if (/[",\n\r]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`
  }
  return s
}

export function rowsToCsv(headers, rows) {
  const head = headers.map(escapeCell).join(',')
  const body = rows.map((r) => r.map(escapeCell).join(',')).join('\r\n')
  return `${head}\r\n${body}\r\n`
}

/**
 * 触发浏览器下载 CSV
 * @param {string} filename  例如 devices-2024-01-15.csv
 * @param {string} csvContent  CSV 文本
 */
export function downloadCsv(filename, csvContent) {
  // 添加 BOM 让 Excel 识别 UTF-8
  const blob = new Blob(['﻿', csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/**
 * 一站式：根据表头与行数据下载 CSV
 */
export function exportCsv(filename, headers, rows) {
  const csv = rowsToCsv(headers, rows)
  downloadCsv(filename, csv)
  return filename
}

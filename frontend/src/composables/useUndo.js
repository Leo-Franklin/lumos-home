import { h } from 'vue'
import { ElMessage } from 'element-plus'

/**
 * 删除撤销 toast（前端延迟删除，5 秒内可撤销）
 *
 * 设计：调用 performDelete() 前先等 5 秒；若 5 秒内用户点「撤销」，
 * 则跳过 performDelete()，相当于未删除。这是真正的"撤销"，不依赖后端支持。
 *
 * 用法：
 *   import { scheduleUndo } from '@/composables/useUndo'
 *
 *   function handleDelete(row) {
 *     // 1. UI 上立即隐藏（调用方负责）
 *     list.value = list.value.filter(r => r.id !== row.id)
 *     // 2. 5 秒后真正发请求
 *     scheduleUndo({
 *       label: '已删除「' + row.file_name + '」',
 *       performDelete: () => deleteRecording(row.id),
 *       onUndo: () => list.value.unshift(row),
 *       onError: handleError,
 *     })
 *   }
 *
 * @param {object} opts
 * @param {string} opts.label              toast 文本
 * @param {() => Promise<void>} opts.performDelete  真正删除（仅在 5s 内未撤销时调用）
 * @param {() => void} [opts.onUndo]       撤销回调（恢复 UI）
 * @param {(e:any)=>any} [opts.onError]    删除失败时的错误处理
 * @param {number} [opts.duration]         倒计时毫秒，默认 5000
 */
export function scheduleUndo({
  label,
  performDelete,
  onUndo,
  onError,
  duration = 5000,
}) {
  let undone = false
  let executed = false

  const execute = async () => {
    if (executed || undone) return
    executed = true
    try {
      await performDelete()
    } catch (e) {
      // 真正执行时失败 → 回滚 UI
      onUndo?.()
      if (onError) onError(e)
    }
  }

  // ElMessage 自定义 action 按钮（Element Plus 2.x）
  const msg = ElMessage({
    message: label,
    type: 'success',
    duration,
    showClose: false,
    action: h(
      'button',
      {
        type: 'button',
        class: 'el-message-undo-btn',
        onClick: () => {
          if (undone) return
          undone = true
          onUndo?.()
          // 主动关闭
          if (msg && typeof msg.close === 'function') msg.close()
        },
      },
      '撤销',
    ),
  })

  // duration 后真正执行
  setTimeout(execute, duration)
}

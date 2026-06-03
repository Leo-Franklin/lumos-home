import { ref, watch, onUnmounted } from 'vue'
import { ElMessageBox } from 'element-plus'

/**
 * 表单脏检查 composable
 *
 * 用法：
 *   const { isDirty, reset, checkBeforeClose } = useFormDirty(formRef, { ignore: ['_mac'] })
 *   <el-form ref="formRef" :model="form" :rules="rules">...</el-form>
 *   <el-dialog @close="checkBeforeClose(close)">...</el-dialog>
 *
 * 行为：
 *   - 首次挂载时把当前表单值保存为基线
 *   - 任一字段变化（深度 watch）即把 isDirty 置为 true
 *   - reset() 重置基线（提交成功后调用）
 *   - checkBeforeClose(closeFn) 在 isDirty 时弹 ElMessageBox.confirm，
 *     用户确认丢弃则调用 closeFn()，否则不调用
 *
 * ignore: 忽略比较的字段路径数组（如 ['password']），用于密码字段不回显
 */
export function useFormDirty(formRef, options = {}) {
  const { ignore = [] } = options
  const isDirty = ref(false)
  let baseline = null
  let stopWatch = null
  let initialized = false

  function snapshot(form) {
    // Deep clone via structured JSON; ignores Vue reactive proxies
    return JSON.stringify(form, (key, value) => {
      if (ignore.includes(key)) return undefined
      return value
    })
  }

  function init(form) {
    if (!form) return
    baseline = snapshot(form)
    isDirty.value = false
    initialized = true

    if (stopWatch) stopWatch()
    stopWatch = watch(
      () => form,
      (next) => {
        if (!initialized || !baseline) return
        isDirty.value = snapshot(next) !== baseline
      },
      { deep: true },
    )
  }

  function reset() {
    baseline = null
    isDirty.value = false
    initialized = false
    if (stopWatch) {
      stopWatch()
      stopWatch = null
    }
  }

  /**
   * 在弹窗关闭钩子中使用
   * @param {Function} closeFn 实际关闭弹窗的回调
   * @returns {Promise<boolean>} true 表示继续关闭，false 表示取消
   */
  async function checkBeforeClose(closeFn) {
    if (!isDirty.value) {
      closeFn?.()
      return true
    }
    try {
      await ElMessageBox.confirm(
        '当前表单有未保存的修改，确定关闭？',
        '放弃修改',
        { type: 'warning', confirmButtonText: '放弃修改', cancelButtonText: '继续编辑' },
      )
    } catch {
      return false
    }
    closeFn?.()
    return true
  }

  onUnmounted(() => {
    if (stopWatch) stopWatch()
  })

  return { isDirty, init, reset, checkBeforeClose }
}

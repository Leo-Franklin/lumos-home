<script setup>
import { ref, onMounted } from 'vue'
import { useDevicesStore } from '@/stores/devices'
import { updateDevice, deleteDevice } from '@/api/devices'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import ScanProgress from '@/components/ScanProgress.vue'
import DeviceCard from '@/components/DeviceCard.vue'

const devicesStore = useDevicesStore()

const editDialog = ref(false)
const editForm = ref({})

onMounted(() => devicesStore.fetchDevices())

function openEdit(row) {
  editForm.value = { ...row }
  editDialog.value = true
}

async function saveEdit() {
  try {
    await updateDevice(editForm.value.mac, {
      alias: editForm.value.alias,
      device_type: editForm.value.device_type,
      notes: editForm.value.notes,
    })
    ElMessage.success('保存成功')
    editDialog.value = false
    devicesStore.fetchDevices()
  } catch {
    ElMessage.error('保存失败')
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除设备 ${row.alias || row.mac}？`, '确认删除', { type: 'warning' })
  await deleteDevice(row.mac)
  ElMessage.success('已删除')
  devicesStore.fetchDevices()
}

const deviceTypeOptions = ['camera', 'computer', 'phone', 'iot', 'unknown']
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h2 class="page-title">设备列表</h2>
        <span class="page-sub">
          在线 {{ devicesStore.items.filter((d) => d.is_online).length }} /
          总计 {{ devicesStore.total }}
        </span>
      </div>
      <div class="header-actions">
        <ScanProgress />
        <el-button
          type="primary"
          :loading="devicesStore.scanning"
          :icon="Refresh"
          @click="devicesStore.scan()"
        >
          扫描网络
        </el-button>
      </div>
    </div>

    <div class="device-list" v-loading="devicesStore.loading">
      <DeviceCard
        v-for="device in devicesStore.items"
        :key="device.mac"
        :device="device"
        @edit="openEdit"
        @delete="handleDelete"
      />
      <div v-if="!devicesStore.loading && devicesStore.items.length === 0" class="empty-state">
        暂无设备，请点击「扫描网络」
      </div>
    </div>

    <el-dialog v-model="editDialog" title="编辑设备" width="440px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="MAC">
          <el-input :value="editForm.mac" disabled />
        </el-form-item>
        <el-form-item label="别名">
          <el-input v-model="editForm.alias" placeholder="输入设备别名" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="editForm.device_type" style="width: 100%">
            <el-option v-for="t in deviceTypeOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
  margin: 0 0 2px;
}
.page-sub {
  font-size: 12px;
  color: var(--color-text-muted);
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface);
}

.empty-state {
  padding: 40px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-muted);
}
</style>

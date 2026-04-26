<script setup>
import { ref, onMounted } from 'vue'
import { useCamerasStore } from '@/stores/cameras'
import { useDevicesStore } from '@/stores/devices'
import { createCamera, updateCamera, deleteCamera, probeCamera, startRecord, stopRecord } from '@/api/cameras'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const camerasStore = useCamerasStore()
const devicesStore = useDevicesStore()

const addDialog = ref(false)
const probeDialog = ref(false)
const probeResult = ref(null)
const probeLoading = ref(false)
const addForm = ref({ device_mac: '', onvif_host: '', onvif_port: 2020, onvif_user: 'admin', onvif_password: '', rtsp_port: 554, stream_profile: 'mainStream' })

onMounted(async () => {
  await Promise.all([camerasStore.fetchCameras(), devicesStore.fetchDevices()])
})

function openAdd() {
  addForm.value = { device_mac: '', onvif_host: '', onvif_port: 2020, onvif_user: 'admin', onvif_password: '', rtsp_port: 554, stream_profile: 'mainStream' }
  addDialog.value = true
}

async function handleAdd() {
  try {
    await createCamera(addForm.value)
    ElMessage.success('摄像头已添加')
    addDialog.value = false
    camerasStore.fetchCameras()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

async function handleDelete(cam) {
  await ElMessageBox.confirm(`确定删除摄像头 ${cam.onvif_host}？`, '确认删除', { type: 'warning' })
  await deleteCamera(cam.device_mac)
  ElMessage.success('已删除')
  camerasStore.fetchCameras()
}

async function handleProbe(cam) {
  probeLoading.value = true
  probeResult.value = null
  probeDialog.value = true
  try {
    const { data } = await probeCamera(cam.device_mac)
    probeResult.value = data
  } catch (e) {
    ElMessage.error('ONVIF 探测失败：' + (e.response?.data?.error?.message || e.message))
    probeDialog.value = false
  } finally {
    probeLoading.value = false
  }
}

async function handleRecord(cam) {
  try {
    if (cam.is_recording) {
      await stopRecord(cam.device_mac)
      ElMessage.success('已发送停止录制指令')
      await camerasStore.fetchCameras()
    } else {
      await startRecord(cam.device_mac)
      ElMessage.success('已发送开始录制指令')
      await camerasStore.fetchCameras()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.response?.data?.error?.message || '操作失败')
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h3>摄像头管理</h3>
      <el-button type="primary" :icon="Plus" @click="openAdd">添加摄像头</el-button>
    </div>

    <el-table v-loading="camerasStore.loading" :data="camerasStore.items" stripe border style="width: 100%">
      <el-table-column label="设备 MAC" prop="device_mac" width="160" />
      <el-table-column label="ONVIF 地址" width="160">
        <template #default="{ row }">{{ row.onvif_host }}:{{ row.onvif_port }}</template>
      </el-table-column>
      <el-table-column label="RTSP 端口" prop="rtsp_port" width="100" />
      <el-table-column label="码流" prop="stream_profile" width="110" />
      <el-table-column label="录制状态" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_recording ? 'danger' : 'info'" size="small">
            {{ row.is_recording ? '录制中' : '空闲' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="220" align="center">
        <template #default="{ row }">
          <el-button size="small" @click="handleProbe(row)">ONVIF 探测</el-button>
          <el-button
            size="small"
            :type="row.is_recording ? 'warning' : 'success'"
            @click="handleRecord(row)"
          >
            {{ row.is_recording ? '停止录制' : '开始录制' }}
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加摄像头弹窗 -->
    <el-dialog v-model="addDialog" title="添加摄像头" width="480px">
      <el-form :model="addForm" label-width="110px">
        <el-form-item label="设备 MAC">
          <el-select v-model="addForm.device_mac" placeholder="选择设备" filterable style="width: 100%">
            <el-option
              v-for="d in devicesStore.items"
              :key="d.mac"
              :label="`${d.alias || d.mac} (${d.ip})`"
              :value="d.mac"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="ONVIF 地址">
          <el-input v-model="addForm.onvif_host" placeholder="192.168.1.x" />
        </el-form-item>
        <el-form-item label="ONVIF 端口">
          <el-input-number v-model="addForm.onvif_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="ONVIF 用户名">
          <el-input v-model="addForm.onvif_user" />
        </el-form-item>
        <el-form-item label="ONVIF 密码">
          <el-input v-model="addForm.onvif_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="RTSP 端口">
          <el-input-number v-model="addForm.rtsp_port" :min="1" :max="65535" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">添加</el-button>
      </template>
    </el-dialog>

    <!-- ONVIF 探测结果 -->
    <el-dialog v-model="probeDialog" title="ONVIF 探测结果" width="500px">
      <div v-if="probeLoading" style="text-align: center; padding: 20px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>正在探测...</p>
      </div>
      <template v-else-if="probeResult">
        <el-descriptions :column="2" border>
          <el-descriptions-item
            v-for="(v, k) in probeResult.device_info"
            :key="k"
            :label="k"
          >{{ v }}</el-descriptions-item>
        </el-descriptions>
        <h4>可用码流</h4>
        <el-table :data="probeResult.profiles" size="small">
          <el-table-column prop="index" label="#" width="50" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="token" label="Token" />
        </el-table>
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
.page-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
}
</style>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCamerasStore } from '@/stores/cameras'
import { useDevicesStore } from '@/stores/devices'
import { useDLNAStore } from '@/stores/dlna'
import {
  createCamera, updateCamera, deleteCamera, probeCamera,
  startRecord, stopRecord, mjpegStreamUrl,
  takeSnapshot, startLive, stopLive, hlsLiveUrl,
} from '@/api/cameras'
import { Plus, Edit, Delete, Search, VideoPlay, Camera, VideoCamera, VideoPause, VideoCameraFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CameraPlayer from '@/components/CameraPlayer.vue'

const { t } = useI18n()

const camerasStore = useCamerasStore()
const devicesStore = useDevicesStore()
const dlnaStore = useDLNAStore()

// ── Add ──────────────────────────────────────────────────────
const addDialog = ref(false)
const addForm = ref({
  device_mac: '', onvif_host: '', onvif_port: 2020,
  onvif_user: 'admin', onvif_password: '', rtsp_port: 554, stream_profile: 'mainStream',
})

function openAdd() {
  addForm.value = {
    device_mac: '', onvif_host: '', onvif_port: 2020,
    onvif_user: 'admin', onvif_password: '', rtsp_port: 554, stream_profile: 'mainStream',
  }
  addDialog.value = true
}

async function handleAdd() {
  try {
    await createCamera(addForm.value)
    ElMessage.success(t('cameras.added'))
    addDialog.value = false
    camerasStore.fetchCameras()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('cameras.addFailed'))
  }
}

// ── Edit ─────────────────────────────────────────────────────
const editDialog = ref(false)
const editForm = ref({})

function openEdit(cam) {
  editForm.value = {
    onvif_host: cam.onvif_host,
    onvif_port: cam.onvif_port,
    onvif_user: cam.onvif_user || '',
    onvif_password: '',
    rtsp_port: cam.rtsp_port,
    rtsp_url: cam.rtsp_url || '',
    stream_profile: cam.stream_profile,
    auto_cast_dlna: cam.auto_cast_dlna || null,
    _mac: cam.device_mac,
  }
  editDialog.value = true
}

async function handleEdit() {
  const { _mac, ...payload } = editForm.value
  if (!payload.onvif_password) delete payload.onvif_password
  if (!payload.rtsp_url) payload.rtsp_url = null
  try {
    await updateCamera(_mac, payload)
    ElMessage.success(t('cameras.saved'))
    editDialog.value = false
    camerasStore.fetchCameras()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('cameras.saveFailed'))
  }
}

// ── Delete ────────────────────────────────────────────────────
async function handleDelete(cam) {
  await ElMessageBox.confirm(t('cameras.deleteConfirm', { host: cam.onvif_host }), t('common.confirmDelete'), { type: 'warning' })
  await deleteCamera(cam.device_mac)
  ElMessage.success(t('cameras.deleted'))
  camerasStore.fetchCameras()
}

// ── Probe ─────────────────────────────────────────────────────
const probeDialog = ref(false)
const probeResult = ref(null)
const probeLoading = ref(false)

async function handleProbe(cam) {
  probeLoading.value = true
  probeResult.value = null
  probeDialog.value = true
  try {
    const { data } = await probeCamera(cam.device_mac)
    probeResult.value = data
    camerasStore.fetchCameras()
  } catch (e) {
    ElMessage.error(t('cameras.onvifProbeFailed', { detail: e.response?.data?.error?.message || e.message }))
    probeDialog.value = false
  } finally {
    probeLoading.value = false
  }
}

// ── Record ────────────────────────────────────────────────────
async function handleRecord(cam) {
  try {
    if (cam.is_recording) {
      await stopRecord(cam.device_mac)
      ElMessage.success(t('cameras.recordStopped'))
    } else {
      await startRecord(cam.device_mac)
      ElMessage.success(t('cameras.recordStarted'))
    }
    await camerasStore.fetchCameras()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.response?.data?.error?.message || t('common.operationFailed'))
  }
}

// ── Live Preview (MJPEG) ──────────────────────────────────────
const liveDialog = ref(false)
const liveUrl = ref('')
const liveTitle = ref('')

function openLive(cam) {
  if (!cam.rtsp_url) {
    ElMessage.warning(t('cameras.noRtspWarning'))
    return
  }
  liveTitle.value = t('cameras.liveTitle', { host: cam.onvif_host })
  liveUrl.value = mjpegStreamUrl(cam.device_mac)
  liveDialog.value = true
}

function closeLive() {
  liveUrl.value = ''
}

// ── Snapshot (B1) ─────────────────────────────────────────────
const snapshotDialog = ref(false)
const snapshotUrl = ref('')
const snapshotTitle = ref('')
const snapshotLoading = ref(false)

async function handleSnapshot(cam) {
  if (!cam.rtsp_url) {
    ElMessage.warning(t('cameras.noRtsp'))
    return
  }
  snapshotLoading.value = true
  snapshotTitle.value = t('cameras.snapshotTitle', { host: cam.onvif_host })
  try {
    const { data } = await takeSnapshot(cam.device_mac)
    if (snapshotUrl.value) URL.revokeObjectURL(snapshotUrl.value)
    snapshotUrl.value = URL.createObjectURL(data)
    snapshotDialog.value = true
  } catch (e) {
    ElMessage.error(t('cameras.snapshotFailed'))
  } finally {
    snapshotLoading.value = false
  }
}

function closeSnapshot() {
  if (snapshotUrl.value) { URL.revokeObjectURL(snapshotUrl.value); snapshotUrl.value = '' }
}

function downloadSnapshot() {
  const a = document.createElement('a')
  a.href = snapshotUrl.value
  a.download = `snapshot_${Date.now()}.jpg`
  a.click()
}

// ── HLS Live (B2) ─────────────────────────────────────────────
const hlsDialog = ref(false)
const hlsTitle = ref('')
const hlsSrc = ref('')
const hlsStarting = ref(false)
let hlsMac = ''

async function openHlsLive(cam) {
  if (!cam.rtsp_url) {
    ElMessage.warning(t('cameras.noRtspWarning'))
    return
  }
  hlsStarting.value = true
  hlsMac = cam.device_mac
  try {
    await startLive(cam.device_mac)
    hlsTitle.value = t('cameras.hlsTitle', { host: cam.onvif_host })
    hlsSrc.value = hlsLiveUrl(cam.device_mac)
    hlsDialog.value = true
  } catch (e) {
    ElMessage.error(t('cameras.hlsStartFailed'))
  } finally {
    hlsStarting.value = false
  }
}

async function closeHlsLive() {
  hlsSrc.value = ''
  if (hlsMac) {
    try { await stopLive(hlsMac) } catch {}
    hlsMac = ''
  }
}

onMounted(async () => {
  await Promise.all([camerasStore.fetchCameras(), devicesStore.fetchDevices(), dlnaStore.fetchDevices()])
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('cameras.title') }}</h2>
      <el-button type="primary" :icon="Plus" @click="openAdd">{{ $t('cameras.addCamera') }}</el-button>
    </div>

    <el-table v-loading="camerasStore.loading" :data="camerasStore.items" style="width: 100%">
      <el-table-column :label="$t('cameras.deviceMac')" prop="device_mac" width="160" />
      <el-table-column :label="$t('cameras.onvifHost')" width="170">
        <template #default="{ row }">{{ row.onvif_host }}:{{ row.onvif_port }}</template>
      </el-table-column>
      <el-table-column :label="$t('cameras.rtspUrl')" min-width="200">
        <template #default="{ row }">
          <span class="rtsp-url">{{ row.rtsp_url || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('cameras.streamProfile')" prop="stream_profile" width="110" />
      <el-table-column :label="$t('cameras.online')" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_online ? 'success' : 'info'" size="small">
            {{ row.is_online ? $t('cameras.online') : $t('cameras.offline') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('cameras.recording')" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_recording ? 'danger' : 'info'" size="small">
            {{ row.is_recording ? $t('cameras.recording') : $t('cameras.idle') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('cameras.lastProbe')" width="160">
        <template #default="{ row }">{{ $d(row.last_probe_at, 'short') }}</template>
      </el-table-column>
      <el-table-column :label="$t('cameras.actions')" min-width="240" align="center">
        <template #default="{ row }">
          <div class="action-group">
            <el-tooltip :content="$t('cameras.onvifProbe')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="Search" @click="handleProbe(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('cameras.livePreview')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="VideoPlay" @click="openLive(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('cameras.snapshot')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="Camera" :loading="snapshotLoading" @click="handleSnapshot(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('cameras.hlsLive')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="VideoCamera" :loading="hlsStarting" @click="openHlsLive(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('cameras.edit')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="Edit" @click="openEdit(row)" />
            </el-tooltip>
            <el-tooltip :content="row.is_recording ? $t('cameras.stopRecord') : $t('cameras.startRecord')" :show-after="400">
              <el-button
                class="action-btn"
                :class="row.is_recording ? 'action-btn--stop' : 'action-btn--record'"
                size="small"
                :icon="row.is_recording ? VideoPause : VideoCameraFilled"
                @click="handleRecord(row)"
              />
            </el-tooltip>
            <el-tooltip :content="$t('cameras.delete')" :show-after="400">
              <el-button class="action-btn action-btn--danger" size="small" :icon="Delete" @click="handleDelete(row)" />
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加摄像头弹窗 -->
    <el-dialog v-model="addDialog" :title="$t('cameras.addCamera')" width="480px">
      <el-form :model="addForm" label-width="110px">
        <el-form-item :label="$t('cameras.deviceMac')">
          <el-select v-model="addForm.device_mac" :placeholder="$t('cameras.selectDevice')" filterable style="width: 100%">
            <el-option
              v-for="d in devicesStore.items"
              :key="d.mac"
              :label="`${d.alias || d.hostname || d.mac} (${d.ip})`"
              :value="d.mac"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('cameras.onvifHost')">
          <el-input v-model="addForm.onvif_host" :placeholder="$t('cameras.onvifPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('cameras.onvifPort')">
          <el-input-number v-model="addForm.onvif_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item :label="$t('cameras.onvifUser')">
          <el-input v-model="addForm.onvif_user" />
        </el-form-item>
        <el-form-item :label="$t('cameras.onvifPassword')">
          <el-input v-model="addForm.onvif_password" type="password" show-password />
        </el-form-item>
        <el-form-item :label="$t('cameras.rtspPort')">
          <el-input-number v-model="addForm.rtsp_port" :min="1" :max="65535" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog = false">{{ $t('cameras.cancel') }}</el-button>
        <el-button type="primary" @click="handleAdd">{{ $t('cameras.add') }}</el-button>
      </template>
    </el-dialog>

    <!-- 编辑摄像头弹窗 -->
    <el-dialog v-model="editDialog" :title="$t('cameras.editCamera')" width="500px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item :label="$t('cameras.onvifHost')">
          <el-input v-model="editForm.onvif_host" />
        </el-form-item>
        <el-form-item :label="$t('cameras.onvifPort')">
          <el-input-number v-model="editForm.onvif_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item :label="$t('cameras.onvifUser')">
          <el-input v-model="editForm.onvif_user" />
        </el-form-item>
        <el-form-item :label="$t('cameras.onvifPassword')">
          <el-input v-model="editForm.onvif_password" type="password" show-password :placeholder="$t('cameras.passwordPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('cameras.rtspPort')">
          <el-input-number v-model="editForm.rtsp_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item :label="$t('cameras.rtspUrl')">
          <el-input v-model="editForm.rtsp_url" :placeholder="$t('cameras.rtspUrlPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('cameras.streamProfile')">
          <el-select v-model="editForm.stream_profile" style="width: 100%">
            <el-option value="mainStream" :label="$t('cameras.mainStream')" />
            <el-option value="subStream" :label="$t('cameras.subStream')" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('cameras.dlnaAutoCast')">
          <el-select v-model="editForm.auto_cast_dlna" clearable :placeholder="$t('cameras.dlnaPlaceholder')" style="width: 100%">
            <el-option
              v-for="d in dlnaStore.devices"
              :key="d.udn"
              :label="d.friendly_name || d.udn"
              :value="d.udn"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">{{ $t('cameras.cancel') }}</el-button>
        <el-button type="primary" @click="handleEdit">{{ $t('cameras.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- ONVIF 探测结果 -->
    <el-dialog v-model="probeDialog" :title="$t('cameras.probeResult')" width="520px">
      <div v-if="probeLoading" style="text-align: center; padding: 20px">
        <el-text>{{ $t('cameras.probing') }}</el-text>
      </div>
      <template v-else-if="probeResult">
        <el-descriptions :column="2" border>
          <el-descriptions-item
            v-for="(v, k) in probeResult.device_info"
            :key="k"
            :label="k"
          >{{ v }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin: 16px 0 8px">{{ $t('cameras.availableStreams') }}</h4>
        <el-table :data="probeResult.profiles" size="small" border>
          <el-table-column prop="index" label="#" width="50" />
          <el-table-column prop="name" :label="$t('cameras.name')" />
          <el-table-column prop="token" :label="$t('cameras.token')" />
          <el-table-column prop="rtsp_url" :label="$t('cameras.rtspUrl')" show-overflow-tooltip />
        </el-table>
        <el-alert v-if="probeResult.auto_set_rtsp_url" type="success" style="margin-top: 12px" :closable="false">
          {{ $t('cameras.rtspUrlWritten', { url: probeResult.auto_set_rtsp_url }) }}
        </el-alert>
      </template>
    </el-dialog>

    <!-- MJPEG 实时预览 -->
    <el-dialog
      v-model="liveDialog"
      :title="liveTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeLive"
    >
      <CameraPlayer v-if="liveDialog && liveUrl" mode="live" :src="liveUrl" />
    </el-dialog>

    <!-- 截图预览 -->
    <el-dialog
      v-model="snapshotDialog"
      :title="snapshotTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeSnapshot"
    >
      <img v-if="snapshotUrl" :src="snapshotUrl" style="width:100%; display:block; border-radius:4px;" />
      <template #footer>
        <el-button @click="snapshotDialog = false">{{ $t('common.close') }}</el-button>
        <el-button type="primary" @click="downloadSnapshot">{{ $t('common.download') }}</el-button>
      </template>
    </el-dialog>

    <!-- HLS 直播 -->
    <el-dialog
      v-model="hlsDialog"
      :title="hlsTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeHlsLive"
    >
      <CameraPlayer v-if="hlsDialog && hlsSrc" mode="hls" :src="hlsSrc" />
    </el-dialog>
  </div>
</template>

<style scoped>
.rtsp-url {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--color-text-secondary);
  word-break: break-all;
}

/* ── Table styling ──────────────────────────── */
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-header-text-color: var(--color-text-muted);
  --el-table-border-color: var(--color-border-subtle);
  --el-table-row-hover-bg-color: var(--color-surface-raised);
  background: transparent;
}

:deep(.el-table__header th.el-table__cell) {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 0;
}

:deep(.el-table__body td.el-table__cell) {
  padding: 10px 0;
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}

/* Action buttons */
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-raised);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--color-text-primary);
  --el-button-active-bg-color: var(--color-surface-overlay);
  --el-button-active-border-color: transparent;
  height: 28px;
  width: 28px;
  padding: 3px;
  border-radius: 5px;
  font-size: 15px;
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out;
}

.action-btn--danger {
  --el-button-hover-bg-color: rgba(240, 82, 82, 0.1);
  --el-button-hover-text-color: var(--color-error);
  --el-button-active-bg-color: rgba(240, 82, 82, 0.15);
}

.action-btn--record {
  --el-button-hover-bg-color: rgba(38, 194, 129, 0.1);
  --el-button-hover-text-color: var(--color-online);
  --el-button-active-bg-color: rgba(38, 194, 129, 0.15);
}

.action-btn--stop {
  --el-button-hover-bg-color: rgba(240, 125, 56, 0.1);
  --el-button-hover-text-color: var(--color-warning);
  --el-button-active-bg-color: rgba(240, 125, 56, 0.15);
}
</style>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApiError } from '@/composables/useApiError'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useMembersStore } from '@/stores/members'
import { listDevices } from '@/api/devices'
import { listCameras } from '@/api/cameras'
import { createMember, updateMember, deleteMember } from '@/api/members'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState.vue'
import MemberOverviewBar from '@/components/members/MemberOverviewBar.vue'
import MemberCard from '@/components/members/MemberCard.vue'
import MemberDetailPanel from '@/components/members/MemberDetailPanel.vue'
import { buildDeviceMap } from '@/utils/memberDeviceLabel'

const { t } = useI18n()
const router = useRouter()
const handleError = useApiError()
const membersStore = useMembersStore()
const { matches: isNarrow } = useMediaQuery('(max-width: 1023.98px)')

const allDevices = ref([])
const allCameras = ref([])
const deviceMap = computed(() => buildDeviceMap(allDevices.value))

const selectedMember = ref(null)
const drawerOpen = ref(false)

// ── Member CRUD ────────────────────────────────────────────
const memberDialog = ref(false)
const isEditMember = ref(false)
const memberForm = ref({ name: '', avatar_url: '', webhook_url: '', auto_record_cameras: [] })
const editMemberId = ref(null)

onMounted(async () => {
  await membersStore.fetchMembers()
  const [devRes, camRes] = await Promise.all([
    listDevices({ page: 1, page_size: 200, device_type: 'phone' }),
    listCameras(),
  ])
  allDevices.value = devRes.data.items
  allCameras.value = camRes.data
  if (membersStore.items.length && !selectedMember.value) {
    selectMember(membersStore.items[0])
  }
})

watch(
  () => membersStore.items,
  (items) => {
    if (!items.length) {
      selectedMember.value = null
      return
    }
    if (!selectedMember.value || !items.some((m) => m.id === selectedMember.value.id)) {
      selectMember(items[0])
    } else {
      selectedMember.value = items.find((m) => m.id === selectedMember.value.id) || items[0]
    }
  },
)

function selectMember(member) {
  selectedMember.value = member
  if (isNarrow.value) drawerOpen.value = true
}

function openAddMember() {
  isEditMember.value = false
  editMemberId.value = null
  memberForm.value = { name: '', avatar_url: '', webhook_url: '', auto_record_cameras: [] }
  memberDialog.value = true
}

function openEditMember(member) {
  isEditMember.value = true
  editMemberId.value = member.id
  memberForm.value = {
    name: member.name,
    avatar_url: member.avatar_url || '',
    webhook_url: member.webhook_url || '',
    auto_record_cameras: member.auto_record_cameras ? [...member.auto_record_cameras] : [],
  }
  memberDialog.value = true
}

async function submitMember() {
  try {
    const payload = {
      name: memberForm.value.name,
      avatar_url: memberForm.value.avatar_url || null,
      webhook_url: memberForm.value.webhook_url || null,
      auto_record_cameras: memberForm.value.auto_record_cameras,
    }
    if (isEditMember.value) {
      await updateMember(editMemberId.value, payload)
      ElMessage.success(t('members.updated'))
    } else {
      const { data } = await createMember(payload)
      ElMessage.success(t('members.created'))
      await membersStore.fetchMembers()
      selectMember(data)
    }
    memberDialog.value = false
    if (isEditMember.value) {
      await membersStore.fetchMembers()
    }
  } catch (e) {
    handleError(e, 'common.operationFailed')
  }
}

async function handleDeleteMember(member) {
  await ElMessageBox.confirm(
    t('members.deleteConfirm', { name: member.name }),
    t('common.confirmDelete'),
    { type: 'warning' },
  )
  await deleteMember(member.id)
  ElMessage.success(t('members.deleted'))
  drawerOpen.value = false
  await membersStore.fetchMembers()
}

function onDevicesChanged() {
  membersStore.fetchMembers()
}

function goToDevices() {
  router.push('/devices')
}
</script>

<template>
  <div class="members-page">
    <div class="page-header">
      <h2 class="page-title">{{ $t('members.title') }}</h2>
      <el-button type="primary" :icon="Plus" @click="openAddMember">{{
        $t('members.addMember')
      }}</el-button>
    </div>

    <MemberOverviewBar v-if="membersStore.items.length" :members="membersStore.items" />

    <div v-if="membersStore.loading" class="members-skeleton">
      <el-skeleton v-for="n in 3" :key="n" animated>
        <template #template>
          <el-skeleton-item variant="rect" style="height: 88px; border-radius: 8px" />
        </template>
      </el-skeleton>
    </div>

    <div v-else-if="!membersStore.items.length" class="empty-container">
      <EmptyState
        icon="member"
        :title="$t('members.emptyTitle')"
        :description="$t('members.emptyDesc')"
        :action-label="$t('members.addMember')"
        @action="openAddMember"
      />
    </div>

    <div v-else class="members-layout">
      <div class="members-list">
        <MemberCard
          v-for="member in membersStore.items"
          :key="member.id"
          :member="member"
          :selected="selectedMember?.id === member.id"
          :device-count="member.device_count ?? 0"
          @select="selectMember"
        />
      </div>

      <div v-if="!isNarrow && selectedMember" class="members-detail glass-card">
        <MemberDetailPanel
          :key="selectedMember.id"
          :member="selectedMember"
          :all-devices="allDevices"
          :all-cameras="allCameras"
          :device-map="deviceMap"
          @edit="openEditMember"
          @delete="handleDeleteMember"
          @devices-changed="onDevicesChanged"
        />
      </div>

      <div v-else-if="!isNarrow" class="members-detail members-detail--placeholder glass-card">
        <EmptyState
          compact
          size="small"
          icon="member"
          :title="$t('members.selectMember')"
          :description="$t('members.selectMemberDesc')"
        />
      </div>
    </div>

    <el-drawer
      v-if="isNarrow"
      v-model="drawerOpen"
      :title="selectedMember?.name"
      direction="btt"
      size="85%"
      class="member-drawer"
    >
      <MemberDetailPanel
        v-if="selectedMember"
        :key="selectedMember.id"
        :member="selectedMember"
        :all-devices="allDevices"
        :all-cameras="allCameras"
        :device-map="deviceMap"
        @edit="openEditMember"
        @delete="handleDeleteMember"
        @devices-changed="onDevicesChanged"
      />
    </el-drawer>

    <!-- Create / edit dialog (automation fields) -->
    <el-dialog
      v-model="memberDialog"
      :title="isEditMember ? $t('members.editMember') : $t('members.addMember')"
      width="460px"
    >
      <el-form :model="memberForm" label-width="110px">
        <el-form-item :label="$t('members.name')" required>
          <el-input v-model="memberForm.name" :placeholder="$t('members.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('members.avatarUrl')">
          <el-input v-model="memberForm.avatar_url" :placeholder="$t('members.avatarOptional')" />
        </el-form-item>
        <el-form-item :label="$t('members.webhook')">
          <el-input
            v-model="memberForm.webhook_url"
            :placeholder="$t('members.webhookPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('members.autoRecord')">
          <el-select
            v-model="memberForm.auto_record_cameras"
            multiple
            clearable
            :placeholder="$t('members.autoRecordPlaceholder')"
            style="width: 100%"
          >
            <el-option
              v-for="c in allCameras"
              :key="c.device_mac"
              :label="c.alias || c.onvif_host || c.device_mac"
              :value="c.device_mac"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <p v-if="!isEditMember" class="form-hint">
        {{ $t('members.createHint') }}
        <el-button type="primary" link @click="goToDevices">{{
          $t('members.goDevices')
        }}</el-button>
      </p>
      <template #footer>
        <el-button @click="memberDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitMember">{{
          isEditMember ? $t('common.save') : $t('common.create')
        }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.members-page {
  --members-chrome: calc(var(--header-height) + 2 * var(--space-6) + 52px);
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--members-chrome));
  max-height: calc(100vh - var(--members-chrome));
  overflow: hidden;
}

.members-page .page-header {
  flex-shrink: 0;
  margin-bottom: 12px;
}

.members-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.empty-container {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.members-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(240px, 300px) 1fr;
  gap: 16px;
  overflow: hidden;
}

.members-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.members-detail {
  padding: 16px;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.members-detail--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0 0 4px;
  line-height: 1.5;
}

:deep(.member-drawer .el-drawer__body) {
  padding-top: 0;
  overflow: hidden;
}

@media (max-width: 1023.98px) {
  .members-page {
    --members-chrome: calc(var(--header-height) + 40px + 52px);
    height: auto;
    max-height: none;
    overflow: visible;
  }

  .members-layout {
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .members-list {
    overflow-y: visible;
  }
}
</style>

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listMembers } from '@/api/members'

export const useMembersStore = defineStore('members', () => {
  const items = ref([])
  const loading = ref(false)

  async function fetchMembers() {
    loading.value = true
    try {
      const { data } = await listMembers()
      items.value = data
    } finally {
      loading.value = false
    }
  }

  function onPresenceEvent(memberId, event) {
    const member = items.value.find((m) => m.id === memberId)
    if (!member) return
    const now = new Date().toISOString()
    if (event === 'member_arrived') {
      member.is_home = true
      member.last_arrived_at = now
    } else if (event === 'member_left') {
      member.is_home = false
      member.last_left_at = now
    }
  }

  return { items, loading, fetchMembers, onPresenceEvent }
})

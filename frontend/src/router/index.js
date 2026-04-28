import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import MainLayout from '@/layout/MainLayout.vue'

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    redirect: '/devices',
    children: [
      { path: 'devices', component: () => import('@/views/DevicesView.vue') },
      { path: 'topology', component: () => import('@/views/TopologyView.vue') },
      { path: 'cameras', component: () => import('@/views/CameraView.vue') },
      { path: 'recordings', component: () => import('@/views/RecordingsView.vue') },
      { path: 'schedule', component: () => import('@/views/ScheduleView.vue') },
      { path: 'members', component: () => import('@/views/MembersView.vue') },
      { path: 'dlna', component: () => import('@/views/DLNAView.vue') },
      { path: 'settings', component: () => import('@/views/SettingsView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) return '/login'
})

export default router

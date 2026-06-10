import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import MainLayout from '@/layout/MainLayout.vue'

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/register', component: RegisterView, meta: { public: true } },
  {
    path: '/reset-password',
    component: () => import('@/views/ResetPasswordView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { titleKey: 'layout.dashboard' },
      },
      {
        path: 'devices',
        component: () => import('@/views/DevicesView.vue'),
        meta: { titleKey: 'layout.devices' },
      },
      {
        path: 'analytics',
        component: () => import('@/views/AnalyticsView.vue'),
        meta: { titleKey: 'layout.analytics' },
      },
      {
        path: 'topology',
        component: () => import('@/views/TopologyView.vue'),
        meta: { titleKey: 'layout.topology' },
      },
      {
        path: 'cameras',
        component: () => import('@/views/CameraView.vue'),
        meta: { titleKey: 'layout.cameras' },
      },
      {
        path: 'recordings',
        component: () => import('@/views/RecordingsView.vue'),
        meta: { titleKey: 'layout.recordings' },
      },
      {
        path: 'schedule',
        component: () => import('@/views/ScheduleView.vue'),
        meta: { titleKey: 'layout.schedule' },
      },
      {
        path: 'members',
        component: () => import('@/views/MembersView.vue'),
        meta: { titleKey: 'layout.members' },
      },
      {
        path: 'dlna',
        component: () => import('@/views/DLNAView.vue'),
        meta: { titleKey: 'layout.dlna' },
      },
      {
        path: 'settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { titleKey: 'layout.settings' },
      },
    ],
  },
  // Catch-all 404 route - must be registered LAST
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) return '/login'
})

export default router

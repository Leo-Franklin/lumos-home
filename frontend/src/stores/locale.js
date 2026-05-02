// src/stores/locale.js
import { defineStore } from 'pinia'
import i18n from '@/locales'
import api from '@/api'

export const useLocaleStore = defineStore('locale', {
  state: () => ({
    locale: localStorage.getItem('app-locale') || 'zh-CN',
  }),

  actions: {
    setLocale(lang) {
      this.locale = lang
      i18n.global.locale.value = lang
      localStorage.setItem('app-locale', lang)
      api.put('/user/profile', { language: lang }).catch(() => {})
    },

    async initLocale() {
      try {
        const { data } = await api.get('/user/profile')
        if (data.language && data.language !== this.locale) {
          this.setLocale(data.language)
        }
      } catch {
        // backend unavailable, use localStorage value
      }
    },
  },
})

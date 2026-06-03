<!-- src/App.vue -->
<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import { useLocaleStore } from '@/stores/locale'

const { locale } = useI18n()
const localeStore = useLocaleStore()

localeStore.initLocale()

const elLocale = computed(() => (locale.value === 'zh-CN' ? zhCn : en))
</script>

<template>
  <el-config-provider :locale="elLocale">
    <router-view />
  </el-config-provider>
</template>

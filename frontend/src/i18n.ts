import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

i18n.use(initReactI18next).init({
  resources: {
    'zh-CN': {
      translation: {
        nav: { desktop: '桌面', allApps: '所有应用', settings: '设置', account: '账号' },
        launcher: { search: '搜索应用', title: '所有应用' },
        apps: { fileManager: '文件管理', appStore: '应用商店', settings: '系统设置', storage: '存储管理', monitor: '资源监控', docker: 'Docker' },
      },
    },
    'en-US': {
      translation: {
        nav: { desktop: 'Desktop', allApps: 'All Apps', settings: 'Settings', account: 'Account' },
        launcher: { search: 'Search apps', title: 'All Apps' },
        apps: { fileManager: 'File Manager', appStore: 'App Store', settings: 'System Settings', storage: 'Storage', monitor: 'Resource Monitor', docker: 'Docker' },
      },
    },
  },
  lng: 'zh-CN',
  fallbackLng: 'zh-CN',
  interpolation: { escapeValue: false },
})

export default i18n

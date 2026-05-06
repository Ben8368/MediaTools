import { APP_ICON_PATHS } from '@/icon-library'

export type MediaToolsApp = {
  id: string
  label: string
  title: string
  icon: string
}

export const MEDIA_TOOLS_APPS: MediaToolsApp[] = [
  { id: 'fetcher', label: '下载', title: '下载', icon: APP_ICON_PATHS.fetcher },
  { id: 'agent', label: 'AI助手', title: 'AI助手', icon: APP_ICON_PATHS.agent },
  { id: 'ps', label: 'PS', title: 'Photoshop 自动化', icon: APP_ICON_PATHS.photoshop },
  { id: 'ae', label: 'AE', title: 'After Effects 自动化', icon: APP_ICON_PATHS.ae },
  { id: 'filebrowser', label: '文件管理', title: '文件管理', icon: APP_ICON_PATHS.filebrowser },
  { id: 'decryptor', label: '音乐解密', title: '音乐解密', icon: APP_ICON_PATHS.decryptor },
]

export const APP_TITLES = Object.fromEntries(MEDIA_TOOLS_APPS.map((app) => [app.id, app.title]))
export const APP_ICONS = Object.fromEntries(MEDIA_TOOLS_APPS.map((app) => [app.id, app.icon]))

// Titles for system windows not in the launcher
APP_TITLES['settings'] = '设置'

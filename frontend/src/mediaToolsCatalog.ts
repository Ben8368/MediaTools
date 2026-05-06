import { appRegistry, getLauncherApps } from '@/appRegistry'

export type MediaToolsApp = {
  id: string
  label: string
  title: string
  icon: string
}

export const MEDIA_TOOLS_APPS: MediaToolsApp[] = getLauncherApps().map((app) => ({
  id: app.id,
  label: app.label,
  title: app.title,
  icon: app.icon,
}))

export const APP_TITLES: Record<string, string> = Object.fromEntries(
  appRegistry.map((app) => [app.id, app.title]),
)

export const APP_ICONS: Record<string, string> = Object.fromEntries(
  appRegistry.map((app) => [app.id, app.icon]),
)

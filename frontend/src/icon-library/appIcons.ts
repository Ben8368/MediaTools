const BASE = '/static/app/icons/default'

export const APP_ICON_PATHS = {
  dashboard:  `${BASE}/resource-manager.png`,
  agent:      `${BASE}/ai.png`,
  fetcher:    `${BASE}/download-center.png`,
  assets:     `${BASE}/file-manager.png`,
  workbench:  `${BASE}/media.png`,
  encoder:    `${BASE}/virtual-machine.png`,
  decryptor:  `${BASE}/um.png`,
  photoshop:  `${BASE}/ps.png`,
  ps:         `${BASE}/ps.png`,
  auditor:    `${BASE}/log-center.png`,
  workspace:  `${BASE}/setting.png`,
  ae:         `${BASE}/ae.png`,
  filebrowser: `${BASE}/file-manager.png`,
  settings:    `${BASE}/setting.png`,
  logs:        `${BASE}/log-center.png`,
  browser:     `${BASE}/app-center.png`,
  chatgpt:     `${BASE}/app-center.png`,
} as const

export type AppId = keyof typeof APP_ICON_PATHS

export const FALLBACK_ICON = `${BASE}/setting.png`

export function getAppIcon(appId: string): string {
  return (APP_ICON_PATHS as Record<string, string>)[appId] ?? FALLBACK_ICON
}

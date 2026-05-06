import {
  AgentApp,
  AssetsApp,
  AuditorApp,
  DashboardApp,
  DecryptorApp,
  EncoderApp,
  PhotoshopApp,
  AEApp,
  WorkbenchApp,
  WorkspaceApp,
  FileManagerApp,
} from '@/apps/MediaToolsApps'
import { DownloaderApp } from '@/apps/DownloaderApp'
import { SettingsApp } from '@/apps/SettingsApp'
import { APP_TITLES } from '@/mediaToolsCatalog'
import { FnOSWindow } from '@/Window'
import { useWindowStore } from '@/windowStore'

const APP_MAP: Record<string, React.ComponentType> = {
  dashboard: DashboardApp,
  agent: AgentApp,
  fetcher: DownloaderApp,
  assets: AssetsApp,
  workbench: WorkbenchApp,
  encoder: EncoderApp,
  decryptor: DecryptorApp,
  ps: PhotoshopApp,
  ae: AEApp,
  photoshop: PhotoshopApp,
  auditor: AuditorApp,
  workspace: WorkspaceApp,
  filebrowser: FileManagerApp,
  settings: SettingsApp,
}

export function WindowContainer() {
  const { windows, closeWindow, minimizeWindow, maximizeWindow, focusWindow, dragWindow, resizeWindow } = useWindowStore()
  const maxZ = Math.max(0, ...windows.map((w) => w.zIndex))

  return (
    <div className="fnos-windows">
      {windows.map((w) => {
        const C = APP_MAP[w.appType]
        if (!C) return null
        return (
          <FnOSWindow
            key={w.id}
            windowId={w.id}
            title={APP_TITLES[w.appType] || w.title}
            width={w.width}
            height={w.height}
            x={w.x}
            y={w.y}
            isMaximized={w.isMaximized}
            isMinimized={w.isMinimized}
            isActive={w.zIndex === maxZ}
            zIndex={w.zIndex}
            appType={w.appType}
            onClose={closeWindow}
            onMinimize={minimizeWindow}
            onMaximize={maximizeWindow}
            onFocus={focusWindow}
            onDrag={dragWindow}
            onResize={resizeWindow}
          >
            <C />
          </FnOSWindow>
        )
      })}
    </div>
  )
}

import { useCallback, useEffect } from 'react'
import { LeftNavbar } from '@/LeftNavbar'
import { AppLauncher } from '@/AppLauncher'
import { WindowContainer } from '@/WindowContainer'
import { DesktopIcons } from '@/DesktopIcons'
import { RightPanel } from '@/RightPanel'
import { useWindowStore } from '@/windowStore'
import { useSystemStore } from '@/store'
import { useModelConfig } from '@/modelConfigStore'

export default function App() {
  const { openWindow } = useWindowStore()
  const { setShowLauncher, wallpaper } = useSystemStore()
  const loadModelConfig = useModelConfig((state) => state.loadConfig)

  const handleOpenApp = useCallback((id: string) => {
    openWindow(id)
    setShowLauncher(false)
  }, [openWindow, setShowLauncher])

  useEffect(() => {
    loadModelConfig()
  }, [loadModelConfig])

  useEffect(() => {
    document.documentElement.style.setProperty('--fnos-wp', `url('/static/bg/live/wallpaper-${wallpaper + 1}-dark.webp')`)
  }, [wallpaper])

  return (
    <div className="fnos-desktop">
      <LeftNavbar />
      <div className="fnos-main">
        <DesktopIcons onOpenApp={handleOpenApp} />
      </div>
      <WindowContainer />
      <AppLauncher onOpenApp={handleOpenApp} />
      <RightPanel />
    </div>
  )
}

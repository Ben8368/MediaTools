import { getRegisteredApp } from '@/appRegistry'
import { FnOSWindow } from '@/Window'
import { useWindowStore } from '@/windowStore'

export function WindowContainer() {
  const { windows, closeWindow, minimizeWindow, maximizeWindow, focusWindow, dragWindow, resizeWindow } = useWindowStore()
  const maxZ = Math.max(0, ...windows.map((w) => w.zIndex))

  return (
    <div className="fnos-windows">
      {windows.map((w) => {
        const registeredApp = getRegisteredApp(w.appType)
        if (!registeredApp) return null
        const C = registeredApp.component
        return (
          <FnOSWindow
            key={w.id}
            windowId={w.id}
            title={registeredApp.title || w.title}
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

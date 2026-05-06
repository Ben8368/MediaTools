import { type CSSProperties, useEffect, useRef, useState } from 'react'

import { getLauncherApps } from '@/appRegistry'

const ICON_ROW_HEIGHT = 86
const ICON_ROW_GAP = 28
const FALLBACK_ROWS = 6

function calculateRows(height: number) {
  if (!height) return FALLBACK_ROWS
  return Math.max(1, Math.floor((height + ICON_ROW_GAP) / (ICON_ROW_HEIGHT + ICON_ROW_GAP)))
}

export function DesktopIcons({ onOpenApp }: { onOpenApp: (id: string) => void }) {
  const gridRef = useRef<HTMLDivElement>(null)
  const [rows, setRows] = useState(FALLBACK_ROWS)

  useEffect(() => {
    const grid = gridRef.current
    if (!grid) return

    const updateRows = () => {
      const height = grid.clientHeight || grid.parentElement?.clientHeight || 0
      setRows(calculateRows(height))
    }

    updateRows()

    if (!window.ResizeObserver) {
      window.addEventListener('resize', updateRows)
      return () => window.removeEventListener('resize', updateRows)
    }

    const observer = new ResizeObserver(updateRows)
    observer.observe(grid)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={gridRef}
      className="icon-grid"
      style={{ '--desktop-icon-rows': rows } as CSSProperties}
    >
      {getLauncherApps().map((app) => (
        <div
          key={app.id}
          className={`app-icon app-icon--${app.id}`}
          onClick={() => onOpenApp(app.id)}
        >
          <div className="app-icon-img">
            <img src={app.icon} alt={app.label} />
          </div>
          <span className="app-icon-label">{app.label}</span>
        </div>
      ))}
    </div>
  )
}

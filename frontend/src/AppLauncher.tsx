import { useEffect, useRef, useState } from 'react'
import { getLauncherApps } from '@/appRegistry'
import { useSystemStore } from '@/store'

export function AppLauncher({ onOpenApp }: { onOpenApp: (id: string) => void }) {
  const { showLauncher, setShowLauncher } = useSystemStore()
  const [search, setSearch] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { if (showLauncher) inputRef.current?.focus() }, [showLauncher])
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') setShowLauncher(false) }
    window.addEventListener('keydown', h, true)
    return () => window.removeEventListener('keydown', h, true)
  }, [setShowLauncher])

  if (!showLauncher) return null

  const filtered = getLauncherApps().filter((app) => app.label.includes(search) || app.title.includes(search))

  return (
    <div className="fnos-launcher-overlay" onClick={() => setShowLauncher(false)}>
      <div className="fnos-launcher" onClick={(e) => e.stopPropagation()}>
        <div className="fnos-launcher-search">
          <input ref={inputRef} type="text" placeholder="搜索..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="fnos-launcher-grid">
          <div className="fnos-launcher-apps">
            {filtered.map((app) => (
              <div
                key={app.id}
                className="launcher-app"
                onClick={() => { onOpenApp(app.id); setShowLauncher(false) }}
              >
                <img src={app.icon} alt={app.label} />
                <span className="launcher-app-name">{app.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

import { shutdownSystem } from '@/api'
import { getAppIcon } from '@/icon-library'
import { useNotificationUnreadStore } from '@/notificationUnreadStore'
import { useSystemStore } from '@/store'
import { useWindowStore } from '@/windowStore'
import { useEffect, useState } from 'react'

export function LeftNavbar() {
  const { showLauncher, toggleLauncher } = useSystemStore()
  const windows = useWindowStore((state) => state.windows)
  const openWindow = useWindowStore((state) => state.openWindow)
  const minimizeWindow = useWindowStore((state) => state.minimizeWindow)
  const focusWindow = useWindowStore((state) => state.focusWindow)
  const unreadNotificationCount = useNotificationUnreadStore((s) => s.unreadNotificationCount)
  const pullUnreadNotificationCount = useNotificationUnreadStore((s) => s.pullUnreadNotificationCount)
  const [showPowerMenu, setShowPowerMenu] = useState(false)
  const [isShuttingDown, setIsShuttingDown] = useState(false)
  const [powerComplete, setPowerComplete] = useState<'shutdown' | null>(null)

  const uniqueRunningApps = windows.filter(
    (windowItem, index, allWindows) =>
      allWindows.findIndex((candidate) => candidate.appType === windowItem.appType) === index
  )

  useEffect(() => {
    void pullUnreadNotificationCount()
    const timer = window.setInterval(() => void pullUnreadNotificationCount(), 3000)
    return () => window.clearInterval(timer)
  }, [pullUnreadNotificationCount])

  function doClick(appType: string) {
    const existingWindow = windows.find((windowItem) => windowItem.appType === appType)
    if (!existingWindow) return

    if (existingWindow.isMinimized) {
      openWindow(appType)
      return
    }

    const topZIndex = Math.max(...windows.map((windowItem) => windowItem.zIndex))
    if (existingWindow.zIndex === topZIndex) {
      minimizeWindow(existingWindow.id)
      return
    }

    focusWindow(existingWindow.id)
  }

  async function doShutdown() {
    if (isShuttingDown) return
    if (!window.confirm('确认关闭 MediaTools 后端服务吗？')) return

    setIsShuttingDown(true)
    try {
      await shutdownSystem()
      setPowerComplete('shutdown')
    } catch (error: any) {
      window.alert(error?.message || '关闭失败，请稍后重试')
      setIsShuttingDown(false)
    }
  }

  if (powerComplete) {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'radial-gradient(circle at top, rgba(34,43,63,.96), rgba(10,12,16,.98))',
          color: 'white',
          zIndex: 9999,
          padding: 24,
        }}
      >
        <div
          style={{
            width: 'min(480px, 100%)',
            padding: '28px 24px',
            borderRadius: 18,
            border: '1px solid rgba(255,255,255,.08)',
            background: 'rgba(12,15,22,.92)',
            boxShadow: '0 24px 80px rgba(0,0,0,.35)',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 10 }}>
            MediaTools 已关闭
          </div>
          <div style={{ color: 'rgba(255,255,255,.72)', lineHeight: 1.6, marginBottom: 18 }}>
            后端服务已经停止。你可以直接关闭这个页面，或者在重新启动 MediaTools 后点击下面的按钮重新连接。
          </div>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              minWidth: 132,
              height: 40,
              borderRadius: 10,
              border: '1px solid rgba(255,255,255,.12)',
              background: 'rgba(255,255,255,.08)',
              color: 'white',
              cursor: 'pointer',
            }}
          >
            重新连接
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      style={{
        position: 'fixed',
        left: 8,
        top: 8,
        bottom: 8,
        width: 44,
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '10px 0 18px',
        background: 'rgba(10,12,16,.6)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        borderRadius: 10,
        border: '1px solid rgba(255,255,255,.04)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Btn icon={<IconMonitor />} tooltip="MediaTools" />
        <Btn icon={<IconGrid />} tooltip="所有应用" active={showLauncher} onClick={toggleLauncher} />
      </div>

      <div style={{ width: 22, height: 1, background: 'rgba(255,255,255,.06)', marginBottom: 12 }} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
        {uniqueRunningApps.map((windowItem) => {
          const topZIndex = Math.max(...windows.map((candidate) => candidate.zIndex))
          return (
            <button
              key={windowItem.id}
              onClick={() => doClick(windowItem.appType)}
              title={windowItem.title}
              className="sb-btn"
              style={{
                width: 36,
                height: 36,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: 'none',
                background: windowItem.zIndex === topZIndex ? 'rgba(255,255,255,.12)' : 'transparent',
                cursor: 'pointer',
                borderRadius: 6,
                transition: 'all .1s',
                flexShrink: 0,
              }}
            >
              <img src={getAppIcon(windowItem.appType)} width={22} height={22} style={{ objectFit: 'contain' }} alt={windowItem.title} />
            </button>
          )
        })}
      </div>

      <div style={{ width: 22, height: 1, background: 'rgba(255,255,255,.06)', marginTop: 12, marginBottom: 8 }} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
        <Btn icon={<IconGlobe />} tooltip="网络" />
        <div style={{ position: 'relative' }}>
          <Btn
            icon={<IconBell />}
            tooltip="日志"
            active={windows.some((item) => item.appType === 'logs' && !item.isMinimized)}
            onClick={() => {
              void pullUnreadNotificationCount()
              openWindow('logs')
            }}
          />
          {unreadNotificationCount > 0 && (
            <div
              style={{
                position: 'absolute',
                top: -4,
                right: -4,
                width: 18,
                height: 18,
                borderRadius: '50%',
                background: '#FF4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 'bold',
                color: 'white',
                border: '2px solid rgba(10,12,16,.6)',
              }}
            >
              {unreadNotificationCount > 99 ? '99+' : unreadNotificationCount}
            </div>
          )}
        </div>
        <Btn icon={<IconUser />} tooltip="账号" />
        <Btn icon={<IconGear />} tooltip="设置" onClick={() => openWindow('settings')} />
        <Btn
          ariaLabel="power-menu"
          icon={<IconPower />}
          tooltip={isShuttingDown ? '关闭中...' : '电源'}
          active={showPowerMenu}
          onClick={() => setShowPowerMenu((visible) => !visible)}
          disabled={isShuttingDown}
        />
      </div>
      {showPowerMenu && (
        <div
          style={{
            position: 'absolute',
            left: 52,
            bottom: 14,
            display: 'grid',
            gap: 6,
            width: 128,
            padding: 8,
            borderRadius: 12,
            border: '1px solid rgba(255,255,255,.10)',
            background: 'rgba(10,12,16,.94)',
            boxShadow: '0 18px 44px rgba(0,0,0,.34)',
          }}
        >
          <PowerMenuButton
            ariaLabel="shutdown-backend"
            icon={<IconPower />}
            label="关闭"
            onClick={() => {
              setShowPowerMenu(false)
              void doShutdown()
            }}
          />
        </div>
      )}
    </div>
  )
}

function PowerMenuButton({
  icon,
  label,
  onClick,
  ariaLabel,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  ariaLabel: string
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 9,
        minHeight: 34,
        border: 0,
        borderRadius: 8,
        background: 'transparent',
        color: 'rgba(255,255,255,.86)',
        cursor: 'pointer',
        padding: '0 10px',
        fontSize: 13,
        fontWeight: 700,
        textAlign: 'left',
      }}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

function Btn({
  icon,
  tooltip,
  active,
  onClick,
  disabled,
  ariaLabel,
}: {
  icon: React.ReactNode
  tooltip: string
  active?: boolean
  onClick?: () => void
  disabled?: boolean
  ariaLabel?: string
}) {
  return (
    <button
      onClick={onClick}
      title={tooltip}
      aria-label={ariaLabel}
      disabled={disabled}
      style={{
        width: 36,
        height: 36,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: 'none',
        background: active ? 'rgba(255,255,255,.1)' : 'transparent',
        color: active ? 'white' : 'rgba(255,255,255,.6)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        borderRadius: 6,
        transition: 'all .1s',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {icon}
    </button>
  )
}

const IconMonitor = () => <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="3" width="18" height="13" rx="2" /><path d="M8 19h8M12 16v3" /></svg>
const IconGrid = () => <svg viewBox="0 0 20 20" width={18} height={18}><circle cx="3.5" cy="3.5" r="2" fill="#6B9DFF" /><circle cx="10" cy="3.5" r="2" fill="#54D2E6" /><circle cx="16.5" cy="3.5" r="2" fill="#F59B5E" /><circle cx="3.5" cy="10" r="2" fill="#A78BFA" /><circle cx="10" cy="10" r="2" fill="#A78BFA" /><circle cx="16.5" cy="10" r="2" fill="#F59B5E" /><circle cx="3.5" cy="16.5" r="2" fill="#6B9DFF" /><circle cx="10" cy="16.5" r="2" fill="#54D2E6" /><circle cx="16.5" cy="16.5" r="2" fill="#F59B5E" /></svg>
const IconGlobe = () => <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="10" /><path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" /></svg>
const IconBell = () => <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" /></svg>
const IconUser = () => <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="7" r="4" /><path d="M5.5 21a6.5 6.5 0 0113 0" /></svg>
const IconGear = () => <svg viewBox="0 0 24 24" width={16} height={16} fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 15a3 3 0 100-6 3 3 0 000 6z"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
const IconPower = () => <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 2v10" /><path d="M18.4 5.6a9 9 0 11-12.8 0" /></svg>

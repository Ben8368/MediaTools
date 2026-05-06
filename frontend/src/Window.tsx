import { useCallback, useRef } from 'react'
import { WINDOW_CHROME } from '@/appPresentation'
import { getAppIcon } from '@/icon-library'

export function FnOSWindow({
  windowId, title, width = 900, height = 600,
  x: ix = 80, y: iy = 80,
  isMaximized, isMinimized, isActive, zIndex,
  appType,
  children, onClose, onMinimize, onMaximize, onFocus, onDrag, onResize,
}: {
  windowId: string; title: string; width?: number; height?: number; x?: number; y?: number;
  isMaximized: boolean; isMinimized: boolean; isActive: boolean; zIndex: number; appType?: string;
  children: React.ReactNode;
  onClose: (id: string) => void; onMinimize: (id: string) => void; onMaximize: (id: string) => void;
  onFocus: (id: string) => void; onDrag: (id: string, x: number, y: number) => void;
  onResize: (id: string, width: number, height: number) => void;
}) {
  const dragS = useRef({ cx: 0, cy: 0, wx: 0, wy: 0 })
  const resizeS = useRef({ cx: 0, cy: 0, ww: 0, wh: 0, wx: 0, wy: 0, dir: '' })

  const startDrag = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.wc') || isMaximized) return
    onFocus(windowId)
    dragS.current = { cx: e.clientX, cy: e.clientY, wx: ix, wy: iy }
    const mm = (e: MouseEvent) => onDrag(
      windowId,
      dragS.current.wx + (e.clientX - dragS.current.cx),
      Math.max(WINDOW_CHROME.minTop, dragS.current.wy + (e.clientY - dragS.current.cy)),
    )
    const mu = () => { document.removeEventListener('mousemove', mm); document.removeEventListener('mouseup', mu) }
    document.addEventListener('mousemove', mm)
    document.addEventListener('mouseup', mu)
  }, [windowId, ix, iy, isMaximized, onFocus, onDrag])

  const startResize = useCallback((e: React.MouseEvent, direction: string) => {
    if (isMaximized) return
    e.stopPropagation()
    e.preventDefault()
    onFocus(windowId)
    resizeS.current = { cx: e.clientX, cy: e.clientY, ww: width, wh: height, wx: ix, wy: iy, dir: direction }

    document.body.style.userSelect = 'none'

    const mm = (e: MouseEvent) => {
      const dx = e.clientX - resizeS.current.cx
      const dy = e.clientY - resizeS.current.cy
      let nw = resizeS.current.ww
      let nh = resizeS.current.wh
      let nx = resizeS.current.wx
      let ny = resizeS.current.wy

      if (direction.includes('e')) nw = Math.max(WINDOW_CHROME.minWidth, resizeS.current.ww + dx)
      if (direction.includes('w')) {
        nw = Math.max(WINDOW_CHROME.minWidth, resizeS.current.ww - dx)
        nx = resizeS.current.wx + (resizeS.current.ww - nw)
      }
      if (direction.includes('s')) nh = Math.max(WINDOW_CHROME.minHeight, resizeS.current.wh + dy)
      if (direction.includes('n')) {
        nh = Math.max(WINDOW_CHROME.minHeight, resizeS.current.wh - dy)
        ny = resizeS.current.wy + (resizeS.current.wh - nh)
      }

      onResize(windowId, nw, nh)
      if (nx !== resizeS.current.wx || ny !== resizeS.current.wy) {
        onDrag(windowId, nx, ny)
      }
    }
    const mu = () => {
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', mm)
      document.removeEventListener('mouseup', mu)
    }
    document.addEventListener('mousemove', mm)
    document.addEventListener('mouseup', mu)
  }, [windowId, width, height, ix, iy, isMaximized, onFocus, onResize, onDrag])

  if (isMinimized) return null

  const w = isMaximized ? '100%' : width
  const h = isMaximized ? '100%' : height
  const minLeft = typeof width === 'number' ? -Math.max(0, width - WINDOW_CHROME.offscreenGutter) : -800
  const left = isMaximized ? 0 : Math.max(minLeft, ix)
  const top = isMaximized ? 0 : Math.max(WINDOW_CHROME.minTop, iy)

  const activeIcon = getAppIcon(appType ?? '')

  return (
    <div
      className={`fnos-window ${isActive ? 'fnos-window--active' : ''} ${isMaximized ? 'fnos-window--maximized' : ''}`}
      style={{ width: w, height: h, left, top, zIndex }}
      onMouseDown={() => onFocus(windowId)}
    >
      <div className="fnos-window-header" onMouseDown={startDrag} onDoubleClick={() => onMaximize(windowId)}>
        <div className="fnos-window-brand">
          {activeIcon && <img src={activeIcon} alt="" />}
          <strong>{title}</strong>
        </div>
        <div className="fnos-window-controls wc">
          <button className="fnos-window-btn fnos-window-btn--min" title="最小化" onClick={(e) => { e.stopPropagation(); onMinimize(windowId) }}>
            <svg viewBox="0 0 24 24"><path d="M5 12h14" /></svg>
          </button>
          <button className="fnos-window-btn fnos-window-btn--max" title="最大化" onClick={(e) => { e.stopPropagation(); onMaximize(windowId) }}>
            <svg viewBox="0 0 24 24"><rect x="6" y="5" width="12" height="14" rx="1.5" /></svg>
          </button>
          <button className="fnos-window-btn fnos-window-btn--close" title="关闭" onClick={(e) => { e.stopPropagation(); onClose(windowId) }}>
            <svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg>
          </button>
        </div>
      </div>
      <div className="fnos-window-body">{children}</div>
      {!isMaximized && (
        <>
          <div className="fnos-resize-handle fnos-resize-n" onMouseDown={(e) => startResize(e, 'n')} />
          <div className="fnos-resize-handle fnos-resize-s" onMouseDown={(e) => startResize(e, 's')} />
          <div className="fnos-resize-handle fnos-resize-w" onMouseDown={(e) => startResize(e, 'w')} />
          <div className="fnos-resize-handle fnos-resize-e" onMouseDown={(e) => startResize(e, 'e')} />
          <div className="fnos-resize-handle fnos-resize-nw" onMouseDown={(e) => startResize(e, 'nw')} />
          <div className="fnos-resize-handle fnos-resize-ne" onMouseDown={(e) => startResize(e, 'ne')} />
          <div className="fnos-resize-handle fnos-resize-sw" onMouseDown={(e) => startResize(e, 'sw')} />
          <div className="fnos-resize-handle fnos-resize-se" onMouseDown={(e) => startResize(e, 'se')} />
        </>
      )}
    </div>
  )
}

import { useEffect, useRef, useState, useCallback } from 'react'

type BrowserAppProps = {
  windowId?: string
  initialUrl?: string
}

type SessionState = 'idle' | 'starting' | 'running' | 'error'

function detectBrowser(): 'chrome' | 'edge' {
  const ua = navigator.userAgent
  if (ua.includes('Edg/')) return 'edge'
  return 'chrome'
}

const BROWSER_LABELS = { chrome: 'Chrome', edge: 'Edge' }

export function BrowserApp({ windowId: _windowId, initialUrl = 'https://chatgpt.com' }: BrowserAppProps = {}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [sessionState, setSessionState] = useState<SessionState>('idle')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [cdpPort, setCdpPort] = useState<number | null>(null)
  const [browserType, setBrowserType] = useState<'chrome' | 'edge'>('chrome')
  const [detectedBrowser, setDetectedBrowser] = useState<'chrome' | 'edge'>(detectBrowser())
  const [cookies, setCookies] = useState<any[]>([])
  const [statusText, setStatusText] = useState('')

  const wsRef = useRef<WebSocket | null>(null)
  const intervalRef = useRef<number | null>(null)

  const startSession = useCallback(async () => {
    setSessionState('starting')
    setStatusText(`正在启动 ${BROWSER_LABELS[detectedBrowser]} 浏览器...`)

    try {
      const resp = await fetch('/api/browser/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: initialUrl, browser_type: detectedBrowser }),
      })

      const data = await resp.json()
      if (!data.ok) {
        throw new Error(data.error || 'Failed to create session')
      }

      const bt = data.browser_type as 'chrome' | 'edge'
      setSessionId(data.session_id)
      setCdpPort(data.cdp_port)
      setBrowserType(bt)
      setSessionState('running')
      setStatusText(`${BROWSER_LABELS[bt]} 已启动，正在加载页面...`)
    } catch (err: any) {
      setSessionState('error')
      setStatusText(`启动失败: ${err.message}`)
    }
  }, [initialUrl, detectedBrowser])

  const fetchScreenshot = useCallback(async () => {
    if (!cdpPort) return
    
    try {
      const resp = await fetch(`http://127.0.0.1:${cdpPort}/json/list`)
      const targets = await resp.json()
      const pageTarget = targets.find((t: any) => t.type === 'page')
      
      if (!pageTarget) return
      
      const wsUrl = pageTarget.webSocketDebuggerUrl
      
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        wsRef.current = new WebSocket(wsUrl)
        
        wsRef.current.onopen = () => {
          setStatusText('已连接到浏览器')
        }
        
        wsRef.current.onmessage = (event) => {
          const msg = JSON.parse(event.data)
          if (msg.result && msg.result.data) {
            const canvas = canvasRef.current
            if (!canvas) return
            
            const ctx = canvas.getContext('2d')
            if (!ctx) return
            
            const img = new Image()
            img.onload = () => {
              canvas.width = img.width
              canvas.height = img.height
              ctx.drawImage(img, 0, 0)
            }
            img.src = `data:image/jpeg;base64,${msg.result.data}`
          }
        }
      }
      
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          id: Date.now(),
          method: 'Page.captureScreenshot',
          params: { format: 'jpeg', quality: 80 }
        }))
      }
    } catch (err) {
      console.error('Screenshot error:', err)
    }
  }, [cdpPort])

  const fetchCookies = useCallback(async () => {
    if (!sessionId) return
    
    try {
      const resp = await fetch(`/api/browser/session/${sessionId}/cookies`)
      const data = await resp.json()
      if (data.ok) {
        setCookies(data.cookies)
        setStatusText(`已获取 ${data.cookie_count} 个 cookies`)
      }
    } catch (err: any) {
      console.error('Failed to fetch cookies:', err)
    }
  }, [sessionId])

  const handleCanvasClick = useCallback((e: React.MouseEvent) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    
    const canvas = canvasRef.current
    if (!canvas) return
    
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) * (canvas.width / rect.width)
    const y = (e.clientY - rect.top) * (canvas.height / rect.height)
    
    wsRef.current.send(JSON.stringify({
      id: Date.now(),
      method: 'Input.dispatchMouseEvent',
      params: {
        type: 'mousePressed',
        x,
        y,
        button: 'left',
        clickCount: 1
      }
    }))
    
    wsRef.current.send(JSON.stringify({
      id: Date.now() + 1,
      method: 'Input.dispatchMouseEvent',
      params: {
        type: 'mouseReleased',
        x,
        y,
        button: 'left',
        clickCount: 1
      }
    }))
  }, [])

  useEffect(() => {
    if (sessionState === 'running' && cdpPort) {
      intervalRef.current = window.setInterval(fetchScreenshot, 500)
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [sessionState, cdpPort, fetchScreenshot])

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return (
    <div className="browser-app" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="browser-toolbar" style={{ padding: '8px', borderBottom: '1px solid #333', display: 'flex', gap: '8px', alignItems: 'center' }}>
        <button
          onClick={startSession}
          disabled={sessionState === 'starting'}
          style={{ padding: '4px 12px', cursor: sessionState === 'starting' ? 'not-allowed' : 'pointer' }}
        >
          {sessionState === 'starting' ? '启动中...' : `启动 ${BROWSER_LABELS[detectedBrowser]}`}
        </button>

        {detectedBrowser === 'chrome' && sessionState === 'idle' && (
          <button onClick={() => setDetectedBrowser('edge')} style={{ padding: '4px 12px' }}>
            使用 Edge
          </button>
        )}
        {detectedBrowser === 'edge' && sessionState === 'idle' && (
          <button onClick={() => setDetectedBrowser('chrome')} style={{ padding: '4px 12px' }}>
            使用 Chrome
          </button>
        )}

        {sessionState === 'running' && (
          <>
            <button onClick={fetchCookies} style={{ padding: '4px 12px' }}>
              获取 Cookies
            </button>
            <span style={{ fontSize: '12px', color: '#888' }}>
              {BROWSER_LABELS[browserType]} · {statusText}
            </span>
          </>
        )}

        {sessionState === 'error' && (
          <span style={{ fontSize: '12px', color: '#f44' }}>{statusText}</span>
        )}
      </div>
      
      <div className="browser-content" style={{ flex: 1, position: 'relative', overflow: 'hidden', background: '#111' }}>
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          style={{ width: '100%', height: '100%', cursor: sessionState === 'running' ? 'pointer' : 'default' }}
        />
        
        {sessionState === 'idle' && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p style={{ color: '#888' }}>点击「启动 {BROWSER_LABELS[detectedBrowser]}」开始</p>
          </div>
        )}
      </div>
      
      {cookies.length > 0 && (
        <div className="browser-cookies" style={{ maxHeight: '150px', overflow: 'auto', padding: '8px', borderTop: '1px solid #333', fontSize: '12px' }}>
          <details>
            <summary style={{ cursor: 'pointer' }}>Cookies ({cookies.length})</summary>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {JSON.stringify(cookies, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  )
}

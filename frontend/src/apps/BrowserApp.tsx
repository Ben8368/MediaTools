import { useEffect, useRef, useState, useCallback } from 'react'

type BrowserAppProps = {
  windowId?: string
  initialUrl?: string
}

type SessionState = 'idle' | 'starting' | 'running' | 'error'
type BrowserType = 'chrome' | 'edge' | 'firefox'
type SupportedBrowserType = Exclude<BrowserType, 'firefox'>

type BrowserOption = {
  type: BrowserType
  label: string
  accent: string
  supported: boolean
}

type BrowserMonitorState = {
  browser_type: SupportedBrowserType
  installed: boolean
  connected: boolean
  cdp_connected: boolean
  supported: boolean
  cdp_port: number
}

function detectBrowser(): SupportedBrowserType {
  const ua = navigator.userAgent
  if (ua.includes('Edg/')) return 'edge'
  return 'chrome'
}

const BROWSER_LABELS: Record<BrowserType, string> = { chrome: 'Chrome', edge: 'Edge', firefox: 'Firefox' }

const BROWSER_OPTIONS: BrowserOption[] = [
  { type: 'chrome', label: 'Chrome', accent: '#4dabff', supported: true },
  { type: 'edge', label: 'Edge', accent: '#38d9a9', supported: true },
  { type: 'firefox', label: 'Firefox', accent: '#ff9f43', supported: false },
]

function normalizeUrl(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return 'https://chatgpt.com'
  if (/^https?:\/\//i.test(trimmed)) return trimmed
  return `https://${trimmed}`
}

export function BrowserApp({ windowId: _windowId, initialUrl = 'https://chatgpt.com' }: BrowserAppProps = {}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [sessionState, setSessionState] = useState<SessionState>('idle')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [cdpPort, setCdpPort] = useState<number | null>(null)
  const [browserType, setBrowserType] = useState<BrowserType>('chrome')
  const [selectedBrowser, setSelectedBrowser] = useState<BrowserType>(detectBrowser())
  const [addressUrl, setAddressUrl] = useState(initialUrl)
  const [browserStatuses, setBrowserStatuses] = useState<BrowserMonitorState[]>([])
  const [cookies, setCookies] = useState<any[]>([])
  const [statusText, setStatusText] = useState('')

  const wsRef = useRef<WebSocket | null>(null)
  const intervalRef = useRef<number | null>(null)
  const pendingNavigationRef = useRef<string | null>(null)

  const fetchBrowserStatuses = useCallback(async () => {
    try {
      const resp = await fetch('/api/browser/status')
      const data = await resp.json()
      if (data.ok && Array.isArray(data.browsers)) {
        setBrowserStatuses(data.browsers)
      }
    } catch (err) {
      console.error('Failed to fetch browser status:', err)
    }
  }, [])

  const getBrowserMonitor = useCallback((type: BrowserType) => {
    if (type === 'firefox') {
      return { label: '未接入', detail: '暂不支持控制', tone: 'offline' }
    }
    if (browserStatuses.length === 0) {
      return { label: '检测中', detail: '读取安装状态', tone: 'pending' }
    }
    const status = browserStatuses.find((item) => item.browser_type === type)
    if (status?.connected || (sessionState === 'running' && browserType === type)) {
      return { label: '已连接', detail: `CDP ${status?.cdp_port || cdpPort || 9222}`, tone: 'online' }
    }
    if (status?.installed) {
      return { label: '可启动', detail: status.cdp_connected ? '调试端口可用' : '等待启动', tone: 'ready' }
    }
    return { label: '未安装', detail: '未找到程序', tone: 'offline' }
  }, [browserStatuses, browserType, cdpPort, sessionState])

  const sendCdpCommand = useCallback((method: string, params: Record<string, unknown> = {}) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return false
    wsRef.current.send(JSON.stringify({ id: Date.now(), method, params }))
    return true
  }, [])

  const startSession = useCallback(async (launchUrl?: string) => {
    const targetUrl = normalizeUrl(launchUrl || addressUrl || initialUrl)
    if (selectedBrowser === 'firefox') {
      setSessionState('error')
      setStatusText('Firefox 暂未接入后端控制，请选择 Chrome 或 Edge')
      return
    }

    setAddressUrl(targetUrl)
    setSessionState('starting')
    setStatusText(`正在启动 ${BROWSER_LABELS[selectedBrowser]} 浏览器...`)

    try {
      const resp = await fetch('/api/browser/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: targetUrl, browser_type: selectedBrowser }),
      })

      const data = await resp.json()
      if (!data.ok) {
        throw new Error(data.error || 'Failed to create session')
      }

      const bt = data.browser_type as SupportedBrowserType
      setSessionId(data.session_id)
      setCdpPort(data.cdp_port)
      setBrowserType(bt)
      setSessionState('running')
      setStatusText(`${BROWSER_LABELS[bt]} 已连接，正在加载 ${targetUrl}`)
      void fetchBrowserStatuses()
    } catch (err: any) {
      setSessionState('error')
      setStatusText(`启动失败: ${err.message}`)
    }
  }, [addressUrl, fetchBrowserStatuses, initialUrl, selectedBrowser])

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
          if (pendingNavigationRef.current) {
            wsRef.current?.send(JSON.stringify({
              id: Date.now(),
              method: 'Page.navigate',
              params: { url: pendingNavigationRef.current },
            }))
            pendingNavigationRef.current = null
          }
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

  const handleNavigate = useCallback((event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const targetUrl = normalizeUrl(addressUrl)
    setAddressUrl(targetUrl)

    if (sessionState !== 'running') {
      void startSession(targetUrl)
      return
    }

    pendingNavigationRef.current = targetUrl
    if (sendCdpCommand('Page.navigate', { url: targetUrl })) {
      pendingNavigationRef.current = null
      setStatusText(`正在打开 ${targetUrl}`)
    } else {
      setStatusText('正在连接浏览器控制通道...')
      void fetchScreenshot()
    }
  }, [addressUrl, fetchScreenshot, sendCdpCommand, sessionState, startSession])

  const primaryActionLabel = (() => {
    if (sessionState === 'starting') return '启动中...'
    if (selectedBrowser === 'firefox') return '未接入'
    if (sessionState === 'running') return '前往'
    return '启动'
  })()

  const selectedMonitor = getBrowserMonitor(selectedBrowser)

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
    void fetchBrowserStatuses()
    const timer = window.setInterval(fetchBrowserStatuses, 5000)
    return () => clearInterval(timer)
  }, [fetchBrowserStatuses])

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return (
    <div className="browser-app">
      <aside className="browser-sidebar">
        <nav className="browser-type-list" aria-label="浏览器类型">
          {BROWSER_OPTIONS.map((option) => {
            const monitor = getBrowserMonitor(option.type)
            return (
              <button
                key={option.type}
                className={`browser-type browser-type--${monitor.tone} ${selectedBrowser === option.type ? 'browser-type--active' : ''} ${!option.supported ? 'browser-type--disabled' : ''}`}
                onClick={() => {
                  setSelectedBrowser(option.type)
                  if (!option.supported) setStatusText('Firefox 暂未接入后端控制，请选择 Chrome 或 Edge')
                }}
                disabled={sessionState === 'starting'}
                style={{ '--browser-accent': option.accent } as React.CSSProperties}
              >
                <span className="browser-type__icon">{option.label.slice(0, 1)}</span>
                <span className="browser-type__text">
                  <strong>{option.label}</strong>
                </span>
              </button>
            )
          })}
        </nav>

        <div className="browser-sidebar-card">
          <span>用途</span>
          <p>打开目标网站并完成登录后，点击“获取 Cookies”即可读取当前浏览器会话的登录态。</p>
        </div>
      </aside>

      <main className="browser-panel">
        <header className="browser-commandbar">
          <form className="browser-nav-form" onSubmit={handleNavigate}>
            <label className="browser-addressbar">
              <span className={`browser-addressbar__monitor browser-addressbar__monitor--${selectedMonitor.tone}`} title={selectedMonitor.detail}>
                <i />
                {selectedMonitor.label}
              </span>
              <input
                value={addressUrl}
                onChange={(event) => setAddressUrl(event.target.value)}
                placeholder="输入网址，例如 youtube.com、chatgpt.com"
                spellCheck={false}
              />
            </label>
            <button className="browser-primary" type="submit" disabled={sessionState === 'starting' || selectedBrowser === 'firefox'}>
              {primaryActionLabel}
            </button>
          </form>

          <button className="dl-btn" onClick={fetchCookies} disabled={!sessionId || sessionState !== 'running'}>
            获取 Cookies
          </button>
        </header>

        <div className={`browser-status browser-status--${sessionState}`}>
          <span>{sessionState === 'running' ? `${BROWSER_LABELS[browserType]} · ` : ''}{statusText || '选择左侧浏览器类型，输入网址后启动会话'}</span>
        </div>

        <section className="browser-stage">
          <div className="browser-frame">
            <canvas
              ref={canvasRef}
              onClick={handleCanvasClick}
              className="browser-canvas"
            />

            {sessionState !== 'running' && (
              <div className="browser-empty">
                <div className="browser-empty__mark">URL</div>
                <strong>像浏览器一样打开目标网站</strong>
                <p>保留系统浏览器中的账号、插件和会话，用于获取其他网址的登录态。</p>
              </div>
            )}
          </div>
        </section>

        {cookies.length > 0 && (
          <details className="browser-cookies">
            <summary>Cookies ({cookies.length})</summary>
            <pre>{JSON.stringify(cookies, null, 2)}</pre>
          </details>
        )}
      </main>
    </div>
  )
}

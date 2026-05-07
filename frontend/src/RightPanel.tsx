import { useEffect, useMemo, useState } from 'react'
import { cancelTask, getSystemMetrics } from '@/api'

type RuntimeMetrics = {
  runtime?: { uptime_seconds?: number }
  system?: {
    cpu_percent?: number
    memory_percent?: number
    gpu_video_encode_percent?: number
    gpu_video_encode_available?: boolean
    gpu_video_encode_detail?: string
  }
  network?: {
    upload?: { text?: string }
    download?: { text?: string }
    upload_bytes_per_sec?: number
    download_bytes_per_sec?: number
  }
  services?: Array<{
    id: string
    name: string
    online: boolean
    status: string
    runtime_status?: string
    availability_status?: string
    mode?: string
    mode_label?: string
    detail?: string
    dep?: string | null
    experimental?: boolean
  }>
  tasks?: Array<{
    id: string
    name: string
    source?: string
    type: string
    status: string
    status_label?: string
    stage: string
    progress: number
    can_pause?: boolean
    can_resume?: boolean
    can_cancel?: boolean
  }>
  task_summary?: {
    active_downloads?: number
    total_download_records?: number
    terminal_download_records?: number
  }
  log_mode?: string
}

const EMPTY_METRICS: RuntimeMetrics = {
  runtime: { uptime_seconds: 0 },
  system: { cpu_percent: 0, memory_percent: 0, gpu_video_encode_percent: 0, gpu_video_encode_available: false },
  network: { upload: { text: '0 B/s' }, download: { text: '0 B/s' }, upload_bytes_per_sec: 0, download_bytes_per_sec: 0 },
  services: [],
  tasks: [],
}

function clampPercent(value: number | undefined) {
  return Math.max(0, Math.min(Number(value || 0), 100))
}

function formatUptime(totalSeconds = 0) {
  const d = Math.floor(totalSeconds / 86400)
  const h = Math.floor((totalSeconds % 86400) / 3600)
  const m = Math.floor((totalSeconds % 3600) / 60)
  const s = Math.floor(totalSeconds % 60)
  return `${d}天${h}时${m}分${s}秒`
}

function serviceTitle(service: NonNullable<RuntimeMetrics['services']>[number]) {
  return [service.id, service.detail || service.dep || service.status].filter(Boolean).join(' · ')
}

function serviceName(service: NonNullable<RuntimeMetrics['services']>[number]) {
  return service.id || service.name
}

function normalizeServices(services: NonNullable<RuntimeMetrics['services']>) {
  const visibleIds = new Set(['fetcher', 'encoder', 'decryptor', 'photoshop', 'auditor', 'wechat_moments'])
  return services
    .filter((service) => service.id !== 'frontend')
    .map((service) => (service.id === 'wechat' ? { ...service, id: 'wechat_moments' } : service))
    .filter((service) => visibleIds.has(service.id))
}

function frontendModeLabel(logMode?: string) {
  if (logMode === 'development') return '开发模式'
  return ''
}

function taskStatusClass(status: string) {
  if (status === 'running') return 'rp-task-status--running'
  if (status === 'pending') return 'rp-task-status--pending'
  if (status === 'paused') return 'rp-task-status--paused'
  return ''
}

function summarizeGroupStatuses(
  tasks: NonNullable<RuntimeMetrics['tasks']>,
) {
  const counts = new Map<string, number>()
  tasks.forEach((task) => {
    const label = task.status_label || task.status
    counts.set(label, (counts.get(label) || 0) + 1)
  })
  return Array.from(counts.entries())
    .map(([label, count]) => `${count} ${label}`)
    .join(' / ')
}

function appTypeForTaskGroup(type: string, label: string) {
  const text = `${type} ${label}`.toLowerCase()
  if (text.includes('decrypt') || text.includes('解密') || text.includes('audio')) return 'decryptor'
  if (text.includes('download') || text.includes('下载')) return 'fetcher'
  return ''
}

export function RightPanel() {
  const [metrics, setMetrics] = useState<RuntimeMetrics>(EMPTY_METRICS)
  const [netUpData, setNetUpData] = useState<number[]>(Array.from({ length: 40 }, () => 0))
  const [netDownData, setNetDownData] = useState<number[]>(Array.from({ length: 40 }, () => 0))
  const [error, setError] = useState('')
  const [expandedTaskType, setExpandedTaskType] = useState<string | null>(null)
  const [servicesExpanded, setServicesExpanded] = useState(false)

  async function refresh() {
    try {
      const data = await getSystemMetrics()
      setMetrics(data)
      setError('')
      setNetUpData((items) => [...items.slice(1), Number(data.network?.upload_bytes_per_sec || 0)])
      setNetDownData((items) => [...items.slice(1), Number(data.network?.download_bytes_per_sec || 0)])
    } catch (err: any) {
      setError(err?.message || '监控数据读取失败')
    }
  }

  async function handleTaskAction(action: 'cancel', taskId: string) {
    try {
      if (action === 'cancel') await cancelTask(taskId)
      await refresh()
    } catch (err: any) {
      setError(err?.message || '任务操作失败')
    }
  }

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(), 2000)
    return () => window.clearInterval(timer)
  }, [])

  function GaugeSvg({ value, color, label, title }: { value: number; color: string; label: string; title?: string }) {
    const r = 24, cx = 28, cy = 28
    const circ = 2 * Math.PI * r
    const offset = circ - (clampPercent(value) / 100) * circ
    return (
      <div className="rp-gauge" title={title}>
        <svg viewBox="0 0 56 56" style={{ shapeRendering: 'geometricPrecision' }}>
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,.06)" strokeWidth="4" />
          <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="5" strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={offset} transform={`rotate(-90 ${cx} ${cy})`}
            style={{ transition: 'stroke-dashoffset 0.3s ease', paintOrder: 'stroke' }} />
          <text x={cx} y={cy - 4} textAnchor="middle" fill="rgba(255,255,255,.55)" fontSize="8.5" fontWeight="500">{label}</text>
          <text x={cx} y={cy + 7} textAnchor="middle" fill="rgba(255,255,255,.92)" fontSize="9" fontWeight="600">{Math.round(clampPercent(value))}%</text>
        </svg>
      </div>
    )
  }

  function DualLineChart({ dataUp, dataDown }: { dataUp: number[]; dataDown: number[] }) {
    const max = Math.max(...dataUp, ...dataDown, 1)
    const w = 280, h = 36
    const up = dataUp.map((p, i) => `${i === 0 ? 'M' : 'L'}${(i / (dataUp.length - 1)) * w},${h - 4 - (p / max) * (h - 8)}`).join(' ')
    const down = dataDown.map((p, i) => `${i === 0 ? 'M' : 'L'}${(i / (dataDown.length - 1)) * w},${h - 4 - (p / max) * (h - 8)}`).join(' ')
    return (
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: '100%', height: h }}>
        <defs>
          <linearGradient id="dup" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#54FFB7" stopOpacity=".25" />
            <stop offset="100%" stopColor="#54FFB7" stopOpacity=".02" />
          </linearGradient>
          <linearGradient id="ddn" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4AA3FF" stopOpacity=".25" />
            <stop offset="100%" stopColor="#4AA3FF" stopOpacity=".02" />
          </linearGradient>
        </defs>
        <path d={`${down} L${w},${h} L0,${h} Z`} fill="url(#ddn)" />
        <path d={down} fill="none" stroke="#4AA3FF" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
        <path d={`${up} L${w},${h} L0,${h} Z`} fill="url(#dup)" />
        <path d={up} fill="none" stroke="#54FFB7" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
      </svg>
    )
  }

  const system = metrics.system || EMPTY_METRICS.system!
  const network = metrics.network || EMPTY_METRICS.network!
  const services = useMemo(() => normalizeServices(metrics.services || []), [metrics.services])
  const tasks = metrics.tasks || []
  const taskSummary = metrics.task_summary
  const groupedTasks = useMemo(() => {
    const groups = new Map<string, { type: string; label: string; tasks: NonNullable<RuntimeMetrics['tasks']>; progress: number; statusSummary: string }>()
    tasks.forEach((task) => {
      const key = task.type || 'unknown'
      if (!groups.has(key)) {
        groups.set(key, { type: key, label: task.name || key, tasks: [], progress: 0, statusSummary: '' })
      }
      groups.get(key)!.tasks.push(task)
    })
    return Array.from(groups.values()).map((group) => {
      const progress = group.tasks.reduce((sum, task) => sum + clampPercent(task.progress), 0) / Math.max(group.tasks.length, 1)
      return {
        ...group,
        progress,
        statusSummary: summarizeGroupStatuses(group.tasks),
      }
    })
  }, [tasks])
  const expandedGroup = groupedTasks.find((group) => group.type === expandedTaskType) || null

  return (
    <div className="fnos-right-panel">
      <div className="rp-card">
        <div className="rp-card-head rp-runtime-head">
          <div className="rp-card-title">运行状态</div>
        </div>
        <div className="rp-gauges">
          <GaugeSvg value={system.cpu_percent || 0} color="#7CB3FF" label="CPU" />
          <GaugeSvg value={system.memory_percent || 0} color="#7CB3FF" label="内存" />
          <GaugeSvg
            value={system.gpu_video_encode_percent || 0}
            color={system.gpu_video_encode_available ? '#7CB3FF' : '#64748b'}
            label="GPU"
            title={system.gpu_video_encode_detail}
          />
        </div>
        <div className="rp-uptime">
          <span>本次运行 <span>{formatUptime(metrics.runtime?.uptime_seconds || 0)}</span></span>
          {frontendModeLabel(metrics.log_mode) && <span className="rp-runtime-mode">{frontendModeLabel(metrics.log_mode)}</span>}
        </div>
        {error && <div className="rp-error">{error}</div>}
      </div>

      <div className="rp-card">
        <div className="rp-card-title">网络</div>
        <div className="rp-net">
          <div className="rp-net-row">
            <span className="rp-net-up">↑ {network.upload?.text || '0 B/s'}</span>
            <span className="rp-net-down">↓ {network.download?.text || '0 B/s'}</span>
          </div>
          <div className="rp-net-chart">
            <DualLineChart dataUp={netUpData} dataDown={netDownData} />
          </div>
        </div>
      </div>

      <div className="rp-card">
        <button
          type="button"
          className="rp-card-head rp-service-toggle"
          aria-expanded={servicesExpanded}
          onClick={() => setServicesExpanded((expanded) => !expanded)}
        >
          <div className="rp-card-title">服务状态</div>
          <span className={`rp-service-chevron ${servicesExpanded ? 'rp-service-chevron--open' : ''}`}>›</span>
        </button>
        {servicesExpanded && (
          <div className="rp-service-list">
            {services.map((service) => (
              <div key={service.id} className="rp-service-item" title={serviceTitle(service)}>
                <span className={`rp-service-dot ${service.online ? 'rp-service-dot--online' : ''}`} />
                <span className="rp-service-name">{serviceName(service)}</span>
              </div>
            ))}
            {!services.length && <div className="rp-empty">暂无服务状态</div>}
          </div>
        )}
      </div>

      <div className="rp-card">
        <div className="rp-card-head">
          <div className="rp-card-title">任务中心</div>
          <div className="rp-card-meta">
            {taskSummary?.active_downloads ?? tasks.length} 进行中
            {typeof taskSummary?.total_download_records === 'number' && ` / ${taskSummary.total_download_records} 记录`}
          </div>
        </div>
        <div className="rp-card-hint">右侧仅显示当前进行中的任务，历史记录请在下载应用中查看。</div>
        {expandedGroup ? (
          <div className="rp-task-group-detail">
            <button type="button" className="rp-back-btn" onClick={() => setExpandedTaskType(null)}>
              <BackIcon />
              返回任务中心
            </button>
            <div className="rp-task-group-title">
              <strong>{expandedGroup.label}</strong>
              <small>{expandedGroup.tasks.length} 个任务</small>
            </div>
            {expandedGroup.tasks.map((task) => (
              <div key={task.id} className="rp-task-item" title={task.stage || task.status}>
                <div className="rp-task-head">
                  <div className="rp-task-main">
                    <span className="rp-task-name">{task.source || task.name}</span>
                    <span className={`rp-task-status ${taskStatusClass(task.status)}`}>{task.status_label || task.status}</span>
                  </div>
                  <div className="rp-task-actions">
                    <button
                      type="button"
                      className="rp-task-btn rp-task-btn--stop"
                      title="停止任务"
                      disabled={!task.can_cancel}
                      onClick={() => void handleTaskAction('cancel', task.id)}
                    >
                      停止
                    </button>
                  </div>
                </div>
                <div className="rp-task-sub">{task.stage || task.id}</div>
                <div className="rp-task-progress-row">
                  <div className="rp-storage-bar"><div className="rp-storage-bar-fill" style={{ width: `${clampPercent(task.progress)}%` }} /></div>
                  <span className="rp-storage-sizes">{Math.round(clampPercent(task.progress))}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          groupedTasks.map((group) => {
            const appType = appTypeForTaskGroup(group.type, group.label)
            const progress = clampPercent(group.progress)
            return (
            <button
              key={group.type}
              type="button"
              className="rp-task-group"
              onClick={() => setExpandedTaskType(group.type)}
            >
              <div className="rp-task-group-head">
                <div className="rp-task-group-title">
                  <strong>{group.label}</strong>
                  <small>{group.statusSummary}</small>
                </div>
                <span className="rp-task-group-count">{group.tasks.length} 个</span>
              </div>
              <div className="rp-task-group-tools">
                <span className="rp-task-group-kind">{appType ? '查看任务详情' : '任务详情'}</span>
                <span className="rp-task-group-percent">{Math.round(progress)}%</span>
              </div>
              <div className="rp-task-progress-row">
                <div className="rp-storage-bar"><div className="rp-storage-bar-fill" style={{ width: `${progress}%` }} /></div>
              </div>
            </button>
            )
          })
        )}
        {!tasks.length && <div className="rp-empty">当前没有任务</div>}
      </div>
    </div>
  )
}

const BackIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 18l-6-6 6-6" />
  </svg>
)

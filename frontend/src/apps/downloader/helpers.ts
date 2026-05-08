import { PLATFORM_OPTIONS } from '@/apps/downloader/constants'
import type { CategoryKey, DetailRow, DownloadPlatform, DownloadTask, PlatformOption, TaskStats } from '@/apps/downloader/types'

export function getCategoryForTask(task: DownloadTask): CategoryKey {
  switch (task.status) {
    case 'pending':
    case 'running':
      return 'downloading'
    case 'completed':
      return 'completed'
    case 'failed':
      return 'error'
    case 'cancelled':
    case 'paused':
      return 'paused'
    default:
      return 'downloading'
  }
}

export function isTaskCancellable(task: Pick<DownloadTask, 'status'>): boolean {
  return task.status === 'pending' || task.status === 'running'
}

export function isTaskRetryable(task: Pick<DownloadTask, 'status' | 'params'>): boolean {
  return ['failed', 'cancelled', 'completed'].includes(task.status) && typeof task.params?.url === 'string'
}

export function isTaskClearable(task: Pick<DownloadTask, 'status'>): boolean {
  return ['completed', 'failed', 'cancelled', 'paused'].includes(task.status)
}

export function computeStats(tasks: DownloadTask[]): TaskStats {
  const stats: TaskStats = {
    all: tasks.length,
    downloading: 0,
    completed: 0,
    paused: 0,
    error: 0,
  }

  tasks.forEach((task) => {
    const category = getCategoryForTask(task)
    if (category === 'downloading') stats.downloading += 1
    else if (category === 'completed') stats.completed += 1
    else if (category === 'paused') stats.paused += 1
    else if (category === 'error') stats.error += 1
  })

  return stats
}

export function mergeTasks(primary: DownloadTask[], secondary: DownloadTask[]): DownloadTask[] {
  const merged = new Map<string, DownloadTask>()
  ;[...secondary, ...primary].forEach((task) => merged.set(task.id, task))
  return Array.from(merged.values()).sort((a, b) => b.created_at - a.created_at)
}

export function getPlatformOption(value?: string | null): PlatformOption {
  return PLATFORM_OPTIONS.find((option) => option.value === value) ?? PLATFORM_OPTIONS[0]
}

export function inferPlatformFromExtractor(extractor: string): DownloadPlatform | null {
  const normalized = extractor.toLowerCase()
  if (!normalized) return null
  if (normalized.includes('youtube')) return 'youtube'
  if (normalized.includes('bili')) return 'bilibili'
  if (['douyin', 'tiktok', 'kuaishou', 'ixigua', 'xiaohongshu', 'instagram'].some((keyword) => normalized.includes(keyword))) {
    return 'short_video'
  }
  return null
}

/** 任务提交时的来源 URL（用于复制、重试等） */
export function getTaskSourceUrl(task: DownloadTask): string {
  const params = task.params ?? {}
  if (typeof params.url === 'string' && params.url.trim()) return params.url.trim()
  return (task.name || '').trim()
}

export function extractTaskInfo(task: DownloadTask): Record<string, unknown> {
  const items = Array.isArray(task.result?.items) ? task.result.items : []
  const firstItem = items[0]
  if (firstItem && typeof firstItem === 'object' && firstItem !== null && typeof (firstItem as Record<string, unknown>).info === 'object') {
    return ((firstItem as Record<string, unknown>).info as Record<string, unknown>) ?? {}
  }
  return {}
}

/** yt-dlp 结果中的本地视频路径（用于工作台切片等） */
export function getTaskVideoFilePath(task: DownloadTask): string {
  const info = extractTaskInfo(task)
  const p = info.local_path
  return typeof p === 'string' && p.trim().length > 0 ? p.trim() : ''
}

/** 本地字幕路径（用于工作台 AI 分析字幕） */
export function getTaskSubtitleFilePath(task: DownloadTask): string {
  const info = extractTaskInfo(task)
  const p = info.subtitle_path
  return typeof p === 'string' && p.trim().length > 0 ? p.trim() : ''
}

/** 是否可向工作台跳转并做「AI 分析字幕」 */
export function canWorkbenchAiAnalyze(task: DownloadTask): boolean {
  return task.status === 'completed' && Boolean(getTaskSubtitleFilePath(task))
}

/** 是否可向工作台跳转并做「AI 切片 / 导出片段」（需本地视频） */
export function canWorkbenchAiSlice(task: DownloadTask): boolean {
  return task.status === 'completed' && Boolean(getTaskVideoFilePath(task))
}

/** 列表主行展示用：优先 yt-dlp 解析出的标题，未就绪时退回任务名（多为链接）。 */
export function getTaskDisplayTitle(task: DownloadTask): string {
  const info = extractTaskInfo(task)
  const title = typeof info.title === 'string' ? info.title.trim() : ''
  if (title) return title
  return task.name || '-'
}

/** 供搜索框匹配标题与原始链接等。 */
export function getTaskSearchHaystack(task: DownloadTask): string {
  const info = extractTaskInfo(task)
  const title = typeof info.title === 'string' ? info.title.trim() : ''
  const parts = [task.name, title].filter((p) => p.length > 0)
  return parts.join('\n').toLowerCase()
}

export function resolveTaskPlatform(task: DownloadTask): PlatformOption {
  const params = task.params ?? {}
  const info = extractTaskInfo(task)
  const platformParam = typeof params.platform === 'string' ? params.platform : ''
  if (platformParam) return getPlatformOption(platformParam)

  const inferred =
    inferPlatformFromExtractor(String(info.extractor_key || '')) ||
    inferPlatformFromExtractor(String(info.extractor || ''))

  return getPlatformOption(inferred || 'auto')
}

export function formatRelativeTime(timestamp?: number | null): string {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins} 分钟前`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours} 小时前`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays} 天前`
  return `${date.getMonth() + 1}/${date.getDate()}`
}

export function formatAbsoluteTime(timestamp?: number | null): string {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

export function toMultilineString(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function createOptimisticTask(url: string, payload: Record<string, unknown>, result: Record<string, unknown>): DownloadTask {
  return {
    id: String(result.task_id),
    type: 'download',
    name: url,
    status: result.status === 'running' ? 'running' : 'pending',
    progress: 0,
    stage: '等待开始',
    created_at: Math.floor(Date.now() / 1000),
    params: payload,
  }
}

export function buildRetryPayload(task: DownloadTask): Record<string, unknown> | null {
  const params = task.params ?? {}
  const url = typeof params.url === 'string' ? params.url : ''
  if (!url) return null
  return {
    url,
    platform: typeof params.platform === 'string' ? params.platform : 'auto',
    output_dir: typeof params.output_dir === 'string' ? params.output_dir : '',
    quality: typeof params.quality === 'string' ? params.quality : 'best',
    subtitles: typeof params.subtitles === 'boolean' ? params.subtitles : true,
    analyze: false,
  }
}

export function extractTaskDetailRows(task: DownloadTask): DetailRow[] {
  const params = task.params ?? {}
  const info = extractTaskInfo(task)
  const result = task.result ?? {}
  const stage = task.stage || '-'
  const platform = resolveTaskPlatform(task)
  const directMediaUrl = (info.direct_media_url as string) || (info.url as string) || '-'
  const requestMethod = directMediaUrl !== '-' ? 'GET' : '-'

  return [
    { label: '任务 ID', value: task.id },
    { label: '平台模式', value: platform.label },
    { label: '当前状态', value: task.status },
    { label: '当前阶段', value: stage },
    { label: '解析器', value: (info.extractor_key as string) || (info.extractor as string) || '-' },
    { label: '来源链接', value: (info.webpage_url as string) || (params.url as string) || task.name },
    { label: '真实下载链接', value: directMediaUrl },
    { label: '请求方式', value: requestMethod },
    { label: '传输协议', value: (info.protocol as string) || '-' },
    { label: '格式标识', value: (info.format_id as string) || '-' },
    { label: '文件类型', value: (info.ext as string) || '-' },
    { label: '视频标题', value: (info.title as string) || task.name },
    { label: '上传者', value: (info.uploader as string) || '-' },
    { label: '输出目录', value: (params.output_dir as string) || '默认下载目录' },
    { label: '下载文件', value: (info.local_path as string) || '-' },
    { label: '字幕文件', value: (info.subtitle_path as string) || '-' },
    { label: '质量策略', value: (params.quality as string) || 'best' },
    { label: '提交接口', value: 'POST /api/fetcher/download' },
    { label: '创建时间', value: formatAbsoluteTime(task.created_at) },
    { label: '开始时间', value: formatAbsoluteTime(task.started_at) },
    { label: '完成时间', value: formatAbsoluteTime(task.completed_at) },
    { label: '错误信息', value: task.error || '-' },
    { label: '结果摘要', value: (result.summary_text as string) || '-' },
  ]
}

export function extractTaskRequestSnapshot(task: DownloadTask): Record<string, unknown> {
  const params = task.params ?? {}
  const info = extractTaskInfo(task)
  const platform = resolveTaskPlatform(task)
  const headers =
    info.http_headers && typeof info.http_headers === 'object' && !Array.isArray(info.http_headers)
      ? (info.http_headers as Record<string, unknown>)
      : {}

  return {
    platform: platform.label,
    extractor: (info.extractor_key as string) || (info.extractor as string) || '-',
    submit_endpoint: 'POST /api/fetcher/download',
    source_url: (info.webpage_url as string) || (params.url as string) || task.name,
    direct_media_url: (info.direct_media_url as string) || (info.url as string) || '-',
    method: (info.direct_media_url as string) || (info.url as string) ? 'GET' : '-',
    protocol: (info.protocol as string) || '-',
    format_id: (info.format_id as string) || '-',
    file_ext: (info.ext as string) || '-',
    headers: Object.keys(headers).length > 0 ? headers : '当前任务结果尚未持久化额外请求头',
  }
}

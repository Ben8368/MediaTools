export type DownloadTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused'

export type DownloadTask = {
  id: string
  type: string
  name: string
  status: DownloadTaskStatus
  progress: number
  stage: string
  created_at: number
  updated_at?: number | null
  started_at?: number | null
  completed_at?: number | null
  paused_at?: number | null
  params?: Record<string, unknown>
  state?: Record<string, unknown>
  result?: Record<string, unknown>
  error?: string
}

export interface TaskStats {
  all: number
  downloading: number
  completed: number
  paused: number
  error: number
}

export type DownloadPlatform = 'auto' | 'youtube' | 'bilibili' | 'short_video'

export type PlatformOption = {
  value: DownloadPlatform
  label: string
  hint: string
  supportsSubtitles: boolean
}

export type CategoryKey = 'all' | 'downloading' | 'completed' | 'paused' | 'error'

/** 下载列表行「更多」菜单动作 */
export type DownloaderRowMenuAction = 'ai_analyze' | 'copy_url' | 'retry'

export type CategoryMeta = {
  label: string
  icon: string
  key: keyof TaskStats
}

export type DetailRow = {
  label: string
  value: unknown
}

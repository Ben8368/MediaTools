const API_KEY_STORAGE_KEY = 'mediatools.apiKey'

function getApiKey() {
  return localStorage.getItem(API_KEY_STORAGE_KEY) || sessionStorage.getItem(API_KEY_STORAGE_KEY) || import.meta.env.VITE_MEDIATOOLS_API_KEY || import.meta.env.VITE_API_KEY || ''
}

function setApiKey(apiKey: string) {
  const key = apiKey.trim()
  if (key) localStorage.setItem(API_KEY_STORAGE_KEY, key)
}

async function request(path: string, init: RequestInit = {}, retry = true): Promise<any> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const apiKey = getApiKey()
  if (apiKey) headers.set('X-API-Key', apiKey)

  const response = await fetch(path, { ...init, headers })
  if (response.status === 401 && retry) {
    const nextKey = window.prompt('Please enter the MediaTools API key')
    if (nextKey) {
      setApiKey(nextKey)
      return request(path, init, false)
    }
  }

  const text = await response.text()
  const data = text ? JSON.parse(text) : null
  if (!response.ok) {
    throw new Error(data?.error || data?.detail || response.statusText)
  }
  return data
}

function get(path: string, params?: Record<string, unknown>) {
  const url = new URL(path, window.location.origin)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  })
  return request(url.pathname + url.search)
}

function post(path: string, payload?: Record<string, unknown>) {
  return request(path, { method: 'POST', body: JSON.stringify(payload || {}) })
}

function put(path: string, payload?: Record<string, unknown>) {
  return request(path, { method: 'PUT', body: JSON.stringify(payload || {}) })
}

function del(path: string, payload?: Record<string, unknown>) {
  return request(path, { method: 'DELETE', body: JSON.stringify(payload || {}) })
}

export function wsUrl(path: string) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = new URL(`${protocol}//${window.location.host}${path}`)
  const apiKey = getApiKey()
  if (apiKey) url.searchParams.set('api_key', apiKey)
  return url.toString()
}

export const getSystemStatus = () => get('/api/system/status')
export const getSystemMetrics = () => get('/api/system/metrics')
export const cancelTask = (taskId: string) => post(`/api/tasks/${taskId}/cancel`)
export const shutdownSystem = () => post('/api/system/shutdown')
export const restartSystem = () => post('/api/system/restart')
export const getModules = () => get('/api/modules')
export const getWorkspace = () => get('/api/workspace')
export const setWorkspace = (projectRoot: string) => post('/api/workspace', { project_root: projectRoot })
export const runAgent = (payload: Record<string, unknown>) => post('/api/agent/chat', payload)
export const testAgentConnection = (payload: Record<string, unknown>) => post('/api/agent/test-connection', payload)
export const runFetcherDownload = (payload: Record<string, unknown>) => post('/api/fetcher/download', payload)
export const runEncoder = (payload: Record<string, unknown>) => post('/api/encoder/transcode', payload)
export const runDecryptor = (payload: Record<string, unknown>) => post('/api/decryptor/decrypt', payload)
export const fetchAssets = (params: Record<string, unknown>) => get('/api/assets/list', params)
export const fetchPathPickerRoots = () => get('/api/path-picker/roots')
export const listPathPickerDirectory = (params: Record<string, unknown>) => get('/api/path-picker/list', params)
export const fetchFilebrowserDisks = () => get('/api/filebrowser/disks')
export const listFilebrowserDirectory = (params: Record<string, unknown>) => get('/api/filebrowser/list', params)
export const createFilebrowserDirectory = (path: string) => post('/api/filebrowser/mkdir', { path })
export const deleteFilebrowserPath = (path: string, recursive = true) => del('/api/filebrowser/delete', { path, recursive })
export const fetchFilebrowserTrash = () => get('/api/filebrowser/trash')
export const restoreFilebrowserTrash = (id: string, restorePath = '') => post('/api/filebrowser/trash/restore', { id, restore_path: restorePath })
export const purgeFilebrowserTrash = (id: string) => post('/api/filebrowser/trash/purge', { id })
export const emptyFilebrowserTrash = () => del('/api/filebrowser/trash/empty')
export const fetchLogs = (params: Record<string, unknown>) => get('/api/logs', params)
export const fetchLogMetadata = () => get('/api/logs/modules')
export const clearLogs = () => post('/api/logs/clear')
export const fetchPhotoshopStatus = () => get('/api/photoshop/status')
export const scanPhotoshopTicket = (payload: Record<string, unknown>) => post('/api/photoshop/scan', payload)
export const scanPhotoshopFolder = (payload: Record<string, unknown>) => post('/api/photoshop/scan-folder', payload)
export const fetchPhotoshopTickets = () => get('/api/photoshop/tickets')
export const fetchPhotoshopTicket = (ticketId: string) => get(`/api/photoshop/tickets/${ticketId}`)
export const importPhotoshopTicket = (filePath: string) => post('/api/photoshop/tickets/import', { file_path: filePath })
export const updatePhotoshopTicket = (ticketId: string, ticket: Record<string, unknown>) => put(`/api/photoshop/tickets/${ticketId}`, { ticket })
export const deletePhotoshopTicket = (ticketId: string) => request(`/api/photoshop/tickets/${ticketId}`, { method: 'DELETE' })
export const executePhotoshopTicket = (ticketId: string, dryRun: boolean, selectedTaskIndexes: number[]) => post(`/api/photoshop/tickets/${ticketId}/execute`, { dry_run: dryRun, selected_task_indexes: selectedTaskIndexes })
export const fetchPhotoshopExecution = (ticketId: string) => get(`/api/photoshop/executions/${ticketId}`)
export const cancelPhotoshopExecution = (ticketId: string) => post(`/api/photoshop/executions/${ticketId}/cancel`)
export const fetchAEStatus = () => get('/api/adobe/after_effects/status')
export const scanAETicket = (payload: Record<string, unknown>) => post('/api/adobe/after_effects/scan', payload)
export const scanAEFolder = (payload: Record<string, unknown>) => post('/api/adobe/after_effects/scan-folder', payload)
export const fetchAETickets = () => get('/api/adobe/after_effects/tickets')
export const fetchAETicket = (ticketId: string) => get(`/api/adobe/after_effects/tickets/${ticketId}`)
export const importAETicket = (filePath: string) => post('/api/adobe/after_effects/tickets/import', { file_path: filePath })
export const updateAETicket = (ticketId: string, ticket: Record<string, unknown>) => put(`/api/adobe/after_effects/tickets/${ticketId}`, { ticket })
export const deleteAETicket = (ticketId: string) => request(`/api/adobe/after_effects/tickets/${ticketId}`, { method: 'DELETE' })
export const executeAETicket = (ticketId: string, dryRun: boolean, selectedTaskIndexes: number[]) => post(`/api/adobe/after_effects/tickets/${ticketId}/execute`, { dry_run: dryRun, selected_task_indexes: selectedTaskIndexes })
export const fetchAEExecution = (ticketId: string) => get(`/api/adobe/after_effects/executions/${ticketId}`)
export const cancelAEExecution = (ticketId: string) => post(`/api/adobe/after_effects/executions/${ticketId}/cancel`)
export const createAECheckpoint = (payload: Record<string, unknown>) => post('/api/adobe/after_effects/checkpoints/create', payload)
export const fetchAECheckpoints = (projectPath: string) => get('/api/adobe/after_effects/checkpoints', { project_path: projectPath })
export const addAERenderQueue = (payload: Record<string, unknown>) => post('/api/adobe/after_effects/render/add', payload)
export const startAERender = (payload: Record<string, unknown>) => post('/api/adobe/after_effects/render/start', payload)
export const fetchAERenderStatus = (projectPath: string) => get('/api/adobe/after_effects/render/status', { project_path: projectPath })
export const fetchSystemFonts = (params: Record<string, unknown> = {}) => get('/api/system/fonts', params)
export const fetchWorkbenchMedia = () => get('/api/workbench/media')
export const analyzeWorkbenchSubtitle = (payload: Record<string, unknown>) => post('/api/workbench/analyze', payload)
export const exportWorkbenchClips = (payload: Record<string, unknown>) => post('/api/workbench/export', payload)
export const fetchAuditorStatus = () => get('/api/auditor/status')
export const fetchAuditorConfig = () => get('/api/auditor/config')
export const updateAuditorConfig = (config: Record<string, unknown>) => put('/api/auditor/config', { config })
export const runAuditorOnce = () => post('/api/auditor/run-once')

export const getTaskList = (params?: Record<string, unknown>) => get('/api/tasks/list', params)
export const getActiveTasks = () => get('/api/tasks/active')
export const getWeeklyHistory = () => get('/api/tasks/history/week')
export const getTask = (taskId: string) => get(`/api/tasks/${taskId}`)
export const deleteTaskRecord = (taskId: string, allowActive = false) => request(`/api/tasks/${taskId}?allow_active=${allowActive ? 'true' : 'false'}`, { method: 'DELETE' })
export const clearTaskRecords = (payload?: Record<string, unknown>) => post('/api/tasks/clear', payload)

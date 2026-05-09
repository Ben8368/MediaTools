import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'

import {
  cancelTask,
  clearTaskRecords,
  runFetcherDownload,
  analyzeDownloaderAi,
  sliceDownloaderAi,
} from '@/api'
import { DirectoryPickerDialog } from '@/apps/FileManagerApp'
import { DownloaderAddForm } from '@/apps/downloader/DownloaderAddForm'
import { DownloaderDetailDrawer } from '@/apps/downloader/DownloaderDetailDrawer'
import {
  buildRetryPayload,
  computeStats,
  createOptimisticTask,
  extractTaskDetailRows,
  extractTaskRequestSnapshot,
  getCategoryForTask,
  getPlatformOption,
  getTaskDisplayTitle,
  getTaskSearchHaystack,
  getTaskSourceUrl,
  getTaskSubtitleFilePath,
  getTaskVideoFilePath,
  isTaskCancellable,
  isTaskClearable,
  isTaskRetryable,
  mergeTasks,
} from '@/apps/downloader/helpers'
import { DownloaderMiniAiChat } from '@/apps/downloader/DownloaderMiniAiChat'
import { DownloaderSidebar } from '@/apps/downloader/DownloaderSidebar'
import { DownloaderStatusBar } from '@/apps/downloader/DownloaderStatusBar'
import { DownloaderTaskTable } from '@/apps/downloader/DownloaderTaskTable'
import { DownloaderToolbar } from '@/apps/downloader/DownloaderToolbar'
import type { CategoryKey, DownloadPlatform, DownloadTask, DownloaderRowMenuAction } from '@/apps/downloader/types'
import { useDownloaderTaskData } from '@/apps/downloader/useDownloaderTaskData'

type AiAnalyzeMode = 'analyze' | 'export'

type SubtitleMode = 'none' | 'hard' | 'soft'

type AiAnalyzeDraft = {
  mode: AiAnalyzeMode
  subtitleMode: SubtitleMode
  padding: number
  expectedDuration: number
  extraContext: string
}

function clampNumber(value: number, min: number, max: number) {
  if (Number.isNaN(value)) return min
  return Math.min(max, Math.max(min, value))
}

type AiAnalyzeDialogProps = {
  open: boolean
  task: DownloadTask | null
  draft: AiAnalyzeDraft
  onDraftChange: (draft: AiAnalyzeDraft) => void
  onClose: () => void
  onSubmit: () => void
  isSubmitting?: boolean
  submitProgress?: string
}

function AiAnalyzeDialog({ open, task, draft, onDraftChange, onClose, onSubmit, isSubmitting, submitProgress }: AiAnalyzeDialogProps) {
  useEffect(() => {
    if (!open) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open || !task) return null

  return (
    <div className="automation-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="automation-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="AI分析"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="automation-dialog-head">
          <div>
            <span>AI分析</span>
            <h3>{getTaskDisplayTitle(task)}</h3>
            <p>先分析字幕生成片段建议；也可以在分析后直接导出切片。</p>
          </div>
          <button className="automation-dialog-close" type="button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <div className="automation-dialog-grid">
          <label>
            模式
            <select
              value={draft.mode}
              onChange={(event) => onDraftChange({ ...draft, mode: event.target.value as AiAnalyzeMode })}
            >
              <option value="analyze">只分析（生成片段建议）</option>
              <option value="export">分析并导出切片</option>
            </select>
          </label>

          <label>
            期望切片时长（秒，0 为自由分析）
            <input
              type="number"
              step={0.1}
              min={0}
              max={600}
              value={draft.expectedDuration}
              onChange={(event) =>
                onDraftChange({
                  ...draft,
                  expectedDuration: clampNumber(Number(event.target.value || 0), 0, 600),
                })
              }
            />
          </label>

          {draft.mode === 'export' && (
            <>
              <label>
                留白时长（秒）
                <input
                  type="number"
                  step={0.1}
                  min={0}
                  max={10}
                  value={draft.padding}
                  onChange={(event) =>
                    onDraftChange({
                      ...draft,
                      padding: clampNumber(Number(event.target.value || 0), 0, 10),
                    })
                  }
                />
              </label>

              <label>
                字幕处理
                <select
                  value={draft.subtitleMode}
                  onChange={(event) => onDraftChange({ ...draft, subtitleMode: event.target.value as SubtitleMode })}
                >
                  <option value="none">否</option>
                  <option value="hard">硬字幕（烧录到视频）</option>
                  <option value="soft">软字幕（单独字幕文件）</option>
                </select>
              </label>
            </>
          )}

          <label style={{ gridColumn: '1 / -1' }}>
            补充需求（可选）
            <textarea
              value={draft.extraContext}
              placeholder="例如：产品名称/定位/目标人群/口播风格/需要强调的卖点/禁用词..."
              onChange={(event) => onDraftChange({ ...draft, extraContext: event.target.value })}
            />
          </label>
        </div>

        <footer className="automation-dialog-actions">
          <button type="button" className="dl-btn" onClick={onClose} disabled={isSubmitting}>
            取消
          </button>
          <button type="button" className="dl-btn dl-btn--primary" onClick={onSubmit} disabled={isSubmitting}>
            {isSubmitting ? (submitProgress || '处理中...') : draft.mode === 'export' ? '分析并导出' : '开始分析'}
          </button>
        </footer>
      </section>
    </div>
  )
}

export { computeStats, isTaskCancellable } from '@/apps/downloader/helpers'

export function DownloaderApp() {
  const [selectedCategory, setSelectedCategory] = useState<CategoryKey>('all')
  const [searchText, setSearchText] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [addingTask, setAddingTask] = useState(false)
  const [taskUrl, setTaskUrl] = useState('')
  const [taskPlatform, setTaskPlatform] = useState<DownloadPlatform>('auto')
  const [taskQuality, setTaskQuality] = useState('best')
  const [taskSubtitles, setTaskSubtitles] = useState(true)
  const [taskOutputDir, setTaskOutputDir] = useState('')
  const [showDirectoryPicker, setShowDirectoryPicker] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [actionError, setActionError] = useState('')
  const [detailOpen, setDetailOpen] = useState(false)
  const [miniAiOpen, setMiniAiOpen] = useState(false)
  const [aiDialogOpen, setAiDialogOpen] = useState(false)
  const [aiDialogTask, setAiDialogTask] = useState<DownloadTask | null>(null)
  const [aiSubmitting, setAiSubmitting] = useState(false)
  const [aiSubmitProgress, setAiSubmitProgress] = useState('')
  const [aiTaskId, setAiTaskId] = useState<string | null>(null)
  const [aiPollInterval, setAiPollInterval] = useState<ReturnType<typeof setInterval> | null>(null)
  const [aiDraft, setAiDraft] = useState<AiAnalyzeDraft>({
    mode: 'analyze',
    subtitleMode: 'none',
    padding: 0.8,
    expectedDuration: 0.0,
    extraContext: '',
  })
  const selectionAnchorIdRef = useRef<string | null>(null)
  const { historyTasks, queueTasks, mergedTasks, fetchHistoryTasks, refreshLists, setOptimisticTasks } = useDownloaderTaskData()

  useEffect(() => {
    if (['completed', 'paused', 'error'].includes(selectedCategory)) {
      void fetchHistoryTasks()
    }
  }, [fetchHistoryTasks, selectedCategory])

  const selectedPlatform = useMemo(() => getPlatformOption(taskPlatform), [taskPlatform])

  useEffect(() => {
    if (!selectedPlatform.supportsSubtitles && taskSubtitles) {
      setTaskSubtitles(false)
    }
  }, [selectedPlatform.supportsSubtitles, taskSubtitles])

  const sourceTasks = useMemo(() => {
    if (selectedCategory === 'all') return mergedTasks
    if (['completed', 'paused', 'error'].includes(selectedCategory)) return historyTasks
    return queueTasks
  }, [historyTasks, mergedTasks, queueTasks, selectedCategory])

  const stats = useMemo(() => computeStats(mergedTasks), [mergedTasks])

  const filteredTasks = useMemo(() => {
    let filtered = sourceTasks
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((task) => getCategoryForTask(task) === selectedCategory)
    }
    if (searchText.trim()) {
      const keyword = searchText.trim().toLowerCase()
      filtered = filtered.filter((task) => getTaskSearchHaystack(task).includes(keyword))
    }
    return filtered
  }, [searchText, selectedCategory, sourceTasks])

  useEffect(() => {
    setSelectedIds((prev) => {
      if (prev.size === 0) return prev
      const next = new Set([...prev].filter((id) => filteredTasks.some((t) => t.id === id)))
      return next.size === prev.size ? prev : next
    })
  }, [filteredTasks])

  useEffect(() => {
    if (filteredTasks.length === 0) {
      setSelectedTaskId(null)
      return
    }
    if (!selectedTaskId || !filteredTasks.some((task) => task.id === selectedTaskId)) {
      setSelectedTaskId(filteredTasks[0].id)
    }
  }, [filteredTasks, selectedTaskId])

  const selectedTask = useMemo(
    () => mergedTasks.find((task) => task.id === selectedTaskId) ?? null,
    [mergedTasks, selectedTaskId],
  )

  const taskContextLine = useMemo(() => {
    if (!selectedTask) return null
    const url = getTaskSourceUrl(selectedTask)
    const title = getTaskDisplayTitle(selectedTask)
    const videoPath = getTaskVideoFilePath(selectedTask)
    const subtitlePath = getTaskSubtitleFilePath(selectedTask)
    const params = selectedTask.params ?? {}
    const outputDir = typeof params.output_dir === 'string' ? params.output_dir.trim() : ''

    const lines = [
      `任务ID：${selectedTask.id}`,
      `标题：${title}`,
      `状态：${selectedTask.status}`,
    ]
    if (url) lines.push(`来源链接：${url}`)
    lines.push(outputDir ? `提交时输出目录：${outputDir}` : '提交时输出目录：未指定（服务端使用工作区默认下载目录）')
    lines.push(videoPath ? `本地视频路径（落盘）：${videoPath}` : '本地视频路径：（任务 result 中暂无，可能仍在下载、历史未含结果字段，或需刷新列表）')
    lines.push(subtitlePath ? `本地字幕路径（落盘）：${subtitlePath}` : '本地字幕路径：（任务 result 中暂无；未勾选字幕或未生成文件时为空）')
    return lines.join('\n')
  }, [selectedTask])

  const hasBulkSelection = selectedIds.size > 0
  const selectedTasks = useMemo(() => {
    if (hasBulkSelection) {
      return filteredTasks.filter((task) => selectedIds.has(task.id))
    }
    return selectedTask ? [selectedTask] : []
  }, [filteredTasks, hasBulkSelection, selectedIds, selectedTask])

  const canStopSelected = selectedTasks.length > 0 && selectedTasks.every((task) => isTaskCancellable(task))
  const canRetrySelected = selectedTasks.length > 0 && selectedTasks.every((task) => isTaskRetryable(task))
  const selectedClearableTasks = useMemo(() => selectedTasks.filter((task) => isTaskClearable(task)), [selectedTasks])
  const canClearRecords = selectedClearableTasks.length > 0
  const clearRecordsTitle = useMemo(() => {
    if (selectedClearableTasks.length > 0) {
      const n = selectedClearableTasks.length
      const m = selectedTasks.length
      if (m === n) {
        return n === 1 ? '删除当前所选记录的下载历史' : `删除所选 ${n} 条记录的下载历史`
      }
      return `删除其中可清除的 ${n} 条记录（${m - n} 条仍在进行中，将保留）`
    }
    if (!filteredTasks.length) return '暂无可显示的下载任务'
    return '没有可删除的记录：仅已完成、已停止或失败的任务可从列表移除。请先选中任务或使用全选。'
  }, [filteredTasks.length, selectedClearableTasks, selectedTasks])
  const canSelectAllVisible = filteredTasks.length > 0
  const allVisibleSelected = filteredTasks.length > 0 && filteredTasks.every((task) => selectedIds.has(task.id))

  const submitTaskPayloads = useCallback(
    async (payloads: Record<string, unknown>[]) => {
      const createdTasks: DownloadTask[] = []
      for (const payload of payloads) {
        const result = await runFetcherDownload(payload)
        if (result?.ok !== true) {
          throw new Error(result?.error || '服务器返回异常响应')
        }
        if (result?.task_id) {
          createdTasks.push(createOptimisticTask(String(payload.url || ''), payload, result))
        }
      }
      if (createdTasks.length > 0) {
        setOptimisticTasks((prev) => mergeTasks(createdTasks, prev))
        setSelectedTaskId(createdTasks[0].id)
        setSelectedIds(new Set())
        selectionAnchorIdRef.current = createdTasks[0].id
      }
      setSelectedCategory('all')
      await refreshLists()
    },
    [refreshLists, setOptimisticTasks],
  )

  const submitNewTask = useCallback(async () => {
    if (!taskUrl.trim() || addingTask) return
    setAddingTask(true)
    setSubmitError('')
    setActionError('')
    try {
      const payloads = taskUrl
        .split('\n')
        .map((url) => url.trim())
        .filter((url) => url.length > 0)
        .map((url) => ({
          url,
          platform: taskPlatform,
          output_dir: taskOutputDir || '',
          quality: taskQuality,
          subtitles: selectedPlatform.supportsSubtitles ? taskSubtitles : false,
          analyze: false,
        }))

      await submitTaskPayloads(payloads)
      setTaskUrl('')
      setShowAddForm(false)
    } catch (err: any) {
      setSubmitError(err?.message || '下载任务提交失败')
    } finally {
      setAddingTask(false)
    }
  }, [addingTask, selectedPlatform.supportsSubtitles, submitTaskPayloads, taskOutputDir, taskPlatform, taskQuality, taskSubtitles, taskUrl])

  const clearRecords = useCallback(async () => {
    if (!canClearRecords) return
    setActionError('')
    try {
      const ids = selectedClearableTasks.map((task) => task.id)
      await clearTaskRecords({ ids, terminal_only: false })
      setSelectedIds((prev) => {
        const next = new Set(prev)
        ids.forEach((id) => next.delete(id))
        return next
      })
      if (selectedTask && ids.includes(selectedTask.id)) {
        setSelectedTaskId(null)
      }
      await refreshLists()
    } catch (err: any) {
      setActionError(err?.message || '删除记录失败')
    }
  }, [canClearRecords, refreshLists, selectedClearableTasks, selectedTask])

  const stopSelected = useCallback(async () => {
    if (!canStopSelected) return
    setActionError('')
    try {
      await Promise.all(selectedTasks.map((task) => cancelTask(task.id)))
      setSelectedIds(new Set())
      await refreshLists()
    } catch (err: any) {
      setActionError(err?.message || '停止任务失败')
    }
  }, [canStopSelected, refreshLists, selectedTasks])

  const retrySelected = useCallback(async () => {
    if (!canRetrySelected) return
    setActionError('')
    try {
      const payloads = selectedTasks
        .map((task) => buildRetryPayload(task))
        .filter((payload): payload is Record<string, unknown> => Boolean(payload))
      if (!payloads.length) {
        throw new Error('选中的任务缺少可重试的下载参数')
      }
      await submitTaskPayloads(payloads)
      setSelectedIds(new Set())
    } catch (err: any) {
      setActionError(err?.message || '重新提交失败')
    }
  }, [canRetrySelected, selectedTasks, submitTaskPayloads])

  const handleRowMenuAction = useCallback(
    async (action: DownloaderRowMenuAction, task: DownloadTask) => {
      setActionError('')
      if (action === 'ai_analyze') {
        if (task.status !== 'completed') {
          setActionError('请先等待任务下载完成后再分析字幕。')
          return
        }
        const sub = getTaskSubtitleFilePath(task)
        if (!sub) {
          setActionError('未找到字幕文件路径，请确认下载任务包含字幕。')
          return
        }
        setAiDialogTask(task)
        setAiDialogOpen(true)
        return
      }
      if (action === 'copy_url') {
        const url = getTaskSourceUrl(task)
        if (!url) {
          setActionError('该任务没有可复制的链接')
          return
        }
        try {
          await navigator.clipboard.writeText(url)
        } catch {
          setActionError('复制失败，请检查浏览器剪贴板权限')
        }
        return
      }
      if (action === 'retry') {
        try {
          const payload = buildRetryPayload(task)
          if (!payload) throw new Error('无法重试：缺少原始链接参数')
          await submitTaskPayloads([payload])
        } catch (err: any) {
          setActionError(err?.message || '重新提交失败')
        }
      }
    },
    [refreshLists, submitTaskPayloads],
  )

  const handleRowClick = useCallback(
    (taskId: string, index: number, event: MouseEvent<HTMLDivElement>) => {
      if (event.shiftKey && selectionAnchorIdRef.current) {
        const anchorIdx = filteredTasks.findIndex((t) => t.id === selectionAnchorIdRef.current)
        if (anchorIdx >= 0) {
          const lo = Math.min(anchorIdx, index)
          const hi = Math.max(anchorIdx, index)
          const range = filteredTasks.slice(lo, hi + 1).map((t) => t.id)
          setSelectedIds(new Set(range))
          setSelectedTaskId(taskId)
          return
        }
      }
      selectionAnchorIdRef.current = taskId
      setSelectedTaskId(taskId)
      setSelectedIds(new Set())
    },
    [filteredTasks],
  )

  const toggleSelectAllVisible = useCallback(() => {
    if (!filteredTasks.length) return
    const allSelected = filteredTasks.every((task) => selectedIds.has(task.id))
    if (allSelected) {
      setSelectedIds(new Set())
      selectionAnchorIdRef.current = filteredTasks[0].id
      setSelectedTaskId(filteredTasks[0].id)
    } else {
      const ids = filteredTasks.map((t) => t.id)
      setSelectedIds(new Set(ids))
      selectionAnchorIdRef.current = filteredTasks[0].id
      setSelectedTaskId(filteredTasks[0].id)
    }
  }, [filteredTasks, selectedIds])

  const detailRows = selectedTask ? extractTaskDetailRows(selectedTask) : []
  const detailRequest = selectedTask ? JSON.stringify(extractTaskRequestSnapshot(selectedTask), null, 2) : ''
  const detailState = selectedTask?.state ? JSON.stringify(selectedTask.state, null, 2) : ''
  const detailResult = selectedTask?.result ? JSON.stringify(selectedTask.result, null, 2) : ''

  return (
    <div className="dl-app">
      <DownloaderSidebar
        selectedCategory={selectedCategory}
        stats={stats}
        miniAiOpen={miniAiOpen}
        onToggleMiniAi={() => setMiniAiOpen((open) => !open)}
        onSelectCategory={(category) => {
          setSelectedCategory(category)
          setSelectedIds(new Set())
          selectionAnchorIdRef.current = null
        }}
      />

      <DownloaderMiniAiChat open={miniAiOpen} onClose={() => setMiniAiOpen(false)} taskContextLine={taskContextLine} />

      <main className={`dl-panel ${showAddForm ? 'dl-panel--with-form' : ''}`}>
        <DownloaderToolbar
          showAddForm={showAddForm}
          onToggleAddForm={() => setShowAddForm((prev) => !prev)}
          canStopSelected={canStopSelected}
          onStopSelected={stopSelected}
          canRetrySelected={canRetrySelected}
          onRetrySelected={retrySelected}
          canSelectAllVisible={canSelectAllVisible}
          allVisibleSelected={allVisibleSelected}
          onToggleSelectAll={toggleSelectAllVisible}
          canClearRecords={canClearRecords}
          clearRecordsTitle={clearRecordsTitle}
          onClearRecords={clearRecords}
          searchText={searchText}
          onSearchTextChange={setSearchText}
        />

        <div className="dl-stage">
          {showAddForm && (
            <DownloaderAddForm
              taskUrl={taskUrl}
              taskPlatform={taskPlatform}
              taskQuality={taskQuality}
              taskSubtitles={taskSubtitles}
              taskOutputDir={taskOutputDir}
              selectedPlatform={selectedPlatform}
              addingTask={addingTask}
              submitError={submitError}
              onTaskUrlChange={setTaskUrl}
              onTaskPlatformChange={setTaskPlatform}
              onTaskQualityChange={setTaskQuality}
              onTaskSubtitlesChange={setTaskSubtitles}
              onTaskOutputDirChange={setTaskOutputDir}
              onOpenDirectoryPicker={() => setShowDirectoryPicker(true)}
              onSubmit={submitNewTask}
              onClose={() => setShowAddForm(false)}
            />
          )}

          <div className="dl-body">
            <section className="dl-content">
              <DownloaderTaskTable
                filteredTasks={filteredTasks}
                selectedIds={selectedIds}
                selectedTaskId={selectedTaskId}
                onRowClick={handleRowClick}
                onRowMenuAction={handleRowMenuAction}
              />
            </section>
          </div>

          <DownloaderDetailDrawer
            open={detailOpen}
            selectedTask={selectedTask}
            detailRows={detailRows}
            detailRequest={detailRequest}
            detailState={detailState}
            detailResult={detailResult}
            actionError={actionError}
            onClose={() => setDetailOpen(false)}
          />

          <AiAnalyzeDialog
            open={aiDialogOpen}
            task={aiDialogTask}
            draft={aiDraft}
            onDraftChange={setAiDraft}
            onClose={() => {
              if (aiPollInterval) {
                clearInterval(aiPollInterval)
                setAiPollInterval(null)
              }
              setAiDialogOpen(false)
              setAiDialogTask(null)
              setAiSubmitting(false)
              setAiSubmitProgress('')
              setAiTaskId(null)
            }}
            isSubmitting={aiSubmitting}
            submitProgress={aiSubmitProgress}
            onSubmit={async () => {
              if (!aiDialogTask || aiSubmitting) return
              setActionError('')
              setAiSubmitting(true)
              setAiSubmitProgress('准备中...')

              if (aiDraft.mode === 'export') {
                const vid = getTaskVideoFilePath(aiDialogTask)
                if (!vid) {
                  setActionError('未找到本地视频文件路径。')
                  setAiSubmitting(false)
                  setAiSubmitProgress('')
                  return
                }
              }

              try {
                let response
                if (aiDraft.mode === 'export') {
                  response = await sliceDownloaderAi({
                    task_id: aiDialogTask.id,
                    subtitle_mode: aiDraft.subtitleMode,
                    padding: aiDraft.padding,
                    expected_duration: aiDraft.expectedDuration,
                    extra_context: aiDraft.extraContext,
                  })
                } else {
                  response = await analyzeDownloaderAi({
                    task_id: aiDialogTask.id,
                    expected_duration: aiDraft.expectedDuration,
                    extra_context: aiDraft.extraContext,
                  })
                }

                if (response?.task_id) {
                  setAiTaskId(response.task_id)
                  setAiSubmitProgress('已提交，等待处理...')

                  const eventSource = new EventSource(`/api/downloader/ai/task/${response.task_id}/stream`)

                  eventSource.onmessage = (event) => {
                    try {
                      const data = JSON.parse(event.data)
                      if (data.error) {
                        setActionError(data.error)
                        eventSource.close()
                        setAiSubmitting(false)
                        setAiSubmitProgress('')
                      } else if (data.done) {
                        eventSource.close()
                        setAiSubmitting(false)
                        setAiSubmitProgress('')
                        setAiTaskId(null)
                        setAiDialogOpen(false)
                        setAiDialogTask(null)
                        if (aiPollInterval) {
                          clearInterval(aiPollInterval)
                          setAiPollInterval(null)
                        }
                        refreshLists()
                      } else if (data.stage) {
                        setAiSubmitProgress(`${data.stage}...`)
                      }
                    } catch (err) {
                      console.error('解析流数据失败:', err)
                    }
                  }

                  eventSource.onerror = () => {
                    eventSource.close()
                    setActionError('连接中断')
                    setAiSubmitting(false)
                    setAiSubmitProgress('')
                  }
                } else {
                  setAiSubmitting(false)
                  setAiSubmitProgress('')
                }
              } catch (err: any) {
                setActionError(err?.message || 'AI分析提交失败')
                setAiSubmitting(false)
                setAiSubmitProgress('')
              }
            }}
          />
        </div>

        <DownloaderStatusBar detailOpen={detailOpen} onToggleDetail={() => setDetailOpen((prev) => !prev)} />
      </main>

      <DirectoryPickerDialog
        open={showDirectoryPicker}
        value={taskOutputDir}
        title="选择下载目录"
        confirmLabel="确认"
        onClose={() => setShowDirectoryPicker(false)}
        onPick={setTaskOutputDir}
      />
    </div>
  )
}

import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'

import {
  cancelTask,
  clearTaskRecords,
  runFetcherDownload,
} from '@/api'
import { DirectoryPickerDialog } from '@/apps/FileManagerApp'
import { WORKBENCH_PREFILL_STORAGE_KEY, type WorkbenchPrefillPayload } from '@/apps/workbench/prefill'
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
import { useWindowStore } from '@/windowStore'

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
  const selectionAnchorIdRef = useRef<string | null>(null)
  const { historyTasks, queueTasks, mergedTasks, fetchHistoryTasks, refreshLists, setOptimisticTasks } = useDownloaderTaskData()
  const openWindow = useWindowStore((state) => state.openWindow)

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
    const bits = [`当前任务：${title}`, `状态：${selectedTask.status}`]
    if (url) bits.push(`链接：${url}`)
    return bits.join(' · ')
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
  const canClearAllTerminal = historyTasks.some((task) => isTaskClearable(task))
  const canClearSelected = hasBulkSelection && selectedClearableTasks.length > 0
  const canClearRecords = hasBulkSelection ? canClearSelected : canClearAllTerminal
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
      if (hasBulkSelection) {
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
      } else {
        await clearTaskRecords({ terminal_only: true })
        setSelectedIds(new Set())
        if (selectedTask && isTaskClearable(selectedTask)) {
          setSelectedTaskId(null)
        }
      }
      await refreshLists()
    } catch (err: any) {
      setActionError(err?.message || '清理记录失败')
    }
  }, [canClearRecords, hasBulkSelection, refreshLists, selectedClearableTasks, selectedTask])

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
        const vid = getTaskVideoFilePath(task)
        const payload: WorkbenchPrefillPayload = {
          subtitlePath: sub,
          highlight: 'analyze',
          ...(vid ? { videoPath: vid } : {}),
        }
        sessionStorage.setItem(WORKBENCH_PREFILL_STORAGE_KEY, JSON.stringify(payload))
        openWindow('workbench')
        return
      }
      if (action === 'ai_slice') {
        if (task.status !== 'completed') {
          setActionError('请先等待任务下载完成后再进行切片。')
          return
        }
        const vid = getTaskVideoFilePath(task)
        if (!vid) {
          setActionError('未找到本地视频文件路径。')
          return
        }
        const sub = getTaskSubtitleFilePath(task)
        const payload: WorkbenchPrefillPayload = {
          videoPath: vid,
          highlight: 'export',
          ...(sub ? { subtitlePath: sub } : {}),
        }
        sessionStorage.setItem(WORKBENCH_PREFILL_STORAGE_KEY, JSON.stringify(payload))
        openWindow('workbench')
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
    [openWindow, refreshLists, submitTaskPayloads],
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
          hasBulkSelection={hasBulkSelection}
          canClearSelected={canClearSelected}
          canClearAllTerminal={canClearAllTerminal}
          canClearRecords={canClearRecords}
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

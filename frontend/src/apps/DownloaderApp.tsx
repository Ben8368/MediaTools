import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  cancelTask,
  clearTaskRecords,
  runFetcherDownload,
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
  isTaskCancellable,
  isTaskClearable,
  isTaskRetryable,
  mergeTasks,
} from '@/apps/downloader/helpers'
import { DownloaderSidebar } from '@/apps/downloader/DownloaderSidebar'
import { DownloaderStatusBar } from '@/apps/downloader/DownloaderStatusBar'
import { DownloaderTaskTable } from '@/apps/downloader/DownloaderTaskTable'
import { DownloaderToolbar } from '@/apps/downloader/DownloaderToolbar'
import type { CategoryKey, DownloadPlatform, DownloadTask } from '@/apps/downloader/types'
import { useDownloaderTaskData } from '@/apps/downloader/useDownloaderTaskData'

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
  const { tasks, historyTasks, queueTasks, mergedTasks, fetchHistoryTasks, refreshLists, setOptimisticTasks } = useDownloaderTaskData()

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
    if (selectedCategory === 'all') return queueTasks
    if (['completed', 'paused', 'error'].includes(selectedCategory)) return historyTasks
    return tasks
  }, [historyTasks, queueTasks, selectedCategory, tasks])

  const stats = useMemo(() => {
    const queueStats = computeStats(queueTasks)
    return {
      ...queueStats,
      completed: historyTasks.filter((task) => getCategoryForTask(task) === 'completed').length,
      paused: historyTasks.filter((task) => getCategoryForTask(task) === 'paused').length,
      error: historyTasks.filter((task) => getCategoryForTask(task) === 'error').length,
    }
  }, [historyTasks, queueTasks])

  const filteredTasks = useMemo(() => {
    let filtered = sourceTasks
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((task) => getCategoryForTask(task) === selectedCategory)
    }
    if (searchText.trim()) {
      const keyword = searchText.trim().toLowerCase()
      filtered = filtered.filter((task) => task.name.toLowerCase().includes(keyword))
    }
    return filtered
  }, [searchText, selectedCategory, sourceTasks])

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
        setDetailOpen(true)
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

  const focusTask = useCallback((id: string) => {
    setSelectedTaskId(id)
    setDetailOpen(true)
  }, [])

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleSelectAllVisible = useCallback(() => {
    if (!filteredTasks.length) return
    setSelectedIds((prev) => {
      const next = new Set(prev)
      const shouldClear = filteredTasks.every((task) => next.has(task.id))
      filteredTasks.forEach((task) => {
        if (shouldClear) next.delete(task.id)
        else next.add(task.id)
      })
      return next
    })
  }, [filteredTasks])

  const detailRows = selectedTask ? extractTaskDetailRows(selectedTask) : []
  const detailRequest = selectedTask ? JSON.stringify(extractTaskRequestSnapshot(selectedTask), null, 2) : ''
  const detailState = selectedTask?.state ? JSON.stringify(selectedTask.state, null, 2) : ''
  const detailResult = selectedTask?.result ? JSON.stringify(selectedTask.result, null, 2) : ''

  return (
    <div className="dl-app">
      <DownloaderSidebar
        selectedCategory={selectedCategory}
        stats={stats}
        onSelectCategory={(category) => {
          setSelectedCategory(category)
          setSelectedIds(new Set())
        }}
      />

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
                onFocusTask={focusTask}
                onToggleSelect={toggleSelect}
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
        confirmLabel="用于下载"
        onClose={() => setShowDirectoryPicker(false)}
        onPick={setTaskOutputDir}
      />
    </div>
  )
}

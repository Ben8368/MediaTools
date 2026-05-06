import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { getActiveTasks, getWeeklyHistory } from '@/api'
import { mergeTasks } from '@/apps/downloader/helpers'
import type { DownloadTask } from '@/apps/downloader/types'

export function useDownloaderTaskData() {
  const [tasks, setTasks] = useState<DownloadTask[]>([])
  const [historyTasks, setHistoryTasks] = useState<DownloadTask[]>([])
  const [optimisticTasks, setOptimisticTasks] = useState<DownloadTask[]>([])
  const loadingRef = useRef(false)
  const historyLoadingRef = useRef(false)

  const fetchTasks = useCallback(async () => {
    if (loadingRef.current) return
    loadingRef.current = true
    try {
      const activeRes = await getActiveTasks()
      const activeTasks: DownloadTask[] = (activeRes.tasks || []).filter((task: DownloadTask) => task.type === 'download')
      activeTasks.sort((a, b) => b.created_at - a.created_at)
      setTasks(activeTasks)
    } catch {
      // Keep the last successful list when polling fails.
    } finally {
      loadingRef.current = false
    }
  }, [])

  const fetchHistoryTasks = useCallback(async () => {
    if (historyLoadingRef.current) return
    historyLoadingRef.current = true
    try {
      const historyRes = await getWeeklyHistory()
      const history: DownloadTask[] = (historyRes.tasks || []).filter((task: DownloadTask) => task.type === 'download')
      history.sort((a, b) => b.created_at - a.created_at)
      setHistoryTasks(history)
    } catch {
      // Keep the last successful list when polling fails.
    } finally {
      historyLoadingRef.current = false
    }
  }, [])

  useEffect(() => {
    void fetchTasks()
    const interval = setInterval(() => {
      void fetchTasks()
    }, 2000)
    return () => clearInterval(interval)
  }, [fetchTasks])

  useEffect(() => {
    void fetchHistoryTasks()
  }, [fetchHistoryTasks])

  useEffect(() => {
    setOptimisticTasks((prev) =>
      prev.filter(
        (task) => !tasks.some((activeTask) => activeTask.id === task.id) && !historyTasks.some((historyTask) => historyTask.id === task.id),
      ),
    )
  }, [historyTasks, tasks])

  const queueTasks = useMemo(() => mergeTasks(optimisticTasks, tasks), [optimisticTasks, tasks])
  const mergedTasks = useMemo(() => mergeTasks(queueTasks, historyTasks), [historyTasks, queueTasks])

  const refreshLists = useCallback(async () => {
    await Promise.all([fetchTasks(), fetchHistoryTasks()])
  }, [fetchHistoryTasks, fetchTasks])

  return {
    tasks,
    historyTasks,
    queueTasks,
    mergedTasks,
    fetchHistoryTasks,
    refreshLists,
    setOptimisticTasks,
  }
}

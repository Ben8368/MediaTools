import { useCallback, useState } from 'react'

import { listFilebrowserDirectory } from '@/api'
import type { FileEntry, ListResponse } from '@/apps/file-manager/types'

export function useFilebrowserNavigator() {
  const [currentPath, setCurrentPath] = useState('')
  const [directories, setDirectories] = useState<FileEntry[]>([])
  const [files, setFiles] = useState<FileEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)

  const navigate = useCallback(async (path: string, push = true) => {
    if (!path) return null
    setLoading(true)
    setError('')
    try {
      const data = await listFilebrowserDirectory({ directory: path }) as ListResponse
      if (!data.ok) throw new Error('目录加载失败')
      setCurrentPath(data.path)
      setDirectories(data.directories || [])
      setFiles(data.files || [])
      if (push) {
        setHistoryIndex((index) => {
          setHistory((items) => {
            const next = items.slice(0, index + 1)
            next.push(data.path)
            return next
          })
          return index + 1
        })
      }
      return data
    } catch (err: any) {
      setError(err?.message || '目录加载失败')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const resetHistory = useCallback(() => {
    setHistory([])
    setHistoryIndex(-1)
  }, [])

  const goBack = useCallback(() => {
    if (historyIndex <= 0) return
    const nextIndex = historyIndex - 1
    setHistoryIndex(nextIndex)
    void navigate(history[nextIndex], false)
  }, [history, historyIndex, navigate])

  const goForward = useCallback(() => {
    if (historyIndex < 0 || historyIndex >= history.length - 1) return
    const nextIndex = historyIndex + 1
    setHistoryIndex(nextIndex)
    void navigate(history[nextIndex], false)
  }, [history, historyIndex, navigate])

  return {
    currentPath,
    directories,
    files,
    loading,
    error,
    setError,
    setCurrentPath,
    setDirectories,
    setFiles,
    navigate,
    resetHistory,
    goBack,
    goForward,
    canGoBack: historyIndex > 0,
    canGoForward: historyIndex >= 0 && historyIndex < history.length - 1,
  }
}

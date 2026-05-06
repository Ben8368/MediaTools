import { useEffect, useMemo, useState } from 'react'

import { fetchFilebrowserDisks, getWorkspace } from '@/api'
import {
  BackIcon,
  CloseIcon,
  DriveIcon,
  FileIcon,
  FolderIcon,
  ForwardIcon,
  IconButton,
  RefreshIcon,
  SearchIcon,
  SortIcon,
} from '@/apps/file-manager/controls'
import type { DirectoryPickerDialogProps, DiskInfo } from '@/apps/file-manager/types'
import { entryType, formatDate, formatSize, locationLabel, parentPath, resolveInitialPath } from '@/apps/file-manager/utils'
import { useFilebrowserNavigator } from '@/apps/file-manager/useFilebrowserNavigator'

export function DirectoryPickerDialog({
  open,
  value,
  mode = 'directory',
  title = '选择路径',
  confirmLabel = '确定',
  onClose,
  onPick,
}: DirectoryPickerDialogProps) {
  const {
    currentPath,
    directories,
    files,
    loading,
    error,
    navigate,
    resetHistory,
    goBack,
    goForward,
    canGoBack,
    canGoForward,
  } = useFilebrowserNavigator()
  const [disks, setDisks] = useState<DiskInfo[]>([])
  const [selectedPath, setSelectedPath] = useState('')
  const [searchText, setSearchText] = useState('')

  const canPickDirectory = mode === 'directory' || mode === 'any'
  const canPickFile = mode === 'file' || mode === 'any'

  useEffect(() => {
    if (!open) return
    let alive = true

    async function init() {
      try {
        const [diskData, workspace] = await Promise.all([fetchFilebrowserDisks(), getWorkspace()])
        if (!alive) return

        const nextDisks = diskData?.disks || []
        const workspacePath = workspace?.workspace?.project_root || workspace?.project_root || ''
        const initialPath = resolveInitialPath(value, workspacePath, nextDisks)
        setDisks(nextDisks)
        setSearchText('')
        resetHistory()
        setSelectedPath(canPickDirectory ? initialPath : '')

        if (initialPath) {
          const data = await navigate(initialPath)
          if (alive && data?.path && canPickDirectory) setSelectedPath(data.path)
        }
      } catch {
        if (alive) setSelectedPath('')
      }
    }

    void init()
    return () => {
      alive = false
    }
  }, [canPickDirectory, navigate, open, resetHistory, value])

  const filteredDirectories = useMemo(() => {
    const keyword = searchText.trim().toLowerCase()
    if (!keyword) return directories
    return directories.filter((entry) => entry.name.toLowerCase().includes(keyword))
  }, [directories, searchText])

  const filteredFiles = useMemo(() => {
    const keyword = searchText.trim().toLowerCase()
    if (!keyword) return files
    return files.filter((entry) => entry.name.toLowerCase().includes(keyword))
  }, [files, searchText])

  const currentParent = parentPath(currentPath)
  const confirmedPath = selectedPath || (canPickDirectory ? currentPath : '')
  const searchPlaceholder = mode === 'directory' ? '搜索文件夹' : '搜索文件或文件夹'

  if (!open) return null

  return (
    <div className="fm-picker" onClick={onClose}>
      <div className="fm-picker__panel fm-picker__panel--compact" onClick={(event) => event.stopPropagation()}>
        <div className="fm-picker__header">
          <div>
            <strong>{title}</strong>
            <div className="fm-picker__hint">
              {mode === 'directory' ? '双击进入文件夹，单击选择后确认。' : '双击进入文件夹，单击文件后确认。'}
            </div>
          </div>
          <button type="button" className="fm-icon-btn" title="关闭" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>

        <div className="fm-picker__content fm-picker__content--compact">
          <div className="fm-picker__toolbar">
            <div className="fm-nav-buttons">
              <IconButton disabled={!canGoBack} title="后退" onClick={goBack}>
                <BackIcon />
              </IconButton>
              <IconButton disabled={!canGoForward} title="前进" onClick={goForward}>
                <ForwardIcon />
              </IconButton>
              <IconButton disabled={!currentParent} title="上一级" onClick={() => currentParent && void navigate(currentParent)}>
                <SortIcon />
              </IconButton>
              <IconButton disabled={!currentPath} title="刷新" onClick={() => void navigate(currentPath, false)}>
                <RefreshIcon />
              </IconButton>
            </div>
            <div className="fm-picker__address">{currentPath || '选择路径'}</div>
            <label className="fm-search fm-picker__search">
              <SearchIcon />
              <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder={searchPlaceholder} />
            </label>
          </div>

          <div className="fm-picker__drives">
            {disks.map((disk) => (
              <button
                key={disk.path}
                type="button"
                className={`fm-picker__drive ${currentPath.toLowerCase().startsWith(disk.path.toLowerCase()) ? 'fm-picker__drive--active' : ''}`}
                onClick={() => void navigate(disk.path)}
              >
                <DriveIcon />
                <span>{disk.name}</span>
                <small>{formatSize(disk.free)}</small>
              </button>
            ))}
          </div>

          {canPickDirectory && currentPath && (
            <button
              type="button"
              className={`fm-picker__current ${selectedPath === currentPath ? 'fm-picker__current--active' : ''}`}
              onClick={() => setSelectedPath(currentPath)}
            >
              <strong>当前目录</strong>
              <span>{currentPath}</span>
            </button>
          )}

          <div className="fm-picker__list">
            {loading && <div className="fm-empty">正在加载...</div>}
            {!loading && error && <div className="fm-empty fm-empty--error">{error}</div>}
            {!loading && !error && filteredDirectories.map((entry) => (
              <button
                key={entry.path}
                type="button"
                className={`fm-picker__row ${canPickDirectory && selectedPath === entry.path ? 'fm-picker__row--selected' : ''}`}
                onClick={() => canPickDirectory && setSelectedPath(entry.path)}
                onDoubleClick={() => void navigate(entry.path)}
              >
                <div className="fm-picker__row-main">
                  <FolderIcon />
                  <div className="fm-picker__row-copy">
                    <strong>{entry.name}</strong>
                    <span>{formatDate(entry.modified)}</span>
                  </div>
                </div>
                <em>{locationLabel(entry.path, disks)}</em>
              </button>
            ))}
            {!loading && !error && filteredFiles.map((entry) => (
              <button
                key={entry.path}
                type="button"
                className={`fm-picker__row ${selectedPath === entry.path ? 'fm-picker__row--selected' : ''}`}
                onClick={() => canPickFile && setSelectedPath(entry.path)}
              >
                <div className="fm-picker__row-main">
                  <FileIcon ext={entry.extension} />
                  <div className="fm-picker__row-copy">
                    <strong>{entry.name}</strong>
                    <span>{entryType(entry)} | {formatSize(entry.size)}</span>
                  </div>
                </div>
                <em>{formatDate(entry.modified)}</em>
              </button>
            ))}
            {!loading && !error && currentPath && filteredDirectories.length === 0 && filteredFiles.length === 0 && (
              <div className="fm-empty">当前目录下没有可选内容</div>
            )}
          </div>
        </div>

        <div className="fm-picker__footer">
          <div className="fm-picker__selection">
            <strong>已选路径</strong>
            <span>{confirmedPath || '未选择'}</span>
          </div>
          <div className="fm-picker__footer-actions">
            <button type="button" className="fm-action-btn" onClick={onClose}>
              取消
            </button>
            <button
              type="button"
              className="fm-action-btn fm-action-btn--primary"
              disabled={!confirmedPath}
              onClick={() => {
                if (!confirmedPath) return
                onPick(confirmedPath)
                onClose()
              }}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import { createFilebrowserDirectory, fetchFilebrowserDisks, getWorkspace } from '@/api'
import {
  BackIcon,
  CloseIcon,
  DriveIcon,
  FileIcon,
  FolderIcon,
  FolderPlusIcon,
  ForwardIcon,
  IconButton,
  ParentDirIcon,
  RefreshIcon,
  SearchIcon,
} from '@/apps/file-manager/controls'
import type { DirectoryPickerDialogProps, DiskInfo } from '@/apps/file-manager/types'
import { displayDiskName, entryType, formatDate, formatSize, cwdCoversSelection, isPathOnDisk, joinPath, locationLabel, parentPath, resolveInitialPath } from '@/apps/file-manager/utils'
import { useFilebrowserNavigator } from '@/apps/file-manager/useFilebrowserNavigator'

export function DirectoryPickerDialog({
  open,
  value,
  mode = 'directory',
  title = '选择路径',
  confirmLabel = '确认',
  portalContainer,
  onClose,
  onPick,
}: DirectoryPickerDialogProps) {
  const {
    currentPath,
    directories,
    files,
    loading,
    error,
    setError,
    navigate,
    resetHistory,
    goBack,
    goForward,
    canGoBack,
    canGoForward,
  } = useFilebrowserNavigator()
  const [disks, setDisks] = useState<DiskInfo[]>([])
  const [selectedPath, setSelectedPath] = useState('')
  const [activeDiskPath, setActiveDiskPath] = useState('')
  const [searchText, setSearchText] = useState('')
  const [mkdirBusy, setMkdirBusy] = useState(false)
  const [addressDraft, setAddressDraft] = useState('')
  const addressFocusedRef = useRef(false)
  const addressInputRef = useRef<HTMLInputElement>(null)

  const scrollAddressInputToEnd = useCallback(() => {
    const el = addressInputRef.current
    if (!el || el.clientWidth <= 0) return
    el.scrollLeft = Math.max(0, el.scrollWidth - el.clientWidth)
  }, [])

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
        const initialSelection = canPickFile && value.trim() ? value.trim() : ''
        const browsePath = initialSelection && !canPickDirectory ? parentPath(initialSelection) || initialSelection : initialPath
        setDisks(nextDisks)
        setActiveDiskPath(nextDisks.find((disk: DiskInfo) => isPathOnDisk(browsePath, disk.path))?.path || '')
        setSearchText('')
        resetHistory()
        setSelectedPath(canPickDirectory ? initialPath : initialSelection)

        if (browsePath) {
          const data = await navigate(browsePath)
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
  }, [canPickDirectory, canPickFile, navigate, open, resetHistory, value])

  useEffect(() => {
    if (!addressFocusedRef.current) setAddressDraft(currentPath)
  }, [currentPath])

  /* 未编辑时让地址栏显示路径尾部（长路径常见需求） */
  useLayoutEffect(() => {
    if (!open || addressFocusedRef.current) return
    scrollAddressInputToEnd()
  }, [addressDraft, open, scrollAddressInputToEnd])

  const commitAddress = useCallback(async () => {
    const raw = addressDraft.trim()
    if (!raw) {
      setAddressDraft(currentPath)
      return
    }
    if (raw === currentPath) return
    const data = await navigate(raw)
    if (data?.path) {
      if (canPickDirectory) setSelectedPath(data.path)
      setAddressDraft(data.path)
    } else {
      setAddressDraft(currentPath)
    }
  }, [addressDraft, canPickDirectory, currentPath, navigate])

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

  const handleNewFolder = async () => {
    if (!currentPath || mkdirBusy) return
    const name = window.prompt('请输入新文件夹名称', '新建文件夹')
    if (name == null) return
    const trimmed = name.trim()
    if (!trimmed) return
    if (trimmed === '.' || trimmed === '..') {
      setError('无效的文件夹名称')
      return
    }
    if (/[<>:"/\\|?*\x00-\x1f]/.test(trimmed)) {
      setError('名称不能包含 \\ / : * ? " < > | 等字符')
      return
    }
    const newPath = joinPath(currentPath, trimmed)
    setMkdirBusy(true)
    setError('')
    try {
      await createFilebrowserDirectory(newPath)
      await navigate(currentPath, false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setMkdirBusy(false)
    }
  }

  useEffect(() => {
    if (!currentPath) return
    setActiveDiskPath((current) => disks.find((disk) => isPathOnDisk(currentPath, disk.path))?.path || current)
  }, [currentPath, disks])

  useEffect(() => {
    if (!canPickDirectory || !currentPath) return
    setSelectedPath((prev) => {
      if (!prev) return currentPath
      return cwdCoversSelection(currentPath, prev) ? prev : currentPath
    })
  }, [canPickDirectory, currentPath])

  if (!open) return null

  const dialog = (
    <div className="fm-picker fm-picker--app-root" onClick={onClose}>
      <div className="fm-picker__panel fm-picker__panel--compact" onClick={(event) => event.stopPropagation()}>
        <div className="fm-picker__header">
          <div>
            <strong>{title}</strong>
            <div className="fm-picker__hint">
              {mode === 'directory'
                ? '顶部地址栏可直接粘贴路径，按 Enter 或失焦跳转；双击进入文件夹，单击文件夹后确认。'
                : '顶部地址栏可直接粘贴路径，按 Enter 或失焦跳转；双击进入文件夹，单击文件后确认。'}
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
              <IconButton disabled={!currentParent} title="返回上一级目录" onClick={() => currentParent && void navigate(currentParent)}>
                <ParentDirIcon />
              </IconButton>
              <IconButton disabled={!currentPath} title="刷新" onClick={() => void navigate(currentPath, false)}>
                <RefreshIcon />
              </IconButton>
            </div>
            <input
              ref={addressInputRef}
              type="text"
              className="fm-picker__address-input"
              value={addressDraft}
              onChange={(e) => setAddressDraft(e.target.value)}
              onFocus={() => {
                addressFocusedRef.current = true
              }}
              onBlur={() => {
                addressFocusedRef.current = false
                void commitAddress()
                requestAnimationFrame(() => scrollAddressInputToEnd())
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  ;(e.target as HTMLInputElement).blur()
                }
              }}
              spellCheck={false}
              autoComplete="off"
              aria-label="当前路径"
              placeholder={currentPath ? '编辑路径后按 Enter 跳转' : '加载中…'}
            />
            <label className="fm-search fm-picker__search">
              <SearchIcon />
              <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder={searchPlaceholder} />
            </label>
          </div>

          <div className="fm-picker__drives">
            <div className="fm-picker__drives-disks">
              {disks.map((disk) => (
                <button
                  key={disk.path}
                  type="button"
                  className={`fm-picker__drive fm-picker__drive--disk ${activeDiskPath === disk.path || isPathOnDisk(currentPath, disk.path) ? 'fm-picker__drive--active' : ''}`}
                  onClick={() => {
                    setActiveDiskPath(disk.path)
                    void navigate(disk.path)
                  }}
                >
                  <span className="fm-picker__drive-icon" aria-hidden>
                    <DriveIcon />
                  </span>
                  <span className="fm-picker__drive-label">{displayDiskName(disk.name)}</span>
                  <small className="fm-picker__drive-meta">{formatSize(disk.free)}</small>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="fm-picker__drive fm-picker__drive--new-folder"
              disabled={!currentPath || loading || mkdirBusy}
              title="在本目录下新建文件夹"
              aria-label="新建文件夹"
              onClick={() => void handleNewFolder()}
            >
              <span className="fm-picker__drive-icon fm-picker__drive-icon--compact" aria-hidden>
                <FolderPlusIcon />
              </span>
              <span className="fm-picker__drive-label">新建文件夹</span>
            </button>
          </div>

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

  return portalContainer ? createPortal(dialog, portalContainer) : dialog
}

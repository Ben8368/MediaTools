import { useEffect, useMemo, useState } from 'react'

import {
  createFilebrowserDirectory,
  deleteFilebrowserPath,
  emptyFilebrowserTrash,
  fetchFilebrowserDisks,
  fetchFilebrowserTrash,
  getWorkspace,
  purgeFilebrowserTrash,
  restoreFilebrowserTrash,
} from '@/api'
import {
  ActionButton,
  BackIcon,
  ChevronIcon,
  ChevronSmallIcon,
  DownloadIcon,
  DriveIcon,
  FileIcon,
  FolderIcon,
  FolderPlusIcon,
  ForwardIcon,
  GridIcon,
  IconButton,
  ListIcon,
  MoreIcon,
  RefreshIcon,
  SearchIcon,
  SettingsIcon,
  SidebarButton,
  SortIcon,
  TrashIcon,
  TuneIcon,
  UploadIcon,
} from '@/apps/file-manager/controls'
import type { DiskInfo, FileEntry, TrashEntry } from '@/apps/file-manager/types'
import {
  entryType,
  displayDiskName,
  formatDate,
  formatSize,
  joinPath,
  isPathOnDisk,
  locationLabel,
  parentPath,
  resolveInitialPath,
  TRASH_PATH,
} from '@/apps/file-manager/utils'
import { useFilebrowserNavigator } from '@/apps/file-manager/useFilebrowserNavigator'

export function FileManagerPane() {
  const {
    currentPath,
    directories,
    files,
    loading,
    error,
    setCurrentPath,
    setDirectories,
    setFiles,
    setError,
    navigate,
    goBack,
    goForward,
    canGoBack,
    canGoForward,
  } = useFilebrowserNavigator()
  const [disks, setDisks] = useState<DiskInfo[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [searchText, setSearchText] = useState('')
  const [activeSection, setActiveSection] = useState<'local' | 'trash'>('local')
  const [activeDiskPath, setActiveDiskPath] = useState('')
  const [lastLocalPath, setLastLocalPath] = useState('')
  const [trashItems, setTrashItems] = useState<TrashEntry[]>([])

  useEffect(() => {
    let alive = true

    async function init() {
      try {
        const [diskData, workspace] = await Promise.all([fetchFilebrowserDisks(), getWorkspace()])
        if (!alive) return
        const nextDisks = diskData?.disks || []
        const workspacePath = workspace?.workspace?.project_root || workspace?.project_root || ''
        const initialPath = resolveInitialPath('', workspacePath, nextDisks)
        setDisks(nextDisks)
        if (initialPath) {
          setActiveDiskPath(nextDisks.find((disk: DiskInfo) => isPathOnDisk(initialPath, disk.path))?.path || '')
          const data = await navigate(initialPath)
          if (alive && data?.path) setLastLocalPath(data.path)
        }
      } catch (err: any) {
        if (alive) setError(err?.message || '文件管理初始化失败')
      }
    }

    void init()
    return () => {
      alive = false
    }
  }, [navigate, setError])

  useEffect(() => {
    if (currentPath && currentPath !== TRASH_PATH) {
      setLastLocalPath(currentPath)
      setActiveSection('local')
      setActiveDiskPath((current) => disks.find((disk) => isPathOnDisk(currentPath, disk.path))?.path || current)
    }
  }, [currentPath, disks])

  const trashEntries = useMemo<FileEntry[]>(() => trashItems.map((item) => ({
    name: item.name,
    path: item.id,
    size: item.size,
    modified: item.deleted_at,
    type: item.type,
    original_path: item.original_path,
  })), [trashItems])

  const allEntries = useMemo(
    () => currentPath === TRASH_PATH ? trashEntries : [...directories, ...files],
    [currentPath, directories, files, trashEntries],
  )

  const filteredEntries = useMemo(() => {
    const keyword = searchText.trim().toLowerCase()
    if (!keyword) return allEntries
    return allEntries.filter((entry) => entry.name.toLowerCase().includes(keyword))
  }, [allEntries, searchText])

  const currentParent = parentPath(currentPath)

  function toggleSelect(path: string) {
    setSelected((items) => {
      const next = new Set(items)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  function openLocalFiles() {
    setActiveSection('local')
    if (currentPath === TRASH_PATH) {
      const targetPath = lastLocalPath || disks[0]?.path
      if (targetPath) void navigate(targetPath)
    }
  }

  async function loadTrash() {
    setError('')
    try {
      const data = await fetchFilebrowserTrash()
      setTrashItems(data?.items || [])
    } catch (err: any) {
      setError(err?.message || '回收站加载失败')
    }
  }

  function openTrash() {
    setActiveSection('trash')
    setCurrentPath(TRASH_PATH)
    setDirectories([])
    setFiles([])
    setSelected(new Set())
    setSearchText('')
    setError('')
    void loadTrash()
  }

  async function createFolder() {
    if (!currentPath || currentPath === TRASH_PATH) return
    const name = window.prompt('新建文件夹名称')
    if (!name?.trim()) return
    try {
      await createFilebrowserDirectory(joinPath(currentPath, name.trim()))
      await navigate(currentPath, false)
    } catch (err: any) {
      setError(err?.message || '新建文件夹失败')
    }
  }

  async function deleteSelected() {
    const paths = Array.from(selected)
    if (!paths.length || currentPath === TRASH_PATH) return
    if (!window.confirm(`确定将选中的 ${paths.length} 项移入回收站吗？`)) return
    try {
      await Promise.all(paths.map((path) => deleteFilebrowserPath(path, true)))
      setSelected(new Set())
      await navigate(currentPath, false)
    } catch (err: any) {
      setError(err?.message || '移入回收站失败')
    }
  }

  async function restoreSelected() {
    const ids = Array.from(selected)
    if (!ids.length || currentPath !== TRASH_PATH) return
    try {
      await Promise.all(ids.map((id) => restoreFilebrowserTrash(id)))
      setSelected(new Set())
      await loadTrash()
    } catch (err: any) {
      setError(err?.message || '恢复失败')
    }
  }

  async function purgeSelected() {
    const ids = Array.from(selected)
    if (!ids.length || currentPath !== TRASH_PATH) return
    if (!window.confirm(`确定彻底删除选中的 ${ids.length} 项吗？此操作不可恢复。`)) return
    try {
      await Promise.all(ids.map((id) => purgeFilebrowserTrash(id)))
      setSelected(new Set())
      await loadTrash()
    } catch (err: any) {
      setError(err?.message || '彻底删除失败')
    }
  }

  async function emptyTrash() {
    if (currentPath !== TRASH_PATH || trashItems.length === 0) return
    if (!window.confirm('确定清空回收站吗？此操作不可恢复。')) return
    try {
      await emptyFilebrowserTrash()
      setSelected(new Set())
      await loadTrash()
    } catch (err: any) {
      setError(err?.message || '清空回收站失败')
    }
  }

  return (
    <div className="fm-app">
      <aside className="fm-sidebar">
        <nav className="fm-nav" style={{ paddingTop: '8px' }}>
          <SidebarButton active={activeSection === 'local'} icon={<ChevronIcon />} label="我的文件" onClick={openLocalFiles} />
          {activeSection === 'local' && disks.length > 0 && (
            <div className="fm-disk-list">
              {disks.map((disk) => (
                <button
                  key={disk.path}
                  className={`fm-disk ${activeDiskPath === disk.path || isPathOnDisk(currentPath, disk.path) ? 'fm-disk--active' : ''}`}
                  onClick={() => {
                    setActiveDiskPath(disk.path)
                    void navigate(disk.path)
                  }}
                >
                  <DriveIcon />
                  <span className="fm-disk-main">{displayDiskName(disk.name)}</span>
                  <small>{formatSize(disk.free)}</small>
                </button>
              ))}
            </div>
          )}
          <div className="fm-nav-gap" />
          <SidebarButton active={activeSection === 'trash'} icon={<TrashIcon />} label="回收站" onClick={openTrash} />
        </nav>
        <button className="fm-settings"><SettingsIcon />设置</button>
      </aside>

      <main className="fm-panel">
        <div className="fm-topbar">
          <div className="fm-nav-buttons">
            <IconButton disabled={!canGoBack} title="后退" onClick={goBack}><BackIcon /></IconButton>
            <IconButton disabled={!canGoForward} title="前进" onClick={goForward}><ForwardIcon /></IconButton>
            <IconButton disabled={!currentPath || currentPath === TRASH_PATH} title="刷新" onClick={() => currentPath && currentPath !== TRASH_PATH && void navigate(currentPath, false)}><RefreshIcon /></IconButton>
          </div>
          <div className="fm-address">{currentPath === TRASH_PATH ? '回收站' : currentPath || '我的文件'}</div>
          <label className="fm-search">
            <SearchIcon />
            <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="搜索" />
          </label>
        </div>

        <div className="fm-actions">
          {currentPath === TRASH_PATH ? (
            <>
              <ActionButton icon={<DownloadIcon />} label="恢复" disabled={!selected.size} onClick={restoreSelected} />
              <ActionButton icon={<TrashIcon />} label="彻底删除" disabled={!selected.size} onClick={purgeSelected} />
              <ActionButton icon={<MoreIcon />} label="清空回收站" disabled={!trashItems.length} onClick={emptyTrash} />
            </>
          ) : (
            <>
              <ActionButton icon={<UploadIcon />} label="上传文件" disabled />
              <ActionButton icon={<FolderPlusIcon />} label="新建文件夹" disabled={!currentPath} onClick={createFolder} />
              <ActionButton icon={<DownloadIcon />} label="下载" disabled={!selected.size} />
              <ActionButton icon={<TrashIcon />} label="移入回收站" disabled={!selected.size} onClick={deleteSelected} />
              <ActionButton icon={<MoreIcon />} label="更多" disabled />
            </>
          )}
          <span className="fm-actions-spacer" />
          <IconButton disabled={!currentParent || currentPath === TRASH_PATH} title="上一级" onClick={() => currentParent && void navigate(currentParent)}><SortIcon /></IconButton>
          <IconButton title="列表视图"><ListIcon /></IconButton>
          <IconButton title="网格视图"><GridIcon /></IconButton>
        </div>

        <section className="fm-table">
          <div className="fm-head">
            <span>文件名</span>
            <span>修改时间</span>
            <span>所在位置</span>
            <span>类型</span>
            <span><TuneIcon /></span>
          </div>

          <div className="fm-list">
            {loading && <div className="fm-empty">正在加载...</div>}
            {!loading && error && <div className="fm-empty fm-empty--error">{error}</div>}
            {!loading && !error && filteredEntries.map((entry) => (
              <div
                className={`fm-row ${selected.has(entry.path) ? 'fm-row--selected' : ''}`}
                key={entry.path}
                onClick={() => toggleSelect(entry.path)}
                onDoubleClick={() => entry.type === 'directory' && void navigate(entry.path)}
              >
                <div className="fm-name">
                  <span className="fm-expander">{entry.type === 'directory' ? <ChevronSmallIcon /> : null}</span>
                  {entry.type === 'directory' ? <FolderIcon /> : <FileIcon ext={entry.extension} />}
                  <strong>{entry.name}</strong>
                  {entry.type === 'file' && <small>{formatSize(entry.size)}</small>}
                </div>
                <span>{formatDate(entry.modified)}</span>
                <span>{currentPath === TRASH_PATH ? entry.original_path : locationLabel(entry.path, disks)}</span>
                <span>{entryType(entry)}</span>
                <span />
              </div>
            ))}
            {!loading && !error && filteredEntries.length === 0 && <div className="fm-empty">{currentPath === TRASH_PATH ? '回收站为空' : '此目录为空'}</div>}
          </div>
        </section>

        <footer className="fm-status">
          <span>共 {filteredEntries.length} 项</span>
          {selected.size > 0 && <span>已选 {selected.size} 项</span>}
        </footer>
      </main>
    </div>
  )
}

import type { DiskInfo, FileEntry } from '@/apps/file-manager/types'

export const TRASH_PATH = '__trash__'

export function formatSize(bytes: number): string {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let index = 0
  let value = bytes
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

export function formatDate(value: string): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function parentPath(path: string): string | null {
  const cleaned = path.replace(/[\\/]+$/, '')
  if (/^[A-Za-z]:$/.test(cleaned)) return null
  const index = Math.max(cleaned.lastIndexOf('\\'), cleaned.lastIndexOf('/'))
  if (index < 0) return null
  if (/^[A-Za-z]:/.test(cleaned) && index <= 2) return `${cleaned.slice(0, 2)}\\`
  return cleaned.slice(0, index) || null
}

export function joinPath(base: string, name: string): string {
  const separator = base.includes('\\') ? '\\' : '/'
  return `${base.replace(/[\\/]+$/, '')}${separator}${name}`
}

/** 所选路径是否为当前浏览目录本身或其下层路径（换到其他目录时需清掉无效的子路径选择）。 */
export function cwdCoversSelection(cwd: string, selected: string): boolean {
  const norm = (p: string) => {
    const t = p.trim().replace(/\\/g, '/')
    if (t === '/') return '/'
    return t.replace(/\/+$/, '')
  }
  const c = norm(cwd)
  const s = norm(selected)
  if (!c || !s) return false
  const cl = c.toLowerCase()
  const sl = s.toLowerCase()
  if (sl === cl) return true
  const base = cl.endsWith('/') ? cl : `${cl}/`
  return sl.startsWith(base)
}

export function entryType(entry: FileEntry): string {
  if (entry.type === 'directory') return '文件夹'
  return entry.extension?.replace('.', '').toUpperCase() || '文件'
}

export function isTemporaryWorkspacePath(path: string): boolean {
  return /[\\/]\.tmp-tests[\\/]/i.test(path)
}

export function resolveInitialPath(value: string, workspacePath: string, disks: DiskInfo[]): string {
  if (value) return value
  if (workspacePath && !isTemporaryWorkspacePath(workspacePath)) return workspacePath
  return disks[0]?.path || ''
}

export function displayDiskName(name: string): string {
  const drive = name.match(/\([A-Za-z]:\)/)?.[0]
  if (drive) return `磁盘 ${drive}`
  return name.replace(/^(本地磁盘|SMB 磁盘|网络磁盘)\s*/i, '磁盘 ')
}

export function isPathOnDisk(path: string, diskPath: string): boolean {
  const currentDrive = path.match(/^([A-Za-z]:)/)?.[1]?.toLowerCase()
  const diskDrive = diskPath.match(/^([A-Za-z]:)/)?.[1]?.toLowerCase()
  if (currentDrive && diskDrive) return currentDrive === diskDrive
  return path.toLowerCase().startsWith(diskPath.toLowerCase())
}

export function locationLabel(path: string, disks: DiskInfo[]): string {
  const disk = disks.find((item) => isPathOnDisk(path, item.path))
  return disk ? disk.name.replace(/^(本地磁盘|SMB 磁盘|网络磁盘)\s*/i, '') : '当前目录'
}

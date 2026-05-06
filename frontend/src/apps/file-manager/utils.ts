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

export function locationLabel(path: string, disks: DiskInfo[]): string {
  const disk = disks.find((item) => path.toLowerCase().startsWith(item.path.toLowerCase()))
  return disk ? disk.name.replace('本地磁盘 ', '') : '当前目录'
}

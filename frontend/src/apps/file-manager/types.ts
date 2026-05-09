export type FileEntry = {
  name: string
  path: string
  size: number
  modified: string
  type: 'directory' | 'file'
  extension?: string
  original_path?: string
}

export type ListResponse = {
  ok: boolean
  path: string
  files: FileEntry[]
  directories: FileEntry[]
}

export type DiskInfo = {
  name: string
  path: string
  total: number
  used: number
  free: number
}

export type PickerMode = 'file' | 'directory' | 'any'

export type DirectoryPickerDialogProps = {
  open: boolean
  value: string
  mode?: PickerMode
  title?: string
  confirmLabel?: string
  portalContainer?: HTMLElement | null
  onClose: () => void
  onPick: (path: string) => void
}

export type TrashEntry = {
  id: string
  name: string
  original_path: string
  deleted_at: string
  type: 'directory' | 'file'
  size: number
  stored_path: string
}

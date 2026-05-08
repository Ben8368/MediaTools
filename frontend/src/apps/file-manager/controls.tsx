import type { ReactNode } from 'react'

export function SidebarButton({ active, icon, label, onClick }: { active?: boolean; icon: ReactNode; label: string; onClick: () => void }) {
  return <button className={`fm-nav-item ${active ? 'fm-nav-item--active' : ''}`} onClick={onClick}>{icon}<span>{label}</span></button>
}

export function IconButton({ children, disabled, title, onClick }: { children: ReactNode; disabled?: boolean; title: string; onClick?: () => void }) {
  return <button className="fm-icon-btn" disabled={disabled} title={title} onClick={onClick}>{children}</button>
}

export function ActionButton({ icon, label, disabled, onClick }: { icon: ReactNode; label: string; disabled?: boolean; onClick?: () => void }) {
  return <button className="fm-action-btn" disabled={disabled} onClick={onClick}>{icon}<span>{label}</span></button>
}

export const ChevronIcon = () => <svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6" /></svg>
export const ChevronSmallIcon = () => <svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6" /></svg>
export const BackIcon = () => <svg viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6" /></svg>
export const ForwardIcon = () => <svg viewBox="0 0 24 24"><path d="M9 18l6-6-6-6" /></svg>
export const RefreshIcon = () => <svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 10-2.34 5.66" /><path d="M20 4v7h-7" /></svg>
export const SearchIcon = () => <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>
export const UploadIcon = () => <svg viewBox="0 0 24 24"><path d="M12 16V4" /><path d="M7 9l5-5 5 5" /><path d="M4 16v3h16v-3" /></svg>
export const FolderPlusIcon = () => <svg viewBox="0 0 24 24"><path d="M3 6h6l2 3h10v9a2 2 0 01-2 2H5a2 2 0 01-2-2z" /><path d="M12 12v5M9.5 14.5h5" /></svg>
export const DownloadIcon = () => <svg viewBox="0 0 24 24"><path d="M12 4v12" /><path d="M7 11l5 5 5-5" /><path d="M4 19h16" /></svg>
export const TrashIcon = () => <svg viewBox="0 0 24 24"><path d="M4 6h16" /><path d="M9 6V4h6v2" /><path d="M7 6l1 14h8l1-14" /></svg>
export const MoreIcon = () => <svg viewBox="0 0 24 24"><circle cx="6" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="18" cy="12" r="1.5" /></svg>
export const CloseIcon = () => <svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg>
export const SortIcon = () => <svg viewBox="0 0 24 24"><path d="M7 4v14" /><path d="M4 15l3 3 3-3" /><path d="M14 6h6M14 12h4M14 18h2" /></svg>

/** 返回上一级目录（水平线 + 向上箭头）。 */
export const ParentDirIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M4 19h16" />
    <path d="M12 17V7M8 11l4-4 4 4" />
  </svg>
)
export const ListIcon = () => <svg viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13" /><path d="M3 6h.01M3 12h.01M3 18h.01" /></svg>
export const GridIcon = () => <svg viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" /></svg>
export const TuneIcon = () => <svg viewBox="0 0 24 24"><path d="M4 7h11M19 7h1M4 12h4M12 12h8M4 17h9M17 17h3" /><circle cx="17" cy="7" r="2" /><circle cx="10" cy="12" r="2" /><circle cx="15" cy="17" r="2" /></svg>
export const DriveIcon = () => <svg viewBox="0 0 24 24"><path d="M5 4h14l2 10v5H3v-5z" /><path d="M3 14h18" /><circle cx="17" cy="17" r="1" /></svg>
export const SettingsIcon = () => <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 00-.1-1l2-1.5-2-3.5-2.4 1a8 8 0 00-1.7-1L14.5 3h-5l-.3 3a8 8 0 00-1.7 1l-2.4-1-2 3.5 2 1.5A7 7 0 005 12a7 7 0 00.1 1l-2 1.5 2 3.5 2.4-1a8 8 0 001.7 1l.3 3h5l.3-3a8 8 0 001.7-1l2.4 1 2-3.5-2-1.5A7 7 0 0019 12z" /></svg>

export function FolderIcon() {
  return (
    <svg className="fm-folder-icon" viewBox="0 0 48 40">
      <defs><linearGradient id="folderGrad" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#6bd6ff" /><stop offset="1" stopColor="#168be8" /></linearGradient></defs>
      <path d="M3 10a6 6 0 016-6h10l4 5h16a6 6 0 016 6v17a6 6 0 01-6 6H9a6 6 0 01-6-6z" fill="url(#folderGrad)" />
      <path d="M7 15h38v17a6 6 0 01-6 6H9a6 6 0 01-6-6V19a4 4 0 014-4z" fill="#1f9be8" opacity=".92" />
      <path d="M9 8h10l3 4H9z" fill="#b7eeff" opacity=".55" />
    </svg>
  )
}

export function FileIcon({ ext }: { ext?: string }) {
  const kind = ext?.replace('.', '').slice(0, 4).toUpperCase() || 'FILE'
  return (
    <span className="fm-file-icon">
      <svg viewBox="0 0 32 38"><path d="M6 1h13l7 7v25a4 4 0 01-4 4H6a4 4 0 01-4-4V5a4 4 0 014-4z" /><path d="M19 1v8h7" /></svg>
      <em>{kind}</em>
    </span>
  )
}

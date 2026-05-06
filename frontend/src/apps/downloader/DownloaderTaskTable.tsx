import { StatusIcon } from '@/apps/downloader/icons'
import { formatRelativeTime } from '@/apps/downloader/helpers'
import type { DownloadTask } from '@/apps/downloader/types'

type DownloaderTaskTableProps = {
  filteredTasks: DownloadTask[]
  selectedIds: Set<string>
  selectedTaskId: string | null
  onFocusTask: (id: string) => void
  onToggleSelect: (id: string) => void
}

export function DownloaderTaskTable({
  filteredTasks,
  selectedIds,
  selectedTaskId,
  onFocusTask,
  onToggleSelect,
}: DownloaderTaskTableProps) {
  return (
    <section className="dl-table">
      <div className="dl-head">
        <span className="dl-col-status" />
        <span className="dl-col-name">任务名称</span>
        <span className="dl-col-progress">进度</span>
        <span className="dl-col-time">时间</span>
      </div>

      <div className="dl-list">
        {filteredTasks.length === 0 && (
          <div className="dl-empty">
            <div className="dl-empty-icon">
              <svg viewBox="0 0 80 72" fill="none">
                <rect x="8" y="20" width="64" height="44" rx="6" fill="rgba(255,255,255,.12)" />
                <path d="M8 32a6 6 0 016-6h10l4 5h32a6 6 0 016 6v24a6 6 0 01-6 6H14a6 6 0 01-6-6z" fill="rgba(255,255,255,.18)" />
                <path d="M12 36h56v24a6 6 0 01-6 6H18a6 6 0 01-6-6V42a6 6 0 016-6z" fill="rgba(255,255,255,.08)" />
                <path d="M18 14h10l4 5H18z" fill="rgba(255,255,255,.14)" />
                <path d="M36 52v8M32 56h8" stroke="rgba(52,210,230,.6)" strokeWidth="2" strokeLinecap="round" />
                <path d="M36 44v4" stroke="rgba(52,210,230,.4)" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M36 44c0-1.5 1-3 2.5-3" stroke="rgba(52,210,230,.4)" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M36 44c0-1.5-1-3-2.5-3" stroke="rgba(52,210,230,.4)" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
            <p>暂无任务</p>
          </div>
        )}

        {filteredTasks.map((task) => (
          <div
            key={task.id}
            className={`dl-row ${selectedIds.has(task.id) ? 'dl-row--selected' : ''} ${selectedTaskId === task.id ? 'dl-row--focused' : ''}`}
            onClick={() => onFocusTask(task.id)}
          >
            <span className="dl-col-status">
              <input
                type="checkbox"
                aria-label={`select-download-task-${task.id}`}
                checked={selectedIds.has(task.id)}
                onChange={() => onToggleSelect(task.id)}
                onClick={(event) => event.stopPropagation()}
              />
              <StatusIcon status={task.status} />
            </span>
            <span className="dl-col-name">
              <strong>{task.name}</strong>
              <small>{task.stage || '-'}</small>
            </span>
            <span className="dl-col-progress">
              <div className="dl-progress-bar">
                <div className="dl-progress-fill" style={{ width: `${Math.min(100, Math.max(0, task.progress || 0))}%` }} />
              </div>
              <span className="dl-progress-text">{(task.progress || 0).toFixed(1)}%</span>
            </span>
            <span className="dl-col-time">{formatRelativeTime(task.created_at)}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

import { type MouseEvent, useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

import { StatusIcon } from '@/apps/downloader/icons'
import { formatRelativeTime, getTaskDisplayTitle, getTaskSourceUrl, canWorkbenchAiAnalyze, isTaskRetryable } from '@/apps/downloader/helpers'
import type { DownloadTask, DownloaderRowMenuAction } from '@/apps/downloader/types'

const MENU_W = 180

function VerticalDotsIcon() {
  return (
    <svg className="dl-row-menu-trigger__icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden>
      <circle cx="8" cy="3.5" r="1.35" fill="currentColor" />
      <circle cx="8" cy="8" r="1.35" fill="currentColor" />
      <circle cx="8" cy="12.5" r="1.35" fill="currentColor" />
    </svg>
  )
}

type DownloaderTaskTableProps = {
  filteredTasks: DownloadTask[]
  selectedIds: Set<string>
  selectedTaskId: string | null
  onRowClick: (taskId: string, index: number, event: MouseEvent<HTMLDivElement>) => void
  onRowMenuAction?: (action: DownloaderRowMenuAction, task: DownloadTask) => void
}

export function DownloaderTaskTable({
  filteredTasks,
  selectedIds,
  selectedTaskId,
  onRowClick,
  onRowMenuAction,
}: DownloaderTaskTableProps) {
  const multi = selectedIds.size > 0
  const [menu, setMenu] = useState<{ task: DownloadTask; x: number; y: number } | null>(null)

  const closeMenu = useCallback(() => setMenu(null), [])

  useEffect(() => {
    if (!menu) return
    function onPointerDown(event: PointerEvent) {
      const el = event.target as HTMLElement | null
      if (el?.closest?.('[data-dl-row-menu-root]')) return
      closeMenu()
    }
    document.addEventListener('pointerdown', onPointerDown, true)
    return () => document.removeEventListener('pointerdown', onPointerDown, true)
  }, [closeMenu, menu])

  useEffect(() => {
    if (!menu) return
    function onScroll() {
      closeMenu()
    }
    window.addEventListener('scroll', onScroll, true)
    return () => window.removeEventListener('scroll', onScroll, true)
  }, [closeMenu, menu])

  function openMenuForTask(task: DownloadTask, event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation()
    const r = event.currentTarget.getBoundingClientRect()
    const x = Math.min(r.right - MENU_W, window.innerWidth - MENU_W - 8)
    const y = r.bottom + 4
    setMenu((prev) => (prev?.task.id === task.id ? null : { task, x, y }))
  }

  function runAction(action: DownloaderRowMenuAction, task: DownloadTask) {
    onRowMenuAction?.(action, task)
    closeMenu()
  }

  const portalMenu =
    menu && typeof document !== 'undefined'
      ? createPortal(
          <div
            data-dl-row-menu-root
            className="dl-row-menu-portal"
            style={{ left: menu.x, top: menu.y }}
            role="menu"
            aria-label="任务扩展操作"
          >
            <button
              type="button"
              role="menuitem"
              className="dl-row-menu-item"
              disabled={!canWorkbenchAiAnalyze(menu.task)}
              title={canWorkbenchAiAnalyze(menu.task) ? '分析字幕并可选导出片段' : '需要任务已完成且存在字幕文件路径'}
              onClick={() => runAction('ai_analyze', menu.task)}
            >
              AI分析
            </button>
            <button
              type="button"
              role="menuitem"
              className="dl-row-menu-item"
              disabled={!getTaskSourceUrl(menu.task)}
              title={getTaskSourceUrl(menu.task) ? '复制原始下载链接' : '无可复制的链接'}
              onClick={() => runAction('copy_url', menu.task)}
            >
              复制链接
            </button>
            <button
              type="button"
              role="menuitem"
              className="dl-row-menu-item"
              disabled={!isTaskRetryable(menu.task)}
              title={isTaskRetryable(menu.task) ? '使用原始参数重新提交下载' : '当前状态不支持重新下载'}
              onClick={() => runAction('retry', menu.task)}
            >
              重新下载
            </button>
          </div>,
          document.body,
        )
      : null

  return (
    <section className="dl-table dl-table--queue">
      {portalMenu}
      <div className="dl-table-scroll">
        <div className="dl-head">
          <span className="dl-col-status" aria-hidden="true" />
          <span className="dl-col-name">视频标题</span>
          <span className="dl-col-progress">进度</span>
          <span className="dl-col-time">时间</span>
          <span className="dl-col-menu" aria-hidden="true" />
        </div>

        {filteredTasks.length === 0 ? (
          <div className="dl-empty">
            <div className="dl-empty-icon">
              <svg viewBox="0 0 80 72" fill="none">
                <rect x="8" y="20" width="64" height="44" rx="6" fill="rgba(255,255,255,.12)" />
                <path
                  d="M8 32a6 6 0 016-6h10l4 5h32a6 6 0 016 6v24a6 6 0 01-6 6H14a6 6 0 01-6-6z"
                  fill="rgba(255,255,255,.18)"
                />
                <path
                  d="M12 36h56v24a6 6 0 01-6 6H18a6 6 0 01-6-6V42a6 6 0 016-6z"
                  fill="rgba(255,255,255,.08)"
                />
                <path d="M18 14h10l4 5H18z" fill="rgba(255,255,255,.14)" />
                <path d="M36 52v8M32 56h8" stroke="rgba(52,210,230,.6)" strokeWidth="2" strokeLinecap="round" />
                <path d="M36 44v4" stroke="rgba(52,210,230,.4)" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M36 44c0-1.5 1-3 2.5-3" stroke="rgba(52,210,230,.4)" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M36 44c0-1.5-1-3-2.5-3" stroke="rgba(52,210,230,.4)" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
            <p>暂无任务</p>
          </div>
        ) : (
          filteredTasks.map((task, index) => {
            const isSelected = multi ? selectedIds.has(task.id) : selectedTaskId === task.id
            const isPrimary = selectedTaskId === task.id
            return (
              <div
                key={task.id}
                className={`dl-row ${isSelected ? 'dl-row--selected' : ''} ${isPrimary ? 'dl-row--focused' : ''}`}
                onClick={(event) => onRowClick(task.id, index, event)}
              >
                <span className="dl-col-status" aria-hidden="true">
                  <StatusIcon status={task.status} />
                </span>
                <span className="dl-col-name">
                  <strong>{getTaskDisplayTitle(task)}</strong>
                  {task.status !== 'completed' && <small>{task.stage?.trim() || '-'}</small>}
                </span>
                <span className="dl-col-progress">
                  <div className="dl-progress-bar">
                    <div
                      className="dl-progress-fill"
                      style={{ width: `${Math.min(100, Math.max(0, task.progress || 0))}%` }}
                    />
                  </div>
                  <span className="dl-progress-text">{(task.progress || 0).toFixed(1)}%</span>
                </span>
                <span className="dl-col-time">{formatRelativeTime(task.created_at)}</span>
                <span className="dl-col-menu">
                  <button
                    type="button"
                    className={`dl-row-menu-trigger ${menu?.task.id === task.id ? 'dl-row-menu-trigger--open' : ''}`}
                    aria-label="更多操作"
                    aria-expanded={menu?.task.id === task.id}
                    aria-haspopup="menu"
                    onClick={(event) => openMenuForTask(task, event)}
                  >
                    <VerticalDotsIcon />
                  </button>
                </span>
              </div>
            )
          })
        )}
      </div>
    </section>
  )
}

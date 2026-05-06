import { toMultilineString } from '@/apps/downloader/helpers'
import type { DetailRow, DownloadTask } from '@/apps/downloader/types'

type DownloaderDetailDrawerProps = {
  open: boolean
  selectedTask: DownloadTask | null
  detailRows: DetailRow[]
  detailRequest: string
  detailState: string
  detailResult: string
  actionError: string
  onClose: () => void
}

export function DownloaderDetailDrawer({
  open,
  selectedTask,
  detailRows,
  detailRequest,
  detailState,
  detailResult,
  actionError,
  onClose,
}: DownloaderDetailDrawerProps) {
  if (!open) return null

  return (
    <>
      <button type="button" className="dl-detail-scrim" aria-label="关闭任务详情" onClick={onClose} />
      <aside className="dl-detail-drawer dl-detail-drawer--open" aria-hidden={false}>
        <div className="dl-detail-panel">
          <div className="dl-detail-header">
            <div>
              <strong>任务详情</strong>
              <small>{selectedTask ? selectedTask.name : '点击一条任务查看详情'}</small>
            </div>
            {selectedTask && (
              <span className={`dl-detail-badge dl-detail-badge--${selectedTask.status}`}>
                {selectedTask.status}
              </span>
            )}
          </div>

          {actionError && <div className="dl-form-error">{actionError}</div>}

          {!selectedTask ? (
            <div className="dl-detail-empty">当前没有可展示的任务详情。</div>
          ) : (
            <div className="dl-detail-stack">
              <div className="dl-detail-card dl-detail-card--summary">
                {detailRows.map((row) => (
                  <div key={row.label} className="dl-detail-row">
                    <span>{row.label}</span>
                    <strong>{toMultilineString(row.value)}</strong>
                  </div>
                ))}
              </div>

              <div className="dl-detail-card dl-detail-card--snapshots">
                <div className="dl-detail-block">
                  <label>下载请求快照</label>
                  <pre>{detailRequest || '-'}</pre>
                </div>

                <div className="dl-detail-block">
                  <label>提交参数</label>
                  <pre>{toMultilineString(selectedTask.params)}</pre>
                </div>

                <div className="dl-detail-block">
                  <label>运行状态快照</label>
                  <pre>{detailState || '-'}</pre>
                </div>

                <div className="dl-detail-block">
                  <label>任务结果</label>
                  <pre>{detailResult || '-'}</pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

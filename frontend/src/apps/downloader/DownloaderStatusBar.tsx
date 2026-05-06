type DownloaderStatusBarProps = {
  detailOpen: boolean
  onToggleDetail: () => void
}

export function DownloaderStatusBar({ detailOpen, onToggleDetail }: DownloaderStatusBarProps) {
  return (
    <footer className="dl-status">
      <span className="dl-speed">
        ↓ 0 B/s (0 B) <span>|</span> ↑ 0 B/s (0 B)
      </span>
      <button type="button" className="dl-task-detail" onClick={onToggleDetail}>
        {detailOpen ? '收起详情' : '任务详情'}
      </button>
    </footer>
  )
}

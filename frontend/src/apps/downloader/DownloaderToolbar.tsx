import { DeleteIcon, PlusIcon, RetryIcon, SearchIcon, SelectAllIcon, StopIcon } from '@/apps/downloader/icons'

type DownloaderToolbarProps = {
  showAddForm: boolean
  onToggleAddForm: () => void
  canStopSelected: boolean
  onStopSelected: () => void
  canRetrySelected: boolean
  onRetrySelected: () => void
  canSelectAllVisible: boolean
  allVisibleSelected: boolean
  onToggleSelectAll: () => void
  canClearRecords: boolean
  clearRecordsTitle: string
  onClearRecords: () => void
  searchText: string
  onSearchTextChange: (value: string) => void
}

export function DownloaderToolbar({
  showAddForm,
  onToggleAddForm,
  canStopSelected,
  onStopSelected,
  canRetrySelected,
  onRetrySelected,
  canSelectAllVisible,
  allVisibleSelected,
  onToggleSelectAll,
  canClearRecords,
  clearRecordsTitle,
  onClearRecords,
  searchText,
  onSearchTextChange,
}: DownloaderToolbarProps) {
  const selectTitle = canSelectAllVisible
    ? allVisibleSelected
      ? '取消全选当前列表'
      : '全选当前列表'
    : '当前列表没有可选择的任务'

  return (
    <div className="dl-toolbar">
      <button className="dl-btn dl-btn--primary" onClick={onToggleAddForm}>
        <PlusIcon />
        {showAddForm ? '收起表单' : '添加任务'}
      </button>
      <button
        className="dl-btn"
        aria-label="stop-selected-downloads"
        disabled={!canStopSelected}
        onClick={onStopSelected}
        title={canStopSelected ? undefined : '只有等待中或下载中的任务可以停止'}
      >
        <StopIcon />
        停止
      </button>
      <button
        className="dl-btn"
        aria-label="retry-selected-downloads"
        disabled={!canRetrySelected}
        onClick={onRetrySelected}
        title={canRetrySelected ? undefined : '请选择已完成、已停止或失败的任务重新提交'}
      >
        <RetryIcon />
        重试
      </button>
      <button
        className="dl-btn"
        aria-label="select-all-downloads"
        disabled={!canSelectAllVisible}
        onClick={onToggleSelectAll}
        title={selectTitle}
      >
        <SelectAllIcon />
        {allVisibleSelected ? '取消' : '全选'}
      </button>
      <button
        className="dl-btn"
        aria-label="delete-download-records"
        disabled={!canClearRecords}
        onClick={onClearRecords}
        title={clearRecordsTitle}
      >
        <DeleteIcon />
        删除
      </button>
      <div className="dl-toolbar-spacer" />
      <div className="dl-search">
        <SearchIcon />
        <input value={searchText} onChange={(event) => onSearchTextChange(event.target.value)} placeholder="搜索标题或链接" />
      </div>
    </div>
  )
}

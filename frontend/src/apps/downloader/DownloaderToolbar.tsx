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
  hasBulkSelection: boolean
  canClearSelected: boolean
  canClearAllTerminal: boolean
  canClearRecords: boolean
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
  hasBulkSelection,
  canClearSelected,
  canClearAllTerminal,
  canClearRecords,
  onClearRecords,
  searchText,
  onSearchTextChange,
}: DownloaderToolbarProps) {
  const clearTitle = hasBulkSelection
    ? canClearSelected
      ? '清理当前选中的已完成、已停止和错误记录'
      : '当前选中的任务里没有可清理的记录'
    : canClearAllTerminal
      ? '清空全部已完成、已停止和错误记录'
      : '当前没有可清理的历史记录'

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
        {allVisibleSelected ? '取消全选' : '全选'}
      </button>
      <button
        className="dl-btn"
        aria-label="clear-all-download-records"
        disabled={!canClearRecords}
        onClick={onClearRecords}
        title={clearTitle}
      >
        <DeleteIcon />
        {hasBulkSelection ? '清理所选' : '全部清理'}
      </button>
      <div className="dl-toolbar-spacer" />
      <div className="dl-search">
        <SearchIcon />
        <input value={searchText} onChange={(event) => onSearchTextChange(event.target.value)} placeholder="搜索任务名称" />
      </div>
    </div>
  )
}

import { PLATFORM_OPTIONS } from '@/apps/downloader/constants'
import type { DownloadPlatform, PlatformOption } from '@/apps/downloader/types'

type DownloaderAddFormProps = {
  taskUrl: string
  taskPlatform: DownloadPlatform
  taskQuality: string
  taskSubtitles: boolean
  taskOutputDir: string
  selectedPlatform: PlatformOption
  addingTask: boolean
  submitError: string
  onTaskUrlChange: (value: string) => void
  onTaskPlatformChange: (value: DownloadPlatform) => void
  onTaskQualityChange: (value: string) => void
  onTaskSubtitlesChange: (value: boolean) => void
  onTaskOutputDirChange: (value: string) => void
  onOpenDirectoryPicker: () => void
  onSubmit: () => void
  onClose: () => void
}

export function DownloaderAddForm({
  taskUrl,
  taskPlatform,
  taskQuality,
  taskSubtitles,
  taskOutputDir,
  selectedPlatform,
  addingTask,
  submitError,
  onTaskUrlChange,
  onTaskPlatformChange,
  onTaskQualityChange,
  onTaskSubtitlesChange,
  onTaskOutputDirChange,
  onOpenDirectoryPicker,
  onSubmit,
  onClose,
}: DownloaderAddFormProps) {
  return (
    <div className="dl-add-form">
      <div className="dl-field">
        <label>下载链接</label>
        <textarea
          value={taskUrl}
          onChange={(event) => onTaskUrlChange(event.target.value)}
          placeholder={'输入视频 URL（YouTube、Bilibili 等）\n支持多行，每行一个链接'}
          rows={4}
          style={{ resize: 'vertical', minHeight: '80px' }}
        />
      </div>

      <div className="dl-form-row">
        <div className="dl-field">
          <label>平台</label>
          <select value={taskPlatform} onChange={(event) => onTaskPlatformChange(event.target.value as DownloadPlatform)}>
            {PLATFORM_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <small className="dl-field-hint">{selectedPlatform.hint}</small>
        </div>
        <div className="dl-field">
          <label>质量</label>
          <select value={taskQuality} onChange={(event) => onTaskQualityChange(event.target.value)}>
            <option value="best">最佳可用</option>
            <option value="h264">优先 H.264</option>
          </select>
        </div>
      </div>

      <div className="dl-form-row">
        <div className="dl-field">
          <label>字幕</label>
          <select
            value={String(selectedPlatform.supportsSubtitles ? taskSubtitles : false)}
            disabled={!selectedPlatform.supportsSubtitles}
            onChange={(event) => onTaskSubtitlesChange(event.target.value === 'true')}
          >
            {selectedPlatform.supportsSubtitles ? (
              <>
                <option value="true">下载字幕</option>
                <option value="false">仅视频</option>
              </>
            ) : (
              <option value="false">当前平台不提供字幕</option>
            )}
          </select>
          {!selectedPlatform.supportsSubtitles && (
            <small className="dl-field-hint">已自动切换为仅视频，适合大多数短视频平台。</small>
          )}
        </div>
      </div>

      <div className="dl-form-row">
        <div className="dl-field dl-field--path">
          <label>目标目录</label>
          <div className="dl-path-field">
            <button
              type="button"
              className={`dl-path-display ${taskOutputDir ? 'dl-path-display--filled' : ''}`}
              onClick={onOpenDirectoryPicker}
            >
              <span className="dl-path-display__label">{taskOutputDir || '留空则使用默认下载目录'}</span>
              <span className="dl-path-display__action">{taskOutputDir ? '更改' : '选择目录'}</span>
            </button>
            {taskOutputDir && (
              <button type="button" className="dl-btn dl-btn--ghost" onClick={() => onTaskOutputDirChange('')}>
                清空
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="dl-form-actions">
        <button className="dl-btn dl-btn--primary" onClick={onSubmit} disabled={addingTask || !taskUrl.trim()}>
          {addingTask ? '提交中...' : '确认添加'}
        </button>
        <button className="dl-btn" onClick={onClose}>
          取消
        </button>
      </div>
      {submitError && <div className="dl-form-error">{submitError}</div>}
    </div>
  )
}

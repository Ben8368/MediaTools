import type { CategoryKey, CategoryMeta, PlatformOption } from '@/apps/downloader/types'

export const PLATFORM_OPTIONS: PlatformOption[] = [
  {
    value: 'auto',
    label: '智能识别',
    hint: '按链接自动识别平台，优先使用当前可用的下载能力。',
    supportsSubtitles: true,
  },
  {
    value: 'youtube',
    label: 'YouTube / Shorts',
    hint: '适合 YouTube 视频与 Shorts，支持字幕提取。',
    supportsSubtitles: true,
  },
  {
    value: 'bilibili',
    label: 'Bilibili',
    hint: '保留常规视频下载与字幕。',
    supportsSubtitles: true,
  },
  {
    value: 'short_video',
    label: '短视频平台',
    hint: '抖音、快手、TikTok 等通常仅下载视频，不显示字幕选项。',
    supportsSubtitles: false,
  },
]

export const CATEGORY_MAP: Record<CategoryKey, CategoryMeta> = {
  all: { label: '全部', icon: 'grid', key: 'all' },
  downloading: { label: '下载中', icon: 'download', key: 'downloading' },
  completed: { label: '已完成', icon: 'check', key: 'completed' },
  paused: { label: '已停止', icon: 'pause', key: 'paused' },
  error: { label: '错误', icon: 'error', key: 'error' },
}

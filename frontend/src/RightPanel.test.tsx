import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RightPanel } from '@/RightPanel'

const apiMocks = vi.hoisted(() => ({
  cancelTask: vi.fn(),
  getSystemMetrics: vi.fn(),
}))

vi.mock('@/api', () => apiMocks)

describe('RightPanel task grouping', () => {
  beforeEach(() => {
    apiMocks.cancelTask.mockReset()
    apiMocks.getSystemMetrics.mockReset()
    apiMocks.getSystemMetrics.mockResolvedValue({
      runtime: { uptime_seconds: 10 },
      system: { cpu_percent: 1, memory_percent: 2, gpu_video_encode_percent: 0, gpu_video_encode_available: false },
      network: { upload: { text: '0 B/s' }, download: { text: '0 B/s' }, upload_bytes_per_sec: 0, download_bytes_per_sec: 0 },
      services: [],
      task_summary: { active_downloads: 2, total_download_records: 5 },
      tasks: [
        {
          id: 'task-1',
          name: 'Media download',
          source: 'https://example.com/a',
          type: 'download',
          status: 'pending',
          status_label: 'Pending',
          stage: 'Queued',
          progress: 0,
          can_cancel: true,
        },
        {
          id: 'task-2',
          name: 'Media download',
          source: 'https://example.com/b',
          type: 'download',
          status: 'running',
          status_label: 'Running',
          stage: 'Downloading',
          progress: 50,
          can_cancel: true,
        },
      ],
      log_mode: 'production',
    })
  })

  it('groups tasks by type and expands into detail view', async () => {
    render(<RightPanel />)

    expect(await screen.findByText('Media download')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Media download/i }))

    expect(await screen.findByRole('button', { name: /返回任务中心/i })).toBeInTheDocument()
    expect(screen.getByText('https://example.com/a')).toBeInTheDocument()
    expect(screen.getByText('https://example.com/b')).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole('button', { name: /停止/i })[0])
    await waitFor(() => {
      expect(apiMocks.cancelTask).toHaveBeenCalledWith('task-1')
    })
  })

  it('collapses services by default and expands backend module ids', async () => {
    apiMocks.getSystemMetrics.mockResolvedValue({
      runtime: { uptime_seconds: 10 },
      system: { cpu_percent: 1, memory_percent: 2, gpu_video_encode_percent: 0, gpu_video_encode_available: false },
      network: { upload: { text: '0 B/s' }, download: { text: '0 B/s' }, upload_bytes_per_sec: 0, download_bytes_per_sec: 0 },
      services: [
        { id: 'frontend', name: '前端', online: true, status: 'ready', runtime_status: 'online', availability_status: 'ready', mode: 'dev', mode_label: '开发' },
        { id: 'encoder', name: '编码转码', online: true, status: 'ready', detail: 'ffmpeg 7' },
        { id: 'wechat', name: '朋友圈生成', online: false, status: 'dep_missing' },
      ],
      tasks: [],
      log_mode: 'development',
    })

    render(<RightPanel />)

    expect(await screen.findByText('开发模式')).toBeInTheDocument()
    expect(screen.queryByText('1/2 在线')).not.toBeInTheDocument()
    expect(screen.queryByText('encoder')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /服务状态/i }))

    expect(await screen.findByText('encoder')).toBeInTheDocument()
    expect(screen.getByText('wechat_moments')).toBeInTheDocument()
    expect(screen.queryByText('frontend')).not.toBeInTheDocument()
    expect(screen.queryByText('wechat')).not.toBeInTheDocument()
    expect(screen.queryByText('编码转码')).not.toBeInTheDocument()
    expect(screen.queryByText('朋友圈生成')).not.toBeInTheDocument()
    expect(screen.queryByText('在线')).not.toBeInTheDocument()
    expect(screen.queryByText('离线')).not.toBeInTheDocument()
    expect(screen.queryByText('不可用')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /服务状态/i }))
    expect(screen.queryByText('encoder')).not.toBeInTheDocument()
  })
})

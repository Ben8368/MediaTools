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
})

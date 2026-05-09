import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { computeStats, DownloaderApp, isTaskCancellable } from '@/apps/DownloaderApp'

const apiMocks = vi.hoisted(() => ({
  cancelTask: vi.fn(),
  clearTaskRecords: vi.fn(),
  deleteTaskRecord: vi.fn(),
  getActiveTasks: vi.fn(),
  getWeeklyHistory: vi.fn(),
  runFetcherDownload: vi.fn(),
}))

const openWindowMock = vi.hoisted(() => vi.fn())

vi.mock('@/api', () => apiMocks)

vi.mock('@/windowStore', () => ({
  useWindowStore: (selector: (state: { openWindow: ReturnType<typeof vi.fn> }) => unknown) =>
    selector({ openWindow: openWindowMock }),
}))

vi.mock('@/apps/FileManagerApp', () => ({
  DirectoryPickerDialog: () => null,
}))

describe('DownloaderApp helpers', () => {
  it('marks only pending and running tasks as cancellable', () => {
    expect(isTaskCancellable({ status: 'pending' })).toBe(true)
    expect(isTaskCancellable({ status: 'running' })).toBe(true)
    expect(isTaskCancellable({ status: 'completed' })).toBe(false)
    expect(isTaskCancellable({ status: 'failed' })).toBe(false)
    expect(isTaskCancellable({ status: 'cancelled' })).toBe(false)
  })

  it('computes grouped task stats', () => {
    const stats = computeStats([
      { id: '1', type: 'download', name: 'pending', status: 'pending', progress: 0, stage: '', created_at: 1 },
      { id: '2', type: 'download', name: 'running', status: 'running', progress: 30, stage: '', created_at: 2 },
      { id: '3', type: 'download', name: 'done', status: 'completed', progress: 100, stage: '', created_at: 3 },
      { id: '4', type: 'download', name: 'err', status: 'failed', progress: 100, stage: '', created_at: 4 },
      { id: '5', type: 'download', name: 'cancelled', status: 'cancelled', progress: 20, stage: '', created_at: 5 },
    ])

    expect(stats).toMatchObject({
      all: 5,
      downloading: 2,
      completed: 1,
      paused: 1,
      error: 1,
    })
  })
})

describe('DownloaderApp interactions', () => {
  beforeEach(() => {
    apiMocks.cancelTask.mockReset()
    apiMocks.clearTaskRecords.mockReset()
    apiMocks.deleteTaskRecord.mockReset()
    apiMocks.getActiveTasks.mockReset()
    apiMocks.getWeeklyHistory.mockReset()
    apiMocks.runFetcherDownload.mockReset()
    apiMocks.getWeeklyHistory.mockResolvedValue({ tasks: [] })
    apiMocks.clearTaskRecords.mockResolvedValue({ ok: true })
    apiMocks.deleteTaskRecord.mockResolvedValue({ ok: true })
  })

  it('stops selected active tasks through the cancel endpoint', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({
      tasks: [
        {
          id: 'task-1',
          type: 'download',
          name: 'Example download',
          status: 'running',
          progress: 40,
          stage: 'downloading',
          created_at: 1710000000,
        },
      ],
    })
    apiMocks.cancelTask.mockResolvedValue({ ok: true })

    render(<DownloaderApp />)

    expect((await screen.findAllByText('Example download')).length).toBeGreaterThan(0)

    fireEvent.click((await screen.findAllByText('Example download'))[0])

    const stopButton = screen.getByLabelText('stop-selected-downloads')
    expect(stopButton).toBeEnabled()

    fireEvent.click(stopButton)

    await waitFor(() => {
      expect(apiMocks.cancelTask).toHaveBeenCalledWith('task-1')
    })
  })

  it('shift-click extends selection across visible rows', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({
      tasks: [
        {
          id: 'task-a',
          type: 'download',
          name: 'Focused task',
          status: 'running',
          progress: 40,
          stage: 'downloading',
          created_at: 1710000000,
        },
        {
          id: 'task-b',
          type: 'download',
          name: 'Second task',
          status: 'pending',
          progress: 0,
          stage: 'queued',
          created_at: 1710000001,
        },
      ],
    })

    render(<DownloaderApp />)

    const rowA = (await screen.findAllByText('Focused task'))[0].closest('div.dl-row') as HTMLElement
    const rowB = (await screen.findAllByText('Second task'))[0].closest('div.dl-row') as HTMLElement
    fireEvent.click(rowA)
    expect(screen.getByLabelText('stop-selected-downloads')).toBeEnabled()

    fireEvent.click(rowB, { shiftKey: true })
    expect(screen.getByLabelText('select-all-downloads')).toHaveTextContent('取消')
  })

  it('keeps stop disabled for completed history tasks', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })
    apiMocks.getWeeklyHistory.mockResolvedValue({
      tasks: [
        {
          id: 'task-2',
          type: 'download',
          name: 'Finished download',
          status: 'completed',
          progress: 100,
          stage: 'done',
          created_at: 1710000000,
        },
      ],
    })

    render(<DownloaderApp />)

    fireEvent.click(await screen.findByRole('button', { name: /已完成/ }))
    expect((await screen.findAllByText('Finished download')).length).toBeGreaterThan(0)

    fireEvent.click((await screen.findAllByText('Finished download'))[0])
    expect(screen.getByLabelText('stop-selected-downloads')).toBeDisabled()
  })

  it('shows queue and weekly history together on the default all view', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })
    apiMocks.getWeeklyHistory.mockResolvedValue({
      tasks: [
        {
          id: 'task-history',
          type: 'download',
          name: 'Old completed download',
          status: 'completed',
          progress: 100,
          stage: 'done',
          created_at: 1710000000,
        },
      ],
    })

    render(<DownloaderApp />)

    await waitFor(() => {
      expect(apiMocks.getWeeklyHistory).toHaveBeenCalled()
    })
    expect(await screen.findByText('Old completed download')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /已完成/ }))
    expect(await screen.findByText('Old completed download')).toBeInTheDocument()
  })

  it('renders readable toolbar, empty state, and add-form labels', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })

    render(<DownloaderApp />)

    expect(await screen.findByText('暂无任务')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('搜索标题或链接')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '添加任务' })).toBeInTheDocument()
    expect(screen.getByText('停止')).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
    expect(screen.getByText('删除')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '添加任务' }))

    expect(screen.getByText('下载链接')).toBeInTheDocument()
    expect(screen.getByText('平台')).toBeInTheDocument()
    expect(screen.getByText('质量')).toBeInTheDocument()
    expect(screen.getByText('字幕')).toBeInTheDocument()
    expect(screen.getByText('目标目录')).toBeInTheDocument()
    expect(screen.getByText('智能识别')).toBeInTheDocument()
    expect(screen.getByText('最佳可用')).toBeInTheDocument()
    expect(screen.getByText('留空则使用默认下载目录')).toBeInTheDocument()
  })

  it('keeps short-video dropdown labels readable and disables subtitles', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })

    render(<DownloaderApp />)

    fireEvent.click(await screen.findByRole('button', { name: '添加任务' }))
    fireEvent.change(screen.getAllByRole('combobox')[0], {
      target: { value: 'short_video' },
    })

    expect(screen.getByText('短视频平台')).toBeInTheDocument()
    expect(screen.getByText('当前平台不提供字幕')).toBeInTheDocument()
    expect(screen.getByText('已自动切换为仅视频，适合大多数短视频平台。')).toBeInTheDocument()
  })

  it('shows a newly submitted task immediately in the queue', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })
    apiMocks.runFetcherDownload.mockResolvedValue({
      ok: true,
      task_id: 'task-new',
      status: 'pending',
    })

    render(<DownloaderApp />)

    fireEvent.click(await screen.findByRole('button', { name: '添加任务' }))
    fireEvent.change(document.querySelector('.dl-add-form textarea') as HTMLTextAreaElement, {
      target: { value: 'https://example.com/video' },
    })

    fireEvent.click(screen.getByRole('button', { name: '确认添加' }))

    await waitFor(() => {
      expect(apiMocks.runFetcherDownload).toHaveBeenCalled()
    })
    expect((await screen.findAllByText('https://example.com/video')).length).toBeGreaterThan(0)
  })

  it('turns subtitles off automatically for short video mode submissions', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })
    apiMocks.runFetcherDownload.mockResolvedValue({
      ok: true,
      task_id: 'task-short',
      status: 'pending',
    })

    render(<DownloaderApp />)

    fireEvent.click(await screen.findByRole('button', { name: '添加任务' }))
    fireEvent.change(screen.getAllByRole('combobox')[0], {
      target: { value: 'short_video' },
    })
    fireEvent.change(document.querySelector('.dl-add-form textarea') as HTMLTextAreaElement, {
      target: { value: 'https://example.com/short' },
    })
    fireEvent.click(screen.getByRole('button', { name: '确认添加' }))

    await waitFor(() => {
      expect(apiMocks.runFetcherDownload).toHaveBeenCalledWith(
        expect.objectContaining({
          url: 'https://example.com/short',
          platform: 'short_video',
          subtitles: false,
        }),
      )
    })
  })

  it('selects visible tasks from the current filtered list', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })
    apiMocks.getWeeklyHistory.mockResolvedValue({
      tasks: [
        {
          id: 'task-3',
          type: 'download',
          name: 'Broken download',
          status: 'failed',
          progress: 12,
          stage: 'failed',
          created_at: 1710000000,
        },
      ],
    })

    render(<DownloaderApp />)

    fireEvent.click(await screen.findByRole('button', { name: /错误/ }))
    await screen.findByText('Broken download')
    fireEvent.click(screen.getByLabelText('select-all-downloads'))
    expect(screen.getByLabelText('select-all-downloads')).toHaveTextContent('取消')
  })

  it('clears all visible terminal records when every visible row is selected', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })
    apiMocks.getWeeklyHistory.mockResolvedValue({
      tasks: [
        {
          id: 'task-5',
          type: 'download',
          name: 'Done A',
          status: 'completed',
          progress: 100,
          stage: 'done',
          created_at: 1710000000,
        },
        {
          id: 'task-6',
          type: 'download',
          name: 'Done B',
          status: 'failed',
          progress: 10,
          stage: 'failed',
          created_at: 1710000001,
        },
      ],
    })

    render(<DownloaderApp />)

    await screen.findByText('Done B')
    await screen.findByText('Done A')
    fireEvent.click(screen.getByLabelText('select-all-downloads'))
    fireEvent.click(screen.getByLabelText('delete-download-records'))

    await waitFor(() => {
      expect(apiMocks.clearTaskRecords).toHaveBeenCalledWith({
        ids: expect.arrayContaining(['task-5', 'task-6']),
        terminal_only: false,
      })
    })
    expect(apiMocks.clearTaskRecords.mock.calls[0]?.[0]?.ids).toHaveLength(2)
  })

  it('clears only the selected clearable records when a filtered list is selected', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({ tasks: [] })
    apiMocks.getWeeklyHistory.mockResolvedValue({
      tasks: [
        {
          id: 'task-7',
          type: 'download',
          name: 'Done selected',
          status: 'completed',
          progress: 100,
          stage: 'done',
          created_at: 1710000000,
        },
      ],
    })

    render(<DownloaderApp />)

    fireEvent.click(await screen.findByRole('button', { name: /已完成/ }))
    await screen.findByText('Done selected')
    fireEvent.click(screen.getByLabelText('select-all-downloads'))
    fireEvent.click(screen.getByLabelText('delete-download-records'))

    await waitFor(() => {
      expect(apiMocks.clearTaskRecords).toHaveBeenCalledWith({ ids: ['task-7'], terminal_only: false })
    })
  })

  it('renders task details for the focused row', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({
      tasks: [
        {
          id: 'task-4',
          type: 'download',
          name: 'https://www.youtube.com/watch?v=test',
          status: 'running',
          progress: 15,
          stage: '获取视频信息',
          created_at: 1710000000,
          params: {
            url: 'https://www.youtube.com/watch?v=test',
            output_dir: 'D:/Downloads',
            quality: 'best',
            subtitles: true,
          },
          result: {
            summary_text: 'working',
            items: [
              {
                info: {
                  title: 'Test Clip',
                  uploader: 'OpenAI',
                  local_path: 'D:/Downloads/test.mp4',
                },
              },
            ],
          },
        },
      ],
    })

    render(<DownloaderApp />)

    fireEvent.click((await screen.findAllByText('Test Clip'))[0])

    expect(screen.queryByText('下载请求快照')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '任务详情' }))

    expect(screen.getAllByText('Test Clip').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('POST /api/fetcher/download')).toBeInTheDocument()
  })

  it('keeps the detail drawer usable while the add form is open', async () => {
    apiMocks.getActiveTasks.mockResolvedValue({
      tasks: [
        {
          id: 'task-8',
          type: 'download',
          name: 'Overlay task',
          status: 'running',
          progress: 15,
          stage: 'downloading',
          created_at: 1710000000,
          params: {
            url: 'https://example.com/overlay',
          },
        },
      ],
    })

    render(<DownloaderApp />)

    fireEvent.click(await screen.findByRole('button', { name: '添加任务' }))
    fireEvent.click((await screen.findAllByText('Overlay task'))[0].closest('div.dl-row') as HTMLElement)

    fireEvent.click(screen.getByRole('button', { name: '任务详情' }))

    expect(screen.getByText('下载请求快照')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '确认添加' })).toBeInTheDocument()
  })
})



import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  AEApp,
  AgentApp,
  AssetsApp,
  AuditorApp,
  DashboardApp,
  DecryptorApp,
  EncoderApp,
  PhotoshopApp,
  WorkbenchApp,
  WorkspaceApp,
} from '@/apps/MediaToolsApps'

const apiMocks = vi.hoisted(() => ({
  addAERenderQueue: vi.fn(),
  analyzeWorkbenchSubtitle: vi.fn(),
  cancelTask: vi.fn(),
  cancelAEExecution: vi.fn(),
  clearTaskRecords: vi.fn(),
  cancelPhotoshopExecution: vi.fn(),
  createAECheckpoint: vi.fn(),
  deleteAETicket: vi.fn(),
  deletePhotoshopTicket: vi.fn(),
  executeAETicket: vi.fn(),
  executePhotoshopTicket: vi.fn(),
  exportWorkbenchClips: vi.fn(),
  fetchAECheckpoints: vi.fn(),
  fetchAEExecution: vi.fn(),
  fetchAERenderStatus: vi.fn(),
  fetchAEStatus: vi.fn(),
  fetchAETicket: vi.fn(),
  fetchAETickets: vi.fn(),
  fetchAuditorConfig: vi.fn(),
  fetchAuditorStatus: vi.fn(),
  fetchAssets: vi.fn(),
  fetchPhotoshopExecution: vi.fn(),
  fetchPhotoshopStatus: vi.fn(),
  fetchPhotoshopTicket: vi.fn(),
  fetchPhotoshopTickets: vi.fn(),
  fetchSystemFonts: vi.fn(),
  fetchWorkbenchMedia: vi.fn(),
  importAETicket: vi.fn(),
  importPhotoshopTicket: vi.fn(),
  getActiveTasks: vi.fn(),
  getModules: vi.fn(),
  getSystemStatus: vi.fn(),
  getWeeklyHistory: vi.fn(),
  getWorkspace: vi.fn(),
  runAuditorOnce: vi.fn(),
  runAgent: vi.fn(),
  runDecryptor: vi.fn(),
  runEncoder: vi.fn(),
  scanAEFolder: vi.fn(),
  scanAETicket: vi.fn(),
  scanPhotoshopFolder: vi.fn(),
  scanPhotoshopTicket: vi.fn(),
  setWorkspace: vi.fn(),
  startAERender: vi.fn(),
  updateAuditorConfig: vi.fn(),
  updateAETicket: vi.fn(),
  updatePhotoshopTicket: vi.fn(),
  wsUrl: vi.fn(),
}))

vi.mock('@/api', () => apiMocks)

vi.mock('@/apps/FileManagerApp', () => ({
  DirectoryPickerDialog: () => null,
}))

function resetApiMocks() {
  Object.values(apiMocks).forEach((mock) => mock.mockReset())
  apiMocks.addAERenderQueue.mockResolvedValue({ ok: true })
  apiMocks.analyzeWorkbenchSubtitle.mockResolvedValue({ ok: true, clips_json: '[]' })
  apiMocks.cancelTask.mockResolvedValue({ ok: true })
  apiMocks.cancelAEExecution.mockResolvedValue({ ok: true })
  apiMocks.clearTaskRecords.mockResolvedValue({ ok: true })
  apiMocks.cancelPhotoshopExecution.mockResolvedValue({ ok: true })
  apiMocks.createAECheckpoint.mockResolvedValue({ ok: true })
  apiMocks.deleteAETicket.mockResolvedValue({ ok: true, deleted: true })
  apiMocks.deletePhotoshopTicket.mockResolvedValue({ ok: true, deleted: true })
  apiMocks.executeAETicket.mockResolvedValue({ ok: true })
  apiMocks.executePhotoshopTicket.mockResolvedValue({ ok: true })
  apiMocks.exportWorkbenchClips.mockResolvedValue({ ok: true })
  apiMocks.fetchAECheckpoints.mockResolvedValue({ ok: true, checkpoints: [] })
  apiMocks.fetchAEExecution.mockResolvedValue({ ok: true, state: { status: 'done' } })
  apiMocks.fetchAERenderStatus.mockResolvedValue({ ok: true })
  apiMocks.fetchAEStatus.mockResolvedValue({ available: true, running_executions: 0, message: 'ready' })
  apiMocks.fetchAETicket.mockResolvedValue({ ok: true, ticket: { meta: { source_project: 'D:/demo.aep' }, tasks: [] } })
  apiMocks.fetchAETickets.mockResolvedValue({ ok: true, items: [] })
  apiMocks.fetchAuditorConfig.mockResolvedValue({ ok: true, config: { watch_folders: [], output_backend: 'local', enabled: false } })
  apiMocks.fetchAuditorStatus.mockResolvedValue({ available: true, module_status: 'staged' })
  apiMocks.fetchAssets.mockResolvedValue({ ok: true, items: [] })
  apiMocks.fetchPhotoshopExecution.mockResolvedValue({ ok: true, state: { status: 'done' } })
  apiMocks.fetchPhotoshopStatus.mockResolvedValue({ available: true, pywin32: true, running_executions: 0 })
  apiMocks.fetchPhotoshopTicket.mockResolvedValue({ ok: true, ticket: { meta: {}, tasks: [] } })
  apiMocks.fetchPhotoshopTickets.mockResolvedValue({
    ok: true,
    items: [{
      ticket_id: 'ps-old-1',
      task_count: 50,
      source_psd: 'D:/design/demo.psd',
      created_at: '2026-05-07T19:30:00',
      updated_at: 1778153400,
    }],
  })
  apiMocks.fetchSystemFonts.mockResolvedValue({ ok: true, items: [] })
  apiMocks.fetchWorkbenchMedia.mockResolvedValue({ ok: true, video_rows: [], subtitle_rows: [], export_rows: [] })
  apiMocks.importAETicket.mockResolvedValue({ ok: true, ticket_id: 'ae-import-1', ticket: { meta: {}, tasks: [] } })
  apiMocks.importPhotoshopTicket.mockResolvedValue({ ok: true, ticket_id: 'ps-import-1', ticket: { meta: {}, tasks: [] } })
  apiMocks.getActiveTasks.mockResolvedValue({ ok: true, tasks: [] })
  apiMocks.getModules.mockResolvedValue({ modules: [{ id: 'fetcher', name: '下载', desc: 'ready', status: 'online' }] })
  apiMocks.getSystemStatus.mockResolvedValue({ ok: true })
  apiMocks.getWeeklyHistory.mockResolvedValue({ ok: true, tasks: [] })
  apiMocks.getWorkspace.mockResolvedValue({ project_root: 'D:/MediaTools' })
  apiMocks.runAuditorOnce.mockResolvedValue({ ok: true })
  apiMocks.runAgent.mockResolvedValue({ ok: true, message: 'done' })
  apiMocks.runDecryptor.mockResolvedValue({ ok: true })
  apiMocks.runEncoder.mockResolvedValue({ ok: true })
  apiMocks.scanAEFolder.mockResolvedValue({ ok: true, ticket_id: 'ae-folder-1', ticket: { meta: {}, tasks: [] }, items: [] })
  apiMocks.scanAETicket.mockResolvedValue({ ok: true, ticket_id: 'ae-1', ticket: { meta: {}, tasks: [] } })
  apiMocks.scanPhotoshopFolder.mockResolvedValue({ ok: true, ticket_id: 'ps-folder-1', ticket: { meta: {}, tasks: [] }, items: [] })
  apiMocks.scanPhotoshopTicket.mockResolvedValue({ ok: true, ticket_id: 'ps-1', ticket: { meta: {}, tasks: [] } })
  apiMocks.setWorkspace.mockResolvedValue({ ok: true })
  apiMocks.startAERender.mockResolvedValue({ ok: true })
  apiMocks.updateAuditorConfig.mockResolvedValue({ ok: true, config: { watch_folders: [] } })
  apiMocks.updateAETicket.mockResolvedValue({ ok: true, ticket: { meta: {}, tasks: [] } })
  apiMocks.updatePhotoshopTicket.mockResolvedValue({ ok: true, ticket: { meta: {}, tasks: [] } })
  apiMocks.wsUrl.mockReturnValue('ws://localhost/ws/jobs')
}

describe('MediaTools utility apps', () => {
  beforeEach(resetApiMocks)

  it('renders the redesigned dashboard and loads module status', async () => {
    render(<DashboardApp />)

    expect(await screen.findByText('MediaTools Console')).toBeInTheDocument()
    expect(apiMocks.getModules).toHaveBeenCalled()
    expect(apiMocks.getWorkspace).toHaveBeenCalled()
  })

  it('renders Agent and submits a task through the API', async () => {
    render(<AgentApp />)

    expect(screen.getByRole('button', { name: '新建会话' })).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('例如：下载这个 YouTube 视频，转成 H.264，并把字幕转换成 SRT'), {
      target: { value: '整理今天下载的视频' },
    })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => {
      expect(apiMocks.runAgent).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByRole('button', { name: '新建会话' }))
    expect(screen.getByLabelText('删除会话 会话 2')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('删除会话 会话 2'))
    expect(screen.queryByText('会话 2')).not.toBeInTheDocument()
  })

  it('renders encoder, decryptor, assets, and workspace consoles', async () => {
    render(<EncoderApp />)
    expect(screen.getByText('Video Encoder')).toBeInTheDocument()

    render(<DecryptorApp />)
    expect(screen.getByRole('button', { name: /添加任务/ })).toBeInTheDocument()
    expect(screen.getByText('暂无解密任务')).toBeInTheDocument()

    render(<AssetsApp />)
    expect(await screen.findByText('Asset Library')).toBeInTheDocument()
    expect(apiMocks.fetchAssets).toHaveBeenCalled()

    render(<WorkspaceApp />)
    expect(await screen.findByText('工作区设置')).toBeInTheDocument()
    expect(apiMocks.getWorkspace).toHaveBeenCalled()
  })
})

describe('MediaTools workflow apps', () => {
  beforeEach(resetApiMocks)

  it('renders Photoshop and AE workflow pages with status calls', async () => {
    render(<PhotoshopApp />)
    expect(await screen.findByRole('button', { name: /扫描工单/ })).toBeInTheDocument()
    expect(apiMocks.fetchPhotoshopStatus).toHaveBeenCalled()

    render(<AEApp />)
    expect(await screen.findByRole('complementary', { name: 'After Effects 工单流程' })).toBeInTheDocument()
    expect(apiMocks.fetchAEStatus).toHaveBeenCalled()
  })

  it('creates Photoshop tickets without implicit languages and allows inline task edits', async () => {
    apiMocks.fetchSystemFonts.mockResolvedValueOnce({
      ok: true,
      items: [{ name: 'NotoSans' }, { name: 'NotoSans-SemiBold' }, { name: 'Arial Narrow Bold' }, { name: 'Inter' }],
    })
    apiMocks.scanPhotoshopTicket.mockResolvedValueOnce({
      ok: true,
      ticket_id: 'ps-1',
      ticket: {
        meta: { source_psd: 'demo.psd' },
        tasks: [{
          layer_name: 'Title',
          language: '',
          original_text: 'Hello',
          source_font: 'NotoSans',
          target_text: '',
          target_font: '',
          output_name: '',
          status: 'pending',
        }],
      },
    })

    render(<PhotoshopApp />)

    await screen.findByRole('button', { name: '扫描并生成工单' })
    expect(await screen.findByText('建立：2026-05-07 19:30')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '扫描并生成工单' }))

    await waitFor(() => {
      expect(apiMocks.scanPhotoshopTicket).toHaveBeenCalledWith(expect.objectContaining({
        psd_path: '',
        languages: [],
      }))
    })

    const replacement = await screen.findByLabelText('替换文本 1')
    const font = await screen.findByLabelText('目标字体 1')
    const output = screen.getByLabelText('输出名称 1')
    fireEvent.focus(font)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Inter' })).toBeInTheDocument()
    })
    expect(screen.getByText('Noto Sans')).toBeInTheDocument()
    fireEvent.change(replacement, { target: { value: 'New headline' } })
    fireEvent.change(font, { target: { value: 'Noto Sans Semi' } })
    fireEvent.click(screen.getByRole('option', { name: 'NotoSans-SemiBold' }))
    fireEvent.change(output, { target: { value: 'custom.psd' } })

    expect(replacement).toHaveValue('New headline')
    expect(font).toHaveValue('Noto Sans / SemiBold')
    expect(output).toHaveValue('custom.psd')

    fireEvent.focus(font)
    fireEvent.change(font, { target: { value: 'Arial Narrow' } })
    await waitFor(() => {
      expect(screen.getByText('Arial Narrow')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('option', { name: 'Arial Narrow Bold' }))
    expect(font).toHaveValue('Arial Narrow / Bold')
  })

  it('shows visible Photoshop scan progress while the backend request is pending', async () => {
    let resolveScan!: (value: unknown) => void
    const sockets: Array<{ onmessage: ((event: { data: string }) => void) | null, close: () => void }> = []
    class FakeWebSocket {
      onmessage: ((event: { data: string }) => void) | null = null
      close = vi.fn()

      constructor() {
        sockets.push(this)
      }
    }
    vi.stubGlobal('WebSocket', FakeWebSocket)
    apiMocks.scanPhotoshopTicket.mockReturnValueOnce(new Promise((resolve) => {
      resolveScan = resolve
    }))

    render(<PhotoshopApp />)

    const scanButton = await screen.findByRole('button', { name: '扫描并生成工单' })
    fireEvent.click(scanButton)

    expect(await screen.findByRole('status')).toHaveTextContent('扫描进行中')
    expect(screen.getByText(/正在连接 Photoshop/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '扫描中，请稍候...' })).toBeDisabled()
    await waitFor(() => {
      expect(sockets.length).toBe(1)
    })
    act(() => {
      sockets[0].onmessage?.({
        data: JSON.stringify({
          jobs: [{
            type: 'photoshop_scan',
            status: 'running',
            stage: '已发现 7 个文字层，正在扫描智能对象：Card',
            scan_layer_count: 7,
            scan_normal_text_layer_count: 4,
            scan_smart_text_layer_count: 3,
            scan_smart_object_count: 2,
          }],
        }),
      })
    })
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Photoshop 扫描计数')).getByText('智能对象文字')).toBeInTheDocument()
    expect(screen.getByText('已发现 7 个文字层，正在扫描智能对象：Card')).toBeInTheDocument()

    resolveScan({ ok: true, ticket_id: 'ps-progress-1', ticket: { meta: {}, tasks: [] } })
    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })
    vi.unstubAllGlobals()
  })

  it('uses the Photoshop language cart as the requested output set', async () => {
    apiMocks.scanPhotoshopTicket.mockResolvedValueOnce({
      ok: true,
      ticket_id: 'ps-1',
      ticket: {
        meta: { source_psd: 'demo.psd' },
        tasks: [
          {
            layer_name: 'Title',
            language: 'zh-CN',
            original_text: 'Hello',
            source_font: 'NotoSans',
            target_text: '',
            target_font: '',
            output_name: 'zh-CN.psd',
            status: 'pending',
          },
          {
            layer_name: 'Title',
            language: 'en-US',
            original_text: 'Hello',
            source_font: 'NotoSans',
            target_text: '',
            target_font: '',
            output_name: 'en-US.psd',
            status: 'pending',
          },
        ],
      },
    })

    render(<PhotoshopApp />)

    await screen.findByRole('button', { name: '扫描并生成工单' })
    fireEvent.change(screen.getByPlaceholderText('输入 zh-CN,en-US'), {
      target: { value: 'zh-CN,en-US' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: '添加' })[0])
    fireEvent.click(screen.getByRole('button', { name: '扫描并生成工单' }))

    await waitFor(() => {
      expect(apiMocks.scanPhotoshopTicket).toHaveBeenCalledWith(expect.objectContaining({
        psd_path: '',
        languages: ['zh-CN', 'en-US'],
      }))
    })
    expect(await screen.findByDisplayValue('zh-CN.psd')).toBeInTheDocument()
    expect(screen.getByDisplayValue('en-US.psd')).toBeInTheDocument()
  })

  it('shows Photoshop smart object task context and supports filtering with batch edits', async () => {
    apiMocks.fetchSystemFonts.mockResolvedValueOnce({
      ok: true,
      items: [{ name: 'Inter' }, { name: 'NotoSans-SemiBold' }],
    })
    apiMocks.scanPhotoshopTicket.mockResolvedValueOnce({
      ok: true,
      ticket_id: 'ps-smart-1',
      ticket: {
        meta: { source_psd: 'demo.psd' },
        tasks: [
          {
            layer_id: 1,
            layer_kind: 'text',
            layer_name: 'Title',
            artboard_name: 'Hero',
            language: '',
            original_text: 'Hello',
            source_font: 'NotoSans',
            target_text: '',
            target_font: '',
            output_name: '',
            status: 'pending',
          },
          {
            layer_id: 2,
            layer_kind: 'smart_object_text',
            smart_object_layer_id: 210,
            smart_object_name: 'Card',
            smart_object_inner_layer_name: 'Price',
            layer_name: 'Card / Price',
            artboard_name: 'Hero',
            language: '',
            original_text: '$9.99',
            source_font: 'NotoSans',
            target_text: '',
            target_font: '',
            output_name: '',
            status: 'pending',
          },
        ],
      },
    })

    render(<PhotoshopApp />)

    await screen.findByRole('button', { name: '扫描并生成工单' })
    fireEvent.click(screen.getByRole('button', { name: '扫描并生成工单' }))

    expect(await screen.findByText('智能对象：Card')).toBeInTheDocument()
    expect(screen.getByText('内部文字层：Price')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /智能对象内文字层/ }))
    fireEvent.change(screen.getByLabelText('搜索 Photoshop 任务'), { target: { value: 'Card' } })

    expect(screen.getByLabelText('替换文本 2')).toBeInTheDocument()
    expect(screen.queryByLabelText('替换文本 1')).not.toBeInTheDocument()

    const bulkFont = screen.getByLabelText('批量目标字体')
    fireEvent.focus(bulkFont)
    fireEvent.change(bulkFont, { target: { value: 'Inter' } })
    fireEvent.keyDown(bulkFont, { key: 'Enter' })
    fireEvent.click(screen.getByRole('button', { name: '批量设置字体' }))
    expect(screen.getByLabelText('目标字体 2')).toHaveValue('Inter / Regular')

    fireEvent.click(screen.getByRole('button', { name: '批量确认当前筛选' }))
    expect(screen.getByRole('checkbox')).toBeChecked()
  })

  it('renders workbench and auditor pages with backend configuration', async () => {
    render(<WorkbenchApp />)
    expect(await screen.findByText('Highlight Workbench')).toBeInTheDocument()
    expect(apiMocks.fetchWorkbenchMedia).toHaveBeenCalled()

    render(<AuditorApp />)
    expect(await screen.findByText('Asset Auditor')).toBeInTheDocument()
    expect(apiMocks.fetchAuditorStatus).toHaveBeenCalled()
    expect(apiMocks.fetchAuditorConfig).toHaveBeenCalled()
  })
})

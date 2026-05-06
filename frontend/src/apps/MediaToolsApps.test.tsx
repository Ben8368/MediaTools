import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  apiMocks.fetchPhotoshopTickets.mockResolvedValue({ ok: true, items: [] })
  apiMocks.fetchSystemFonts.mockResolvedValue({ ok: true, items: [] })
  apiMocks.fetchWorkbenchMedia.mockResolvedValue({ ok: true, video_rows: [], subtitle_rows: [], export_rows: [] })
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
    expect(await screen.findByText('Photoshop 自动化')).toBeInTheDocument()
    expect(apiMocks.fetchPhotoshopStatus).toHaveBeenCalled()

    render(<AEApp />)
    expect(await screen.findByText('After Effects 自动化')).toBeInTheDocument()
    expect(apiMocks.fetchAEStatus).toHaveBeenCalled()
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

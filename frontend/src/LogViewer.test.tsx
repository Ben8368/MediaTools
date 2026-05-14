import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LogViewer } from '@/LogViewer'
import { useNotificationUnreadStore } from '@/notificationUnreadStore'

const apiMocks = vi.hoisted(() => ({
  clearLogs: vi.fn(),
  clearNotifications: vi.fn(),
  fetchLogMetadata: vi.fn(),
  fetchLogs: vi.fn(),
  getSystemMetrics: vi.fn(),
  getUnreadNotificationCount: vi.fn(),
  markAllNotificationsAsRead: vi.fn(),
}))

vi.mock('@/api', () => apiMocks)

describe('LogViewer', () => {
  beforeEach(() => {
    apiMocks.clearLogs.mockReset()
    apiMocks.clearNotifications.mockReset()
    apiMocks.fetchLogMetadata.mockReset()
    apiMocks.fetchLogs.mockReset()
    apiMocks.getSystemMetrics.mockReset()
    apiMocks.getUnreadNotificationCount.mockReset()
    apiMocks.markAllNotificationsAsRead.mockReset()

    apiMocks.clearNotifications.mockResolvedValue({ ok: true, unread_count: 0 })
    apiMocks.fetchLogMetadata.mockResolvedValue({ modules: ['api', 'tasks'] })
    apiMocks.fetchLogs.mockResolvedValue({
      ok: true,
      total: 2,
      page: 1,
      page_size: 50,
      items: [
        {
          level: 'INFO',
          module: 'api',
          time: '2026-04-30 22:40:00',
          user: 'system',
          event: '服务启动',
          message: 'MediaTools started',
        },
        {
          level: 'ERROR',
          module: 'tasks',
          time: '2026-04-30 22:41:00',
          message: 'Task failed',
        },
      ],
    })
    apiMocks.clearLogs.mockResolvedValue({ ok: true })
    apiMocks.getSystemMetrics.mockResolvedValue({ log_mode: 'development' })
    apiMocks.getUnreadNotificationCount.mockResolvedValue({ unread_count: 0 })
    apiMocks.markAllNotificationsAsRead.mockResolvedValue({ ok: true, unread_count: 0 })
    useNotificationUnreadStore.setState({ unreadNotificationCount: 0, cooldownUntil: 0 })
  })

  it('renders backend logs with level labels and module metadata', async () => {
    render(<LogViewer />)

    expect(await screen.findByText('日志')).toBeInTheDocument()
    expect(apiMocks.fetchLogs).toHaveBeenCalledWith(expect.objectContaining({ level: 'NOTICE' }))
    expect((await screen.findAllByText('通知')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('错误')).length).toBeGreaterThan(0)
    expect(screen.getByText('服务启动')).toBeInTheDocument()
    expect(screen.getByText('Task failed')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'api' })).toBeInTheDocument()
  })

  it('reloads logs when level and module filters change', async () => {
    render(<LogViewer />)

    await screen.findByText('服务启动')
    await screen.findByRole('option', { name: 'Debug' })
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'ERROR' } })
    fireEvent.change(selects[1], { target: { value: 'tasks' } })

    await waitFor(() => {
      expect(apiMocks.fetchLogs).toHaveBeenCalledWith(expect.objectContaining({
        level: 'ERROR',
        module: 'tasks',
        page: 1,
        page_size: 50,
      }))
    })
  })

  it('clears logs and reloads the table', async () => {
    render(<LogViewer />)

    await screen.findByText('服务启动')
    fireEvent.click(screen.getByRole('button', { name: /清空/ }))

    await waitFor(() => {
      expect(apiMocks.markAllNotificationsAsRead).toHaveBeenCalled()
      expect(apiMocks.clearNotifications).toHaveBeenCalled()
      expect(apiMocks.clearLogs).toHaveBeenCalled()
      expect(apiMocks.getUnreadNotificationCount).toHaveBeenCalled()
      expect(apiMocks.fetchLogs).toHaveBeenCalledTimes(2)
    })
  })

  it('sets a cooldown so polling does not overwrite the cleared count', async () => {
    useNotificationUnreadStore.setState({ unreadNotificationCount: 5 })
    render(<LogViewer />)

    await screen.findByText('服务启动')
    fireEvent.click(screen.getByRole('button', { name: /清空/ }))

    await waitFor(() => {
      expect(useNotificationUnreadStore.getState().unreadNotificationCount).toBe(0)
      expect(useNotificationUnreadStore.getState().cooldownUntil).toBeGreaterThan(Date.now())
    })

    apiMocks.getUnreadNotificationCount.mockClear()
    apiMocks.getUnreadNotificationCount.mockResolvedValue({ unread_count: 3 })
    await useNotificationUnreadStore.getState().pullUnreadNotificationCount()

    expect(useNotificationUnreadStore.getState().unreadNotificationCount).toBe(0)
  })
})

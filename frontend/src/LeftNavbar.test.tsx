import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LeftNavbar } from '@/LeftNavbar'
import { useNotificationUnreadStore } from '@/notificationUnreadStore'
import { useSystemStore } from '@/store'
import { useWindowStore } from '@/windowStore'

const apiMocks = vi.hoisted(() => ({
  getUnreadNotificationCount: vi.fn(),
  shutdownSystem: vi.fn(),
}))

vi.mock('@/api', () => apiMocks)

describe('LeftNavbar shutdown flow', () => {
  beforeEach(() => {
    apiMocks.getUnreadNotificationCount.mockReset()
    apiMocks.shutdownSystem.mockReset()
    apiMocks.getUnreadNotificationCount.mockResolvedValue({ unread_count: 0 })
    useNotificationUnreadStore.setState({ unreadNotificationCount: 0, cooldownUntil: 0 })
    useSystemStore.setState({ showLauncher: false, themeMode: 'dark', wallpaper: 2 })
    useWindowStore.setState({ windows: [], maxZ: 100 })
  })

  it('shows a shutdown confirmation state after backend shutdown succeeds', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    apiMocks.shutdownSystem.mockResolvedValue({ ok: true })

    render(<LeftNavbar />)

    fireEvent.click(screen.getByLabelText('power-menu'))
    fireEvent.click(screen.getByLabelText('shutdown-backend'))

    await waitFor(() => {
      expect(apiMocks.shutdownSystem).toHaveBeenCalledTimes(1)
    })
    expect(screen.getByText('MediaTools 已关闭')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新连接' })).toBeInTheDocument()

    confirmSpy.mockRestore()
  })

  it('shows unread badge when notification API reports a positive count', async () => {
    apiMocks.getUnreadNotificationCount.mockResolvedValue({ unread_count: 7 })

    render(<LeftNavbar />)

    await waitFor(() => {
      expect(screen.getByText('7')).toBeInTheDocument()
    })
  })

  it('opens logs through the shared window manager', () => {
    render(<LeftNavbar />)

    fireEvent.click(screen.getByTitle('日志'))

    expect(apiMocks.getUnreadNotificationCount).toHaveBeenCalled()

    expect(useWindowStore.getState().getWindowByType('logs')).toMatchObject({
      appType: 'logs',
      title: '日志',
      width: 960,
      height: 640,
    })
  })

  it('focuses, minimizes, and restores running app windows from the sidebar', () => {
    useWindowStore.getState().openWindow('fetcher')
    useWindowStore.getState().openWindow('agent')

    render(<LeftNavbar />)

    fireEvent.click(screen.getByTitle('下载'))
    const focusedFetcher = useWindowStore.getState().getWindowByType('fetcher')
    const agent = useWindowStore.getState().getWindowByType('agent')
    expect(focusedFetcher?.zIndex).toBeGreaterThan(agent?.zIndex ?? 0)

    fireEvent.click(screen.getByTitle('下载'))
    expect(useWindowStore.getState().getWindowByType('fetcher')?.isMinimized).toBe(true)

    fireEvent.click(screen.getByTitle('下载'))
    expect(useWindowStore.getState().getWindowByType('fetcher')?.isMinimized).toBe(false)
  })
})

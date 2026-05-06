import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LeftNavbar } from '@/LeftNavbar'
import { useSystemStore } from '@/store'
import { useWindowStore } from '@/windowStore'

const apiMocks = vi.hoisted(() => ({
  restartSystem: vi.fn(),
  shutdownSystem: vi.fn(),
}))

vi.mock('@/api', () => apiMocks)

vi.mock('@/LogViewer', () => ({
  LogViewer: () => null,
}))

describe('LeftNavbar shutdown flow', () => {
  beforeEach(() => {
    apiMocks.restartSystem.mockReset()
    apiMocks.shutdownSystem.mockReset()
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

  it('shows a restart confirmation state after backend restart succeeds', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    apiMocks.restartSystem.mockResolvedValue({ ok: true })

    render(<LeftNavbar />)

    fireEvent.click(screen.getByLabelText('power-menu'))
    fireEvent.click(screen.getByLabelText('restart-backend'))

    await waitFor(() => {
      expect(apiMocks.restartSystem).toHaveBeenCalledTimes(1)
    })
    expect(screen.getByText('MediaTools 正在重启')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新连接' })).toBeInTheDocument()

    confirmSpy.mockRestore()
  })
})

import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { WindowContainer } from '@/WindowContainer'
import { useWindowStore } from '@/windowStore'

const demoApp = vi.hoisted(() => ({
  id: 'demo',
  title: 'Demo App',
  label: 'Demo',
  icon: '/demo.png',
  component: () => <div>Demo app body</div>,
}))

vi.mock('@/appRegistry', () => ({
  appRegistry: [demoApp],
  getAppMetadata: (appId: string) => appId === demoApp.id ? demoApp : undefined,
  getRegisteredApp: (appId: string) => appId === demoApp.id ? demoApp : undefined,
  getLauncherApps: () => [demoApp],
}))

describe('WindowContainer', () => {
  beforeEach(() => {
    useWindowStore.setState({ windows: [], maxZ: 100 })
  })

  it('renders window content from the app registry', () => {
    useWindowStore.getState().openWindow('demo')

    render(<WindowContainer />)

    expect(screen.getByText('Demo App')).toBeInTheDocument()
    expect(screen.getByText('Demo app body')).toBeInTheDocument()
  })

  it('lets a newly registered app open through the shared window manager', () => {
    useWindowStore.getState().openWindow('demo')

    const [windowItem] = useWindowStore.getState().windows

    expect(windowItem).toMatchObject({
      appType: 'demo',
      title: 'Demo App',
      width: 960,
      height: 640,
      x: 160,
      y: 80,
    })
  })
})

import { create } from 'zustand'

import { getAppMetadata } from '@/appRegistry'
import { getWindowPreset } from '@/appPresentation'

export interface FnOSWindow {
  id: string
  appType: string
  title: string
  width: number
  height: number
  x: number
  y: number
  isMinimized: boolean
  isMaximized: boolean
  zIndex: number
}

interface WindowStore {
  windows: FnOSWindow[]
  maxZ: number
  openWindow: (appType: string, title?: string) => void
  closeWindow: (id: string) => void
  minimizeWindow: (id: string) => void
  maximizeWindow: (id: string) => void
  focusWindow: (id: string) => void
  dragWindow: (id: string, x: number, y: number) => void
  resizeWindow: (id: string, width: number, height: number) => void
  hasWindow: (appType: string) => boolean
  getWindowByType: (appType: string) => FnOSWindow | undefined
}

let counter = 0

export const useWindowStore = create<WindowStore>()((set, get) => ({
  windows: [],
  maxZ: 100,

  openWindow: (appType, title) => {
    const existing = get().getWindowByType(appType)
    if (existing) {
      if (existing.isMinimized) {
        set((s) => ({ windows: s.windows.map((w) => w.id === existing.id ? { ...w, isMinimized: false } : w) }))
      }
      get().focusWindow(existing.id)
      return
    }
    const count = get().windows.length
    const id = `w-${++counter}`
    const newZ = get().maxZ + 1
    const offset = (count % 5) * 30
    const preset = getWindowPreset(appType)
    const appTitle = title || getAppMetadata(appType)?.title || appType
    set((s) => ({
      windows: [...s.windows, {
        id,
        appType,
        title: appTitle,
        width: preset.width,
        height: preset.height,
        x: preset.x + offset,
        y: preset.y + offset,
        isMinimized: false,
        isMaximized: false,
        zIndex: newZ,
      }],
      maxZ: newZ,
    }))
  },

  closeWindow: (id) => set((s) => ({ windows: s.windows.filter((w) => w.id !== id) })),

  minimizeWindow: (id) => set((s) => ({
    windows: s.windows.map((w) => w.id === id ? { ...w, isMinimized: true } : w),
  })),

  maximizeWindow: (id) => set((s) => ({
    windows: s.windows.map((w) => w.id === id ? { ...w, isMaximized: !w.isMaximized } : w),
  })),

  focusWindow: (id) => set((s) => {
    const target = s.windows.find((w) => w.id === id)
    if (!target || target.zIndex === s.maxZ) return s
    const nz = s.maxZ + 1
    return { windows: s.windows.map((w) => w.id === id ? { ...w, zIndex: nz } : w), maxZ: nz }
  }),

  dragWindow: (id, x, y) => set((s) => ({
    windows: s.windows.map((w) => w.id === id && !w.isMaximized ? { ...w, x, y } : w),
  })),

  resizeWindow: (id, width, height) => set((s) => ({
    windows: s.windows.map((w) => w.id === id && !w.isMaximized ? { ...w, width, height } : w),
  })),

  hasWindow: (appType) => get().windows.some((w) => w.appType === appType),

  getWindowByType: (appType) => get().windows.find((w) => w.appType === appType),
}))

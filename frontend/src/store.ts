import { create } from 'zustand'

interface SystemStore {
  showLauncher: boolean
  themeMode: 'light' | 'dark'
  wallpaper: number
  setShowLauncher: (show: boolean) => void
  toggleLauncher: () => void
  setThemeMode: (mode: 'light' | 'dark') => void
  setWallpaper: (idx: number) => void
}

export const useSystemStore = create<SystemStore>()((set, get) => ({
  showLauncher: false,
  themeMode: 'dark',
  wallpaper: 2,
  setShowLauncher: (show) => set({ showLauncher: show }),
  toggleLauncher: () => set((s) => ({ showLauncher: !s.showLauncher })),
  setThemeMode: (themeMode) => set({ themeMode }),
  setWallpaper: (wallpaper) => set({ wallpaper }),
}))

declare global {
  interface DocumentElement extends HTMLElement {
    className: string
  }
}

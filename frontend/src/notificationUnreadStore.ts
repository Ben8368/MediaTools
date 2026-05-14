import { getUnreadNotificationCount } from '@/api'
import { create } from 'zustand'

const CLEAR_COOLDOWN_MS = 5000

interface NotificationUnreadStore {
  unreadNotificationCount: number
  cooldownUntil: number
  setUnreadNotificationCount: (count: number) => void
  setClearCooldown: () => void
  pullUnreadNotificationCount: () => Promise<void>
}

export const useNotificationUnreadStore = create<NotificationUnreadStore>((set, get) => ({
  unreadNotificationCount: 0,
  cooldownUntil: 0,
  setUnreadNotificationCount: (count) => set({ unreadNotificationCount: count }),
  setClearCooldown: () => set({ cooldownUntil: Date.now() + CLEAR_COOLDOWN_MS }),
  pullUnreadNotificationCount: async () => {
    if (Date.now() < get().cooldownUntil) return
    try {
      const data = await getUnreadNotificationCount()
      const raw = data?.unread_count ?? 0
      const n = typeof raw === 'number' ? raw : Number(raw)
      const count = Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : 0
      set({ unreadNotificationCount: count })
    } catch {
      set({ unreadNotificationCount: 0 })
    }
  },
}))

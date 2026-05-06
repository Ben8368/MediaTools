import { create } from 'zustand'

export interface ModelConfig {
  baseUrl: string
  model: string
  apiKey: string
}

interface ModelConfigStore {
  config: ModelConfig
  setConfig: (next: Partial<ModelConfig>) => void
}

export const useModelConfig = create<ModelConfigStore>()((set) => ({
  config: { baseUrl: '', model: '', apiKey: '' },
  setConfig: (next) =>
    set((s) => ({ config: { ...s.config, ...next } })),
}))

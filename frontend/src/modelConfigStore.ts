import { create } from 'zustand'

import { clearPersistedModelConfig, fetchPersistedModelConfig, savePersistedModelConfig } from '@/api'

export interface ModelConfig {
  baseUrl: string
  model: string
  apiKey: string
}

interface ModelConfigStore {
  config: ModelConfig
  hasSavedConfig: boolean
  isLoading: boolean
  saveConfig: (next: ModelConfig) => Promise<void>
  clearSavedConfig: () => Promise<void>
  loadConfig: () => Promise<void>
}

const emptyConfig: ModelConfig = { baseUrl: '', model: '', apiKey: '' }

function normalizeConfig(config: ModelConfig): ModelConfig {
  return {
    baseUrl: config.baseUrl.trim(),
    model: config.model.trim(),
    apiKey: config.apiKey.trim(),
  }
}

function hasConfigValue(config: ModelConfig) {
  return Boolean(config.baseUrl || config.model || config.apiKey)
}

async function fetchModelConfig(): Promise<ModelConfig> {
  try {
    const data = await fetchPersistedModelConfig()
    return normalizeConfig({
      baseUrl: String(data.baseUrl || ''),
      model: String(data.model || ''),
      apiKey: String(data.apiKey || ''),
    })
  } catch (err) {
    console.warn('Failed to load model config from server:', err)
    return emptyConfig
  }
}

async function persistModelConfig(config: ModelConfig): Promise<ModelConfig> {
  const data = await savePersistedModelConfig({
    baseUrl: config.baseUrl,
    model: config.model,
    apiKey: config.apiKey,
  })
  return normalizeConfig({
    baseUrl: String(data.baseUrl || ''),
    model: String(data.model || ''),
    apiKey: String(data.apiKey || ''),
  })
}

async function deleteModelConfigRemote(): Promise<void> {
  await clearPersistedModelConfig()
}

export const useModelConfig = create<ModelConfigStore>()((set) => ({
  config: emptyConfig,
  hasSavedConfig: false,
  isLoading: true,
  loadConfig: async () => {
    set({ isLoading: true })
    try {
      const config = await fetchModelConfig()
      set({ config, hasSavedConfig: hasConfigValue(config), isLoading: false })
    } catch (err) {
      console.error('Failed to load config:', err)
      set({ isLoading: false })
    }
  },
  saveConfig: async (next) => {
    const config = normalizeConfig(next)
    const saved = await persistModelConfig(config)
    set({ config: saved, hasSavedConfig: hasConfigValue(saved) })
  },
  clearSavedConfig: async () => {
    await deleteModelConfigRemote()
    set({ config: emptyConfig, hasSavedConfig: false })
  },
}))

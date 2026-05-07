import { create } from 'zustand'

const MODEL_CONFIG_STORAGE_KEY = 'mediatools.modelConfig'
const MODEL_API_KEY_SESSION_STORAGE_KEY = 'mediatools.modelConfig.apiKey'

export interface ModelConfig {
  baseUrl: string
  model: string
  apiKey: string
}

interface ModelConfigStore {
  config: ModelConfig
  hasSavedConfig: boolean
  saveConfig: (next: ModelConfig) => void
  clearSavedConfig: () => void
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

function readSessionApiKey() {
  try {
    return window.sessionStorage.getItem(MODEL_API_KEY_SESSION_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

function writeSessionApiKey(apiKey: string) {
  try {
    if (apiKey) {
      window.sessionStorage.setItem(MODEL_API_KEY_SESSION_STORAGE_KEY, apiKey)
    } else {
      window.sessionStorage.removeItem(MODEL_API_KEY_SESSION_STORAGE_KEY)
    }
  } catch {
    // Ignore storage failures; the in-memory config remains usable.
  }
}

function persistNonSecretConfig(config: ModelConfig) {
  const nonSecretConfig = {
    baseUrl: config.baseUrl,
    model: config.model,
  }
  if (!nonSecretConfig.baseUrl && !nonSecretConfig.model) {
    window.localStorage.removeItem(MODEL_CONFIG_STORAGE_KEY)
    return
  }
  window.localStorage.setItem(MODEL_CONFIG_STORAGE_KEY, JSON.stringify(nonSecretConfig))
}

function loadSavedConfig(): { config: ModelConfig; hasSavedConfig: boolean } {
  try {
    const raw = window.localStorage.getItem(MODEL_CONFIG_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) as Partial<ModelConfig> : {}
    const legacyApiKey = String(parsed.apiKey || '')
    const sessionApiKey = readSessionApiKey() || legacyApiKey
    const config = normalizeConfig({
      baseUrl: String(parsed.baseUrl || ''),
      model: String(parsed.model || ''),
      apiKey: sessionApiKey,
    })
    if (legacyApiKey) writeSessionApiKey(config.apiKey)
    persistNonSecretConfig(config)
    return { config, hasSavedConfig: hasConfigValue(config) }
  } catch {
    const config = normalizeConfig({ ...emptyConfig, apiKey: readSessionApiKey() })
    return { config, hasSavedConfig: hasConfigValue(config) }
  }
}

function persistConfig(config: ModelConfig) {
  try {
    persistNonSecretConfig(config)
    writeSessionApiKey(config.apiKey)
  } catch {
    writeSessionApiKey(config.apiKey)
  }
  return hasConfigValue(config)
}

function removePersistedConfig() {
  try {
    window.localStorage.removeItem(MODEL_CONFIG_STORAGE_KEY)
  } catch {
    // Ignore storage failures; the in-memory config is still cleared.
  }
  writeSessionApiKey('')
}

const saved = loadSavedConfig()

export const useModelConfig = create<ModelConfigStore>()((set) => ({
  config: saved.config,
  hasSavedConfig: saved.hasSavedConfig,
  saveConfig: (next) => {
    const config = normalizeConfig(next)
    set({ config, hasSavedConfig: persistConfig(config) })
  },
  clearSavedConfig: () => {
    removePersistedConfig()
    set({ config: emptyConfig, hasSavedConfig: false })
  },
}))

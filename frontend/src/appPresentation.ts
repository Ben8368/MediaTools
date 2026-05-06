export type WindowPreset = {
  width: number
  height: number
  x: number
  y: number
}

export const WINDOW_CHROME = {
  minWidth: 400,
  minHeight: 300,
  offscreenGutter: 140,
  minTop: 8,
}

export const DEFAULT_WINDOW_PRESET: WindowPreset = {
  width: 960,
  height: 640,
  x: 160,
  y: 80,
}

export const APP_WINDOW_PRESETS: Record<string, WindowPreset> = {
  fetcher: DEFAULT_WINDOW_PRESET,
  agent: DEFAULT_WINDOW_PRESET,
  ps: DEFAULT_WINDOW_PRESET,
  photoshop: DEFAULT_WINDOW_PRESET,
  ae: DEFAULT_WINDOW_PRESET,
  decryptor: DEFAULT_WINDOW_PRESET,
  workbench: DEFAULT_WINDOW_PRESET,
  auditor: DEFAULT_WINDOW_PRESET,
  filebrowser: { width: 1008, height: 592, x: 304, y: 149 },
  settings: { width: 860, height: 560, x: 200, y: 100 },
}

export function getWindowPreset(appType: string) {
  return APP_WINDOW_PRESETS[appType] || DEFAULT_WINDOW_PRESET
}

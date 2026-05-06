export type WindowPreset = {
  width: number
  height: number
  x: number
  y: number
}

export const WINDOW_CHROME = {
  minWidth: 760,
  minHeight: 520,
  offscreenGutter: 140,
  minTop: 8,
}

export const DEFAULT_WINDOW_PRESET: WindowPreset = {
  width: 960,
  height: 640,
  x: 160,
  y: 80,
}

export function getWindowPreset(_appType: string) {
  return DEFAULT_WINDOW_PRESET
}

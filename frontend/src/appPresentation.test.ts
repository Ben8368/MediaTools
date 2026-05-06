import { describe, expect, it } from 'vitest'

import { appRegistry } from './appRegistry'
import { DEFAULT_WINDOW_PRESET, WINDOW_CHROME, getWindowPreset } from './appPresentation'

describe('app presentation presets', () => {
  it('uses one shared default preset for every registered desktop app', () => {
    appRegistry.forEach((app) => {
      expect(getWindowPreset(app.id)).toEqual(DEFAULT_WINDOW_PRESET)
    })
  })

  it('falls back to the shared default preset for unknown apps', () => {
    expect(getWindowPreset('unknown-app')).toEqual(DEFAULT_WINDOW_PRESET)
  })

  it('keeps window shell geometry in one shared chrome preset', () => {
    expect(WINDOW_CHROME).toEqual({
      minWidth: 760,
      minHeight: 520,
      offscreenGutter: 140,
      minTop: 8,
    })
  })
})

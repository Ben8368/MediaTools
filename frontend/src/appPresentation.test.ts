import { describe, expect, it } from 'vitest'

import { DEFAULT_WINDOW_PRESET, WINDOW_CHROME, getWindowPreset } from './appPresentation'

describe('app presentation presets', () => {
  it('keeps Adobe and workbench apps aligned with the downloader window size', () => {
    const downloader = getWindowPreset('fetcher')

    expect(getWindowPreset('agent')).toEqual(downloader)
    expect(getWindowPreset('ps')).toEqual(downloader)
    expect(getWindowPreset('photoshop')).toEqual(downloader)
    expect(getWindowPreset('ae')).toEqual(downloader)
    expect(getWindowPreset('decryptor')).toEqual(downloader)
    expect(getWindowPreset('workbench')).toEqual(downloader)
    expect(getWindowPreset('auditor')).toEqual(downloader)
  })

  it('falls back to the shared default preset for unknown apps', () => {
    expect(getWindowPreset('unknown-app')).toEqual(DEFAULT_WINDOW_PRESET)
  })

  it('keeps window shell geometry in one shared chrome preset', () => {
    expect(WINDOW_CHROME).toEqual({
      minWidth: 400,
      minHeight: 300,
      offscreenGutter: 140,
      minTop: 8,
    })
  })
})

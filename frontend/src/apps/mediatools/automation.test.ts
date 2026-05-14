import { describe, expect, it } from 'vitest'

import {
  automationTaskIndexes,
  isAutomationTaskExecutable,
  patchAutomationTask,
} from './automation'

describe('automation task helpers', () => {
  it('detects executable automation tasks (real text or font change only)', () => {
    expect(isAutomationTaskExecutable({ status: 'skip', target_text: 'hello' })).toBe(false)
    expect(isAutomationTaskExecutable({ status: 'confirmed', original_text: 'a', target_text: '' })).toBe(false)
    expect(isAutomationTaskExecutable({ status: 'ready', original_text: 'a', target_text: 'a' })).toBe(false)
    expect(isAutomationTaskExecutable({ original_text: 'a', target_text: 'b' })).toBe(true)
    expect(isAutomationTaskExecutable({ layer_name: 'Layer 1', target_text: 'edited' })).toBe(true)
    expect(isAutomationTaskExecutable({ target_font: 'Inter' })).toBe(true)
    expect(isAutomationTaskExecutable({ status: 'pending', original_text: 'x', target_text: '' })).toBe(false)
    expect(
      isAutomationTaskExecutable({ status: 'pending', original_text: 'Brand', target_text: '', preserve_copy: true }),
    ).toBe(true)
  })

  it('returns executable task indexes only', () => {
    expect(automationTaskIndexes([
      { status: 'pending', original_text: 'a', target_text: '' },
      { status: 'confirmed', original_text: 'a', target_text: 'b' },
      { target_text: 'replace me', layer_name: 'x' },
      { status: 'skip', target_font: 'Inter' },
    ])).toEqual([1, 2])
  })

  it('patches one task without mutating the original ticket', () => {
    const ticket = {
      ticket_id: 'demo',
      tasks: [
        { layer_name: 'title', target_text: 'old' },
        { layer_name: 'subtitle', target_text: 'keep' },
      ],
    }

    const nextTicket = patchAutomationTask(ticket, 0, { target_text: 'new', status: 'confirmed' })

    expect(nextTicket).toEqual({
      ticket_id: 'demo',
      tasks: [
        { layer_name: 'title', target_text: 'new', status: 'confirmed' },
        { layer_name: 'subtitle', target_text: 'keep' },
      ],
    })
    expect(ticket.tasks[0].target_text).toBe('old')
  })

  it('ignores invalid tickets', () => {
    expect(patchAutomationTask(null, 0, { status: 'confirmed' })).toBeNull()
    expect(patchAutomationTask({ ticket_id: 'bad' }, 0, { status: 'confirmed' })).toBeNull()
  })
})

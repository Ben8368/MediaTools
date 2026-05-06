import { describe, expect, it } from 'vitest'

import {
  automationTaskIndexes,
  isAutomationTaskExecutable,
  patchAutomationTask,
} from './automation'

describe('automation task helpers', () => {
  it('detects executable automation tasks', () => {
    expect(isAutomationTaskExecutable({ status: 'skip', target_text: 'hello' })).toBe(false)
    expect(isAutomationTaskExecutable({ status: 'confirmed' })).toBe(true)
    expect(isAutomationTaskExecutable({ status: 'ready' })).toBe(true)
    expect(isAutomationTaskExecutable({ target_text: 'hello' })).toBe(true)
    expect(isAutomationTaskExecutable({ target_font: 'Inter' })).toBe(true)
    expect(isAutomationTaskExecutable({ status: 'pending' })).toBe(false)
  })

  it('returns executable task indexes only', () => {
    expect(automationTaskIndexes([
      { status: 'pending' },
      { status: 'confirmed' },
      { target_text: 'replace me' },
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

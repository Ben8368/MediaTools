export type AutomationRecord = Record<string, any>

export function isAutomationTaskExecutable(task: AutomationRecord) {
  if (task.status === 'skip') return false
  if (['confirmed', 'ready', 'approved'].includes(task.status)) return true
  return Boolean(String(task.target_text || '').trim() || String(task.target_font || '').trim())
}

export function automationTaskIndexes(tasks: AutomationRecord[]) {
  return tasks
    .map((task, index) => isAutomationTaskExecutable(task) ? index : -1)
    .filter((index) => index >= 0)
}

export function patchAutomationTask(ticket: AutomationRecord | null, index: number, patch: AutomationRecord) {
  if (!ticket || !Array.isArray(ticket.tasks)) return null
  return {
    ...ticket,
    tasks: ticket.tasks.map((task: AutomationRecord, taskIndex: number) => (
      taskIndex === index ? { ...task, ...patch } : task
    )),
  }
}

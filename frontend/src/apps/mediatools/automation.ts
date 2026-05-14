export type AutomationRecord = Record<string, any>

export function isSmartObjectTask(task: AutomationRecord) {
  return task.layer_kind === 'smart_object_text' || Number(task.smart_object_layer_id || 0) > 0
}

/** 与 Photoshop 扫描一致：工单里「母版文案」来源，用于对照 target_text、Ai 翻译 Source */
export function taskEffectiveSourceText(task: AutomationRecord): string {
  const orig = task.original_text
  if (orig != null && String(orig).trim()) return String(orig)
  const raw = task.raw_text
  if (raw != null && String(raw).trim()) return String(raw)
  const smart = isSmartObjectTask(task)
  const layerFallback = String(smart ? (task.smart_object_inner_layer_name || task.layer_name) : task.layer_name || '').trim()
  return layerFallback
}

/** target_text 非空且与原文（规范化 trim）不同 → 视为用户或 Ai 改过文案，应参与执行 */
export function isTargetTextModifiedFromSource(task: AutomationRecord): boolean {
  const src = taskEffectiveSourceText(task).trim()
  const tgt = String(task.target_text ?? '').trim()
  if (!tgt) return false
  return tgt !== src
}

export function isAutomationTaskExecutable(task: AutomationRecord) {
  if (task.status === 'skip') return false
  if (Boolean(task.preserve_copy)) return true
  if (String(task.target_font || '').trim()) return true
  return isTargetTextModifiedFromSource(task)
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

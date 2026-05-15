/** Shared ticket/workorder state management for Photoshop and AE apps. */

import { useCallback, useMemo, useState } from 'react'
import {
  automationTaskIndexes,
  isAutomationTaskExecutable,
  patchAutomationTask,
  taskEffectiveSourceText,
} from '@/apps/mediatools/automation'
import type { AnyRecord } from '@/types'

// ── helpers ────────────────────────────────────────────────────────────────

function uniqueNumbers(items: number[]): number[] {
  return [...new Set(items)].sort((a, b) => a - b)
}

export function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

export function ticketWithOutputDir(ticket: AnyRecord, dir: string): AnyRecord {
  if (!ticket || typeof ticket !== 'object') return ticket
  const meta =
    ticket.meta && typeof ticket.meta === 'object' ? { ...(ticket.meta as AnyRecord), output_dir: dir } : { output_dir: dir }
  return { ...ticket, meta }
}

export function masterPsdStemForOutput(ticket: AnyRecord): string {
  const source = (typeof ticket?.meta?.source_psd === 'string' && ticket.meta.source_psd) || ''
  const name = source.split(/[/\\]/).pop() || ''
  const dot = name.lastIndexOf('.')
  return dot === -1 ? name : name.slice(0, dot)
}

// ── hook ───────────────────────────────────────────────────────────────────

export interface AutomationTicketApi {
  fetchStatus: () => Promise<AnyRecord>
  fetchTickets: () => Promise<{ items?: AnyRecord[] }>
  fetchTicket: (id: string) => Promise<{ ticket?: AnyRecord }>
  updateTicket: (id: string, ticket: AnyRecord) => Promise<{ ticket?: AnyRecord }>
  deleteTicket: (id: string) => Promise<AnyRecord>
  executeTicket: (id: string, dryRun: boolean, selected: number[]) => Promise<AnyRecord>
  cancelExecution: (id: string) => Promise<AnyRecord>
  fetchExecution: (id: string) => Promise<AnyRecord>
  scanDocument: (payload: AnyRecord) => Promise<AnyRecord>
  scanFolder: (payload: AnyRecord) => Promise<AnyRecord>
  cancelScan: () => Promise<AnyRecord>
  importTicket: (filePath: string, ticketId?: string) => Promise<AnyRecord>
}

export function useAutomationTicket(api: AutomationTicketApi) {
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [tickets, setTickets] = useState<AnyRecord[]>([])
  const [ticketId, setTicketId] = useState('')
  const [ticketText, setTicketText] = useState('')
  const [activePanel, setActivePanel] = useState<'scan' | 'import' | 'result'>('scan')
  const [selected, setSelected] = useState<number[]>([])
  const [result, setResult] = useState<unknown>('等待扫描或选择工单')
  const [execution, setExecution] = useState<unknown>('等待执行')
  const [isScanning, setIsScanning] = useState(false)
  const [scanJob, setScanJob] = useState<AnyRecord | null>(null)

  const parsedTicket = useMemo(() => {
    try {
      return JSON.parse(ticketText || '{}')
    } catch {
      return null
    }
  }, [ticketText])

  const tasks: AnyRecord[] = useMemo(() => {
    const t = Array.isArray(parsedTicket?.tasks) ? parsedTicket.tasks : []
    return t.map((task: AnyRecord) => {
      const src = taskEffectiveSourceText(task)
      return { ...task, original_text: src, raw_text: src }
    })
  }, [parsedTicket])

  const executableIndexSet = useMemo(
    () => new Set(automationTaskIndexes(tasks)),
    [tasks],
  )

  const selectedExecutableCount = useMemo(
    () => selected.reduce((count, index) => count + (executableIndexSet.has(index) ? 1 : 0), 0),
    [selected, executableIndexSet],
  )

  // ── ticket CRUD ──────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    const [statusData, ticketData] = await Promise.all([api.fetchStatus(), api.fetchTickets()])
    setStatus(statusData)
    setTickets(ticketData.items || [])
  }, [api])

  const loadTicket = useCallback(async (nextId: string) => {
    setActivePanel('import')
    setTicketId(nextId)
    const data = await api.fetchTicket(nextId)
    const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
    setTicket(data.ticket || null)
    setTicketText(JSON.stringify(data.ticket ?? {}, null, 2))
    setSelected(automationTaskIndexes(nextTasks))
    setResult(data)
    await refresh()
  }, [api, refresh])

  const deleteTicket = useCallback(async (nextId: string) => {
    await api.deleteTicket(nextId)
    if (ticketId === nextId) {
      setTicketId('')
      setTicketText('')
      setSelected([])
      setResult('工单已删除')
    }
    await refresh()
  }, [api, refresh, ticketId])

  const save = useCallback(async () => {
    const data = await api.updateTicket(ticketId, JSON.parse(ticketText || '{}'))
    const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
    setTicket(data.ticket || null)
    setSelected((items) => items.filter((index) => index < nextTasks.length))
    setResult(data)
    await refresh()
  }, [api, refresh, ticketId, ticketText])

  const saveAndExecute = useCallback(async (dryRun: boolean) => {
    await save()
    return execute(dryRun)
  }, [save])

  const importTicket = useCallback(async (filePath: string, id = '') => {
    const data = await api.importTicket(filePath, id)
    setResult(data)
    await refresh()
  }, [api, refresh])

  // ── selection ────────────────────────────────────────────────────────

  const updateTask = useCallback((index: number, patch: AnyRecord) => {
    const nextTicket = patchAutomationTask(parsedTicket, index, patch)
    if (!nextTicket) return
    setTicketText(JSON.stringify(nextTicket, null, 2))
  }, [parsedTicket])

  const updateTasks = useCallback((indexes: number[], patch: AnyRecord) => {
    if (!parsedTicket || !Array.isArray(parsedTicket.tasks)) return
    const indexSet = new Set(indexes)
    const nextTicket = {
      ...parsedTicket,
      tasks: parsedTicket.tasks.map((task: AnyRecord, i: number) =>
        indexSet.has(i) ? { ...task, ...patch } : task,
      ),
    } as AnyRecord
    setTicketText(JSON.stringify(nextTicket, null, 2))
  }, [parsedTicket])

  const toggleTask = useCallback((index: number, checked: boolean) => {
    setSelected((items) => {
      if (checked) return items.includes(index) ? items : [...items, index]
      return items.filter((item) => item !== index)
    })
  }, [])

  const saveTaskDialog = useCallback((index: number, patch: AnyRecord, checked: boolean) => {
    updateTask(index, patch)
    toggleTask(index, checked)
  }, [updateTask, toggleTask])

  const confirmTask = useCallback((index: number) => {
    updateTask(index, { status: 'confirmed' })
    toggleTask(index, true)
  }, [updateTask, toggleTask])

  const confirmVisibleTasks = useCallback((visibleIndexes: number[]) => {
    if (!visibleIndexes.length) return
    updateTasks(visibleIndexes, { status: 'confirmed' })
    setSelected((items) => uniqueNumbers([...items, ...visibleIndexes]))
  }, [updateTasks])

  const selectVisible = useCallback((visibleIndexes: number[]) => {
    const exe = visibleIndexes.filter((i) => executableIndexSet.has(i))
    setSelected(uniqueNumbers([...selected, ...exe]))
  }, [selected, executableIndexSet])

  // ── execution ────────────────────────────────────────────────────────

  const execute = useCallback(async (dryRun: boolean) => {
    if (!selected.length) {
      setExecution('请先勾选至少一个任务')
      return { ok: false, error: 'no tasks selected' }
    }
    if (!ticketId) return { ok: false, error: 'no ticket' }
    const currentTicketId = ticketId
    const started = await api.executeTicket(currentTicketId, dryRun, selected)
    setExecution(started)
    if (started?.ok !== false) {
      const finalState = await waitForExecution(currentTicketId)
      setExecution(finalState)
    }
    return started
  }, [api, selected, ticketId])

  const waitForExecution = useCallback(async (execTicketId: string) => {
    for (let i = 0; i < 720; i++) {
      try {
        const state = await api.fetchExecution(execTicketId)
        if (state && PHOTOSHOP_EXECUTION_TERMINAL_STATES.has(String((state as AnyRecord)?.state?.status))) {
          return state
        }
      } catch {
        // keep polling
      }
      await wait(3000)
    }
    await refresh()
    return { state: { status: 'done' } }
  }, [api, refresh])

  // ── scan ─────────────────────────────────────────────────────────────

  const scan = useCallback(async (psdPath: string, opts: AnyRecord = {}) => {
    if (isScanning) return
    setIsScanning(true)
    setScanJob(null)
    try {
      const data = await api.scanDocument({ psd_path: psdPath, ...opts })
      setScanJob(data)
      setResult(data)
    } catch {
      setResult({ ok: false, error: 'Scan failed' })
    } finally {
      setIsScanning(false)
    }
  }, [api, isScanning])

  const scanFolder = useCallback(async (directory: string, opts: AnyRecord = {}) => {
    if (isScanning) return
    setIsScanning(true)
    setScanJob(null)
    try {
      const data = await api.scanFolder({ directory, ...opts })
      setScanJob(data)
      setResult(data)
    } catch {
      setResult({ ok: false, error: 'Folder scan failed' })
    } finally {
      setIsScanning(false)
    }
  }, [api, isScanning])

  const cancelScan = useCallback(async () => {
    await api.cancelScan()
    setIsScanning(false)
    setScanJob(null)
  }, [api])

  return {
    // state
    status, setStatus,
    tickets,
    ticketId, setTicketId,
    ticketText, setTicketText,
    activePanel, setActivePanel,
    selected, setSelected,
    result, setResult,
    execution, setExecution,
    isScanning, setIsScanning,
    scanJob, setScanJob,
    // derived
    parsedTicket, tasks, executableIndexSet, selectedExecutableCount,
    // actions
    refresh, loadTicket, deleteTicket, save, saveAndExecute, importTicket,
    updateTask, updateTasks, toggleTask, saveTaskDialog,
    confirmTask, confirmVisibleTasks, selectVisible,
    execute, waitForExecution,
    scan, scanFolder, cancelScan,
  }
}

const PHOTOSHOP_EXECUTION_TERMINAL_STATES = new Set(['done', 'error', 'cancelled'])

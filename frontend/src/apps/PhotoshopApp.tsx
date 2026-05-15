import { memo, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  cancelPhotoshopExecution,
  cancelPhotoshopScan,
  deletePhotoshopTicket,
  executePhotoshopTicket,
  exportPhotoshopTicketJson,
  fetchPhotoshopExecution,
  fetchPhotoshopStatus,
  fetchPhotoshopTicket,
  fetchPhotoshopTickets,
  fetchSystemFonts,
  importPhotoshopTicket,
  scanPhotoshopFolder,
  scanPhotoshopTicket,
  translatePhotoshopCopy,
  updatePhotoshopTicket,
  wsUrl,
} from '@/api'
import { AiIcon } from '@/apps/downloader/icons'
import { DirectoryPickerDialog } from '@/apps/FileManagerApp'
import { CloseIcon } from '@/apps/file-manager/controls'
import { AutomationTaskDialog, AutomationTaskDialogMemo } from '@/apps/mediatools/AutomationTaskDialog'
import { FontPicker } from '@/apps/mediatools/FontPicker'
import { PhotoshopLocaleRequestDialog, type PhotoshopLocaleRequestResult } from '@/apps/mediatools/PhotoshopLocaleRequestDialog'
import { PsSavePathSummaryValue } from '@/apps/mediatools/PsSavePathSummaryValue'
import { PhotoshopMiniAiChat } from '@/apps/mediatools/PhotoshopMiniAiChat'
import {
  automationTaskIndexes,
  isAutomationTaskExecutable,
  isSmartObjectTask,
  patchAutomationTask,
  taskEffectiveSourceText,
} from '@/apps/mediatools/automation'
import {
  Field,
  PrimaryButton,
  ResultBox,
  ToolbarButton,
} from '@/apps/mediatools/primitives'
import { useModelConfig } from '@/modelConfigStore'
import type { AnyRecord } from '@/types'

type TaskFilter = 'all' | 'text' | 'smart_object_text' | 'pending' | 'ready' | 'warning'
type FilterCounts = Record<TaskFilter, number>
type TranslateUiState =
  | {
      mode: 'running'
      phase: 'model' | 'save' | 'refresh'
      count: number
      taskNos: string
      indexes: number[]
      localeSample: string
      textPreview: string
      textPreviewFull: string
    }
  | { mode: 'error'; message: string }
  | { mode: 'success'; message: string }
const PHOTOSHOP_EXECUTION_TERMINAL_STATES = new Set(['done', 'error', 'cancelled'])

/** 填入 Photoshop 助手输入框的快捷指令（发送前可改） */
const PS_AI_PROMPTS = {
  copycheck: '请检查当前工单中各任务的 target_text 相对 original_text：是否存在错别字、语病、术语不一致或与使用场景不符；按任务顺序给出问题与修改建议。',
} as const

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

/** 解析 POST /api/photoshop/translate-copy 返回的单条译文（兼容 index 为字符串、字段名为 t） */
function readTranslateCopyItem(row: AnyRecord): { index: number; text: string } | null {
  const rawIdx = row?.index ?? row?.i
  let idx: number
  if (typeof rawIdx === 'number' && Number.isFinite(rawIdx)) idx = rawIdx
  else {
    const n = Number(rawIdx)
    if (!Number.isFinite(n)) return null
    idx = n
  }
  const txt = row?.text ?? row?.t
  if (txt == null) return null
  return { index: idx, text: String(txt) }
}

function truncateForUi(text: string, maxChars: number): string {
  const t = String(text || '').replace(/\s+/g, ' ').trim()
  if (t.length <= maxChars) return t
  return `${t.slice(0, Math.max(0, maxChars - 1))}…`
}

/**
 * 从输出文件名最后一段推断语种（如 x_ja-JP.psd），仅作 task.language 为空时的筛选补充。
 */
function inferLocaleFromOutputName(outputName: unknown): string {
  const name = String(outputName || '').trim()
  if (!name) return ''
  const base = name.split(/[/\\]/).pop() || name
  const dot = base.lastIndexOf('.')
  const stem = dot === -1 ? base : base.slice(0, dot)
  const us = stem.lastIndexOf('_')
  if (us === -1 || us >= stem.length - 1) return ''
  const frag = stem.slice(us + 1)
  if (/^[a-z]{2}(-[A-Za-z0-9]+)*$/i.test(frag)) return frag
  return ''
}

function taskLocaleForListFilter(task: AnyRecord, resolve: (t: AnyRecord) => string): string {
  const direct = resolve(task).trim()
  if (direct) return direct
  return inferLocaleFromOutputName(task.output_name).trim()
}

function ExecutionSummary({ result, execution }: { result: any, execution: any }) {
  if (!result && !execution) return <div className="ps-empty">暂无执行记录。</div>
  
  return (
    <div className="ps-execution-summary">
       {result && (
         <div className="ps-execution-card">
           <h4>执行请求</h4>
           {result.ok ? <p className="success">请求已提交成功</p> : <p className="error">提交失败：{result.error || '未知错误'}</p>}
           {result.message && <p>{result.message}</p>}
         </div>
       )}
       {execution && typeof execution === 'string' ? (
         <div className="ps-execution-card"><p>{execution}</p></div>
       ) : execution && (
         <div className="ps-execution-card">
           <h4>执行状态</h4>
           <p>状态：{execution.state?.status || '未知'}</p>
           {execution.state?.progress !== undefined && <p>进度：{execution.state.progress}%</p>}
           {execution.state?.message && <p>{execution.state.message}</p>}
           {execution.state?.output_paths?.length > 0 && (
             <div>
               <p>输出文件：</p>
               {execution.state.output_paths.map((p: string, i: number) => (
                 <p key={i} style={{wordBreak: 'break-all', fontSize: '0.85em', opacity: 0.8}}>{p}</p>
               ))}
             </div>
           )}
         </div>
       )}
    </div>
  )
}

export function PhotoshopApp() {
  const { config: modelConfig } = useModelConfig()
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [activePanel, setActivePanel] = useState<'scan' | 'import' | 'result'>('scan')
  const [tickets, setTickets] = useState<AnyRecord[]>([])
  const [ticketId, setTicketId] = useState('')
  const [ticket, setTicket] = useState<AnyRecord | null>(null)
  const [ticketText, setTicketText] = useState('')
  const [ticketImportPath, setTicketImportPath] = useState('')
  const [sourceMode, setSourceMode] = useState<'file' | 'folder' | null>(null)
  const [psdPath, setPsdPath] = useState('')
  const [psdFolder, setPsdFolder] = useState('')
  const [targetLanguages, setTargetLanguages] = useState<string[]>([])
  const [selected, setSelected] = useState<number[]>([])
  const [editingTaskIndex, setEditingTaskIndex] = useState<number | null>(null)
  const [taskFilter, setTaskFilter] = useState<TaskFilter>('all')
  const [taskSearch, setTaskSearch] = useState('')
  /** 空字符串表示「全部」：批量字体/批量确认作用于当前列表筛选下的全部可见任务。 */
  const [bulkLocaleFilter, setBulkLocaleFilter] = useState('')
  const [bulkFont, setBulkFont] = useState('')
  const [fonts, setFonts] = useState<string[]>([])
  const [result, setResult] = useState<unknown>('等待扫描或选择工单')
  const [execution, setExecution] = useState<unknown>('等待执行')
  const [isScanning, setIsScanning] = useState(false)
  const [scanStartedAt, setScanStartedAt] = useState<number | null>(null)
  const [scanElapsedSec, setScanElapsedSec] = useState(0)
  const [scanJob, setScanJob] = useState<AnyRecord | null>(null)
  const [miniAiOpen, setMiniAiOpen] = useState(false)
  const psAppRootRef = useRef<HTMLDivElement>(null)
  const [localeRequestOpen, setLocaleRequestOpen] = useState(false)
  const [saveOutputDir, setSaveOutputDir] = useState('')
  const [savePathPickerOpen, setSavePathPickerOpen] = useState(false)
  /** 为 true 时：目录选择器确认后除保存工单外，还将 JSON 导出到所选目录 */
  const pendingExportAfterPathRef = useRef(false)
  /** 扫描来源：选择 PSD 文件 / 文件夹 时打开的目录或文件选择器 */
  const [scanSourcePicker, setScanSourcePicker] = useState<null | 'file' | 'directory'>(null)
  const [ticketImportPickerOpen, setTicketImportPickerOpen] = useState(false)
  const [translateBusy, setTranslateBusy] = useState(false)
  const [translateUi, setTranslateUi] = useState<TranslateUiState | null>(null)
  const translateOutcomeTimerRef = useRef<number | null>(null)
  const aiComposerNonceRef = useRef(0)
  const [aiComposerSeed, setAiComposerSeed] = useState<{ key: number; text: string } | null>(null)
  const clearAiComposerSeed = useCallback(() => setAiComposerSeed(null), [])
  const pushAiComposerText = useCallback((text: string) => {
    aiComposerNonceRef.current += 1
    setMiniAiOpen(true)
    setAiComposerSeed({ key: aiComposerNonceRef.current, text })
  }, [])

  const parsedTicket = ticket

  const tasks: AnyRecord[] = Array.isArray(parsedTicket?.tasks) ? parsedTicket.tasks : []

  const localeFallbacks = useMemo(() => {
    const meta = typeof ticket?.meta === 'object' && ticket.meta ? ticket.meta as AnyRecord : {}
    const metaLangs = Array.isArray(meta.target_languages) ? meta.target_languages.map((x: unknown) => String(x)) : []
    return uniqueStrings([...targetLanguages, ...metaLangs])
  }, [ticket, targetLanguages])

  const resolveTaskLocale = useCallback((task: AnyRecord): string => {
    const fromTask = String(task.language || '').trim()
    if (fromTask) return fromTask
    if (localeFallbacks.length === 1) return localeFallbacks[0]
    return ''
  }, [localeFallbacks])

  const bulkLocaleOptions = useMemo(() => {
    const acc = new Set<string>()
    for (const task of tasks) {
      const loc = taskLocaleForListFilter(task, resolveTaskLocale)
      if (loc) acc.add(loc)
    }
    return Array.from(acc).sort((a, b) => a.localeCompare(b))
  }, [tasks, resolveTaskLocale])

  useEffect(() => {
    setBulkLocaleFilter('')
  }, [ticketId])

  useEffect(() => {
    if (bulkLocaleFilter && !bulkLocaleOptions.includes(bulkLocaleFilter)) {
      setBulkLocaleFilter('')
    }
  }, [bulkLocaleFilter, bulkLocaleOptions])

  const translateAndPersist = useCallback(async (
    items: { index: number; text: string; locale: string }[],
    onPhase?: (phase: 'save' | 'refresh') => void,
  ): Promise<string> => {
    if (!ticketId || !parsedTicket) throw new Error('请先选择工单')
    const payload: Record<string, unknown> = { items }
    if (modelConfig.apiKey) payload.api_key = modelConfig.apiKey
    if (modelConfig.baseUrl) payload.base_url = modelConfig.baseUrl
    if (modelConfig.model) payload.model = modelConfig.model
    const data = await translatePhotoshopCopy(payload)
    if (!data?.ok) throw new Error(data?.error || '翻译失败')
    const byIndex = new Map<number, string>()
    for (const row of (data.items || []) as AnyRecord[]) {
      const parsed = readTranslateCopyItem(row)
      if (!parsed) continue
      byIndex.set(parsed.index, parsed.text)
    }
    if (items.length > 0 && byIndex.size === 0) {
      throw new Error('翻译响应无法解析（未得到任何 index/text），请检查网络或后端日志')
    }
    const sourceSnap = new Map(items.map((it) => [it.index, it.text.trim()]))
    const nextTasks = tasks.map((task: AnyRecord, index: number) => {
      const t = byIndex.get(index)
      if (t === undefined) return task
      const snap = sourceSnap.get(index)
      const out = String(t)
      /* Ai 写入：只要模型有返回即落库；若与发送给模型的原文 trim 相同再置空（视为未改） */
      if (snap !== undefined && out.trim() === snap) {
        return { ...task, target_text: '' }
      }
      return { ...task, target_text: out }
    })
    const nextTicket = { ...parsedTicket, tasks: nextTasks }
    onPhase?.('save')
    setTicket(nextTicket)
    const saved = await updatePhotoshopTicket(ticketId, ticketWithOutputDir(nextTicket, saveOutputDir))
    const savedTasks = Array.isArray(saved.ticket?.tasks) ? saved.ticket.tasks : []
    setTicket(saved.ticket || null)
    setTicketText('')
    setSelected((idxs) => idxs.filter((i) => i < savedTasks.length))
    const doneNums = [...byIndex.keys()].sort((a, b) => a - b).map((i) => i + 1).join('、')
    const successMsg = `已完成 ${byIndex.size} 条翻译并保存。任务序号：${doneNums}。请到下方任务列表查看各条「目标文案」是否已更新。`
    setResult({
      ok: true,
      message: successMsg,
    })
    onPhase?.('refresh')
    await refresh()
    return successMsg
  }, [modelConfig.apiKey, modelConfig.baseUrl, modelConfig.model, parsedTicket, refresh, saveOutputDir, tasks, ticketId])

  const runPhotoshopBulkTranslate = useCallback(async () => {
    if (!ticketId || !parsedTicket || !tasks.length) {
      setResult({ ok: false, error: '请先选择工单并确保有任务' })
      return
    }
    const items: { index: number; text: string; locale: string }[] = []
    tasks.forEach((task: AnyRecord, index: number) => {
      if (Boolean(task.preserve_copy)) return
      const text = taskEffectiveSourceText(task)
      if (!text.trim()) return
      const locale = resolveTaskLocale(task)
      if (!locale) return
      items.push({ index, text, locale })
    })
    if (!items.length) {
      setResult({
        ok: false,
        error: localeFallbacks.length > 1
          ? '没有可翻译的任务：多语言工单请在「语种需求」中为每行生成带 language 的任务，或为工单只保留一种目标语。'
          : '没有可翻译的任务：请确认各任务行有可译原文，并在「语种需求」中选择目标语。',
      })
      return
    }
    const indexes = items.map((x) => x.index)
    const taskNosHuman = items.length <= 14
      ? items.map((x) => x.index + 1).join('、')
      : `${items.slice(0, 14).map((x) => x.index + 1).join('、')} 等 ${items.length} 条`
    const localeLine = [...new Set(items.map((x) => x.locale))].join('、')
    const fullFirst = items[0].text
    if (translateOutcomeTimerRef.current != null) {
      window.clearTimeout(translateOutcomeTimerRef.current)
      translateOutcomeTimerRef.current = null
    }
    setTranslateUi({
      mode: 'running',
      phase: 'model',
      count: items.length,
      taskNos: taskNosHuman,
      indexes,
      localeSample: localeLine,
      textPreview: truncateForUi(fullFirst, 76),
      textPreviewFull: fullFirst,
    })
    setTranslateBusy(true)
    try {
      const successMsg = await translateAndPersist(items, (phase) => {
        setTranslateUi((prev) => (prev?.mode === 'running' ? { ...prev, phase } : prev))
      })
      setTranslateUi({ mode: 'success', message: successMsg })
      translateOutcomeTimerRef.current = window.setTimeout(() => {
        translateOutcomeTimerRef.current = null
        setTranslateUi((u) => (u?.mode === 'success' ? null : u))
      }, 6500)
    } catch (err: any) {
      const msg = err?.message || 'Ai 翻译失败'
      setResult({ ok: false, error: msg })
      setTranslateUi({ mode: 'error', message: msg })
    } finally {
      setTranslateBusy(false)
    }
  }, [localeFallbacks.length, parsedTicket, resolveTaskLocale, tasks, ticketId, translateAndPersist])

  const activeTicket = tickets.find((ticket) => ticket.ticket_id === ticketId)
  const sourcePsd = activeTicket?.source_psd || parsedTicket?.meta?.source_psd || ''
  const executableIndexes = useMemo(() => automationTaskIndexes(tasks), [tasks])
  const executableIndexSet = useMemo(() => new Set(executableIndexes), [executableIndexes])
  const selectedSet = useMemo(() => new Set(selected), [selected])
  const selectedExecutableCount = useMemo(
    () => selected.reduce((count, index) => count + (executableIndexSet.has(index) ? 1 : 0), 0),
    [selected, executableIndexSet],
  )
  const smartTaskCount = useMemo(() => tasks.filter(isSmartObjectTask).length, [tasks])
  const normalTaskCount = tasks.length - smartTaskCount
  /** 与扫描面板「已发现文字层」一致：普通文字层 + 智能对象内文字层（与下方两项同源，二者之和） */
  const scanTextLayerTotal = normalTaskCount + smartTaskCount
  const warningTaskCount = useMemo(() => tasks.filter(hasTaskWarning).length, [tasks])
  const filterCounts = useMemo(() => countTasksByFilter(tasks), [tasks])

  /** 实际扫描来源：有路径用路径；单文件/文件夹下路径留空则与「当前文档」相同 */
  const effectiveScanSource = useMemo((): 'active' | 'file' | 'folder' => {
    if (psdFolder.trim()) return 'folder'
    if (psdPath.trim()) return 'file'
    return 'active'
  }, [psdPath, psdFolder])

  const psAiContextLine = useMemo(() => {
    const lines: string[] = []
    if (status && typeof status === 'object') {
      const available = (status as AnyRecord).available === true
      lines.push(`桥接状态：${available ? '可用' : '不可用或未知'}`)
      const running = (status as AnyRecord).running_executions
      if (typeof running === 'number') lines.push(`进行中执行：${running}`)
    }
    lines.push(`当前工单：${ticketId || '（未选择）'}`)
    lines.push(`任务总数：${tasks.length}；已勾选：${selected.length}`)
    if (sourcePsd) lines.push(`源 PSD：${sourcePsd}`)
    const panelLabel = activePanel === 'scan' ? '扫描' : activePanel === 'import' ? '导入/编辑工单' : '执行结果'
    lines.push(`当前步骤：${panelLabel}`)
    if (targetLanguages.length) lines.push(`目标语言：${targetLanguages.join('、')}`)
    const saveDir = saveOutputDir.trim()
    if (saveDir) {
      lines.push(`计划输出目录（修改后 PSD）：${saveDir}`)
    } else {
      lines.push('输出目录：未指定，修改后的 PSD 默认保存在母版 PSD 同目录')
    }
    return lines.join('\n')
  }, [status, ticketId, tasks.length, selected.length, sourcePsd, activePanel, targetLanguages, saveOutputDir])

  const deferredTaskSearch = useDeferredValue(taskSearch)
  const filteredTaskEntries = useMemo(() => (
    tasks
      .map((task, index) => ({ task, index }))
      .filter(({ task }) => matchesTaskFilter(task, taskFilter))
      .filter(({ task }) => matchesTaskSearch(task, deferredTaskSearch))
  ), [tasks, taskFilter, deferredTaskSearch])

  /** 列表展示：在搜索/分类筛选之上，再按批量区「语种」下拉过滤（与批量设字体/确认范围一致）。 */
  const displayedTaskEntries = useMemo(() => {
    const key = bulkLocaleFilter.trim()
    if (!key) return filteredTaskEntries
    return filteredTaskEntries.filter(
      ({ task }) => taskLocaleForListFilter(task, resolveTaskLocale) === key,
    )
  }, [filteredTaskEntries, bulkLocaleFilter, resolveTaskLocale])

  const visibleIndexes = useMemo(() => displayedTaskEntries.map(({ index }) => index), [displayedTaskEntries])
  /** 批量改字体时排除「固定文案」任务 */
  const bulkFontTargetIndexes = useMemo(
    () => visibleIndexes.filter((i) => !Boolean(tasks[i]?.preserve_copy)),
    [visibleIndexes, tasks],
  )

  const updateTask = useCallback((index: number, patch: AnyRecord) => {
    setTicket((current) => patchAutomationTask(current, index, patch))
  }, [])

  function updateTasks(indexes: number[], patch: AnyRecord) {
    if (!parsedTicket || !Array.isArray(parsedTicket.tasks)) return
    const indexSet = new Set(indexes)
    const nextTicket = {
      ...parsedTicket,
      tasks: parsedTicket.tasks.map((task: AnyRecord, index: number) => (
        indexSet.has(index) ? { ...task, ...patch } : task
      )),
    }
    setTicket(nextTicket)
  }

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
  }, [toggleTask, updateTask])

  const closeTaskDialog = useCallback(() => setEditingTaskIndex(null), [])

  function confirmVisibleTasks() {
    if (!visibleIndexes.length) return
    updateTasks(visibleIndexes, { status: 'confirmed' })
    setSelected((items) => uniqueNumbers([...items, ...visibleIndexes]))
  }

  function applyBulkFontToVisibleTasks() {
    const font = bulkFont.trim()
    if (!font || !bulkFontTargetIndexes.length) return
    updateTasks(bulkFontTargetIndexes, { target_font: font })
  }

  async function handleLocaleRequestConfirm(result: PhotoshopLocaleRequestResult) {
    setLocaleRequestOpen(false)
    const fromCustom = result.customRaw
      .split(/[,\n，\s]+/)
      .map((item) => item.trim())
      .filter(Boolean)
    const additions = uniqueStrings([...result.presets.map((p) => p.bcp47), ...fromCustom])
    if (!additions.length) return

    const nextTargets = uniqueStrings([...targetLanguages, ...additions])
    setTargetLanguages(nextTargets)
    if (!ticketId || !parsedTicket || !tasks.length) return

    const nextTicket = rebuildTicketForLanguages(parsedTicket, nextTargets)
    if (!nextTicket) return
    const nextTaskList = Array.isArray(nextTicket.tasks) ? nextTicket.tasks : []
    setTicket(nextTicket)
    setTicketText('')
    setSelected(automationTaskIndexes(nextTaskList))
    try {
      const data = await updatePhotoshopTicket(ticketId, ticketWithOutputDir(nextTicket, saveOutputDir))
      const savedTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
      setTicket(data.ticket || null)
      setSelected((items) => items.filter((index) => index < savedTasks.length))
      setResult(data)
      await refresh()
    } catch (err: any) {
      setResult({ ok: false, error: err?.message || '保存多语言工单失败' })
    }
  }

  async function refresh() {
    const [statusData, ticketData] = await Promise.all([fetchPhotoshopStatus(), fetchPhotoshopTickets()])
    setStatus(statusData)
    setTickets(ticketData.items || [])
  }

  async function loadTicket(nextId: string) {
    setActivePanel('import')
    setTicketId(nextId)
    const data = await fetchPhotoshopTicket(nextId)
    const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
    setTicket(data.ticket || null)
    setTicketText('')
    setSaveOutputDir(String(data.ticket?.meta?.output_dir || ''))
    setTargetLanguages(uniqueStrings(nextTasks.map((task: AnyRecord) => task.language).filter(Boolean)))
    setSelected(automationTaskIndexes(nextTasks))
    setResult(data)
  }

  async function deleteTicket(nextId: string) {
    const data = await deletePhotoshopTicket(nextId)
    if (ticketId === nextId) {
      setTicketId('')
      setTicket(null)
      setTicketText('')
      setSelected([])
      setTargetLanguages([])
      setSaveOutputDir('')
    }
    setResult(data)
    await refresh()
  }

  async function scan() {
    if (isScanning) return
    setIsScanning(true)
    setScanStartedAt(Date.now())
    setScanElapsedSec(0)
    setScanJob(null)
    setResult({
      ok: null,
      status: 'scanning',
      message: 'Photoshop 正在扫描文本图层，请保持 Photoshop 打开；智能对象较多时会逐个打开和关闭。',
      source_mode: effectiveScanSource,
    })
    try {
      const data = effectiveScanSource === 'folder'
        ? await scanPhotoshopFolder({
            directory: psdFolder,
            languages: targetLanguages,
            recursive: true,
            max_files: 30,
          })
        : await scanPhotoshopTicket({
            psd_path: effectiveScanSource === 'file' ? psdPath : '',
            languages: targetLanguages,
          })
      setResult(data)
      if (data?.cancelled) {
        await refresh()
        return
      }
      if (data.ok) {
        const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
        const returnedLanguages = uniqueStrings(nextTasks.map((task: AnyRecord) => task.language).filter(Boolean))
        setTicketId(data.ticket_id)
      setTicket(data.ticket || null)
      setTicketText('')
      setSaveOutputDir(String(data.ticket?.meta?.output_dir || ''))
      setTargetLanguages(returnedLanguages.length || !targetLanguages.length ? returnedLanguages : targetLanguages)
        setSelected(automationTaskIndexes(nextTasks))
        setActivePanel('import')
        await refresh()
      }
    } catch (err: any) {
      setResult({ ok: false, status: 'error', error: err?.message || 'Photoshop 扫描失败' })
    } finally {
      setIsScanning(false)
      setScanStartedAt(null)
    }
  }

  async function cancelScan() {
    try {
      await cancelPhotoshopScan()
    } catch (err: any) {
      setResult({ ok: false, status: 'error', error: err?.message || '取消扫描失败' })
    }
  }

  async function importTicket() {
    if (!ticketImportPath) {
      setResult({ ok: false, error: '请先选择工单 JSON 文件' })
      return
    }
    try {
      const data = await importPhotoshopTicket(ticketImportPath)
      const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
      setTicketId(data.ticket_id)
      setTicket(data.ticket || null)
      setTicketText('')
      setSaveOutputDir(String(data.ticket?.meta?.output_dir || ''))
      setTargetLanguages(uniqueStrings(nextTasks.map((task: AnyRecord) => task.language).filter(Boolean)))
      setSelected(automationTaskIndexes(nextTasks))
      setActivePanel('import')
      setResult(data)
      await refresh()
    } catch (err: any) {
      setResult({ ok: false, error: err?.message || '导入工单失败' })
    }
  }

  async function persistTicket(outputDirOverride?: string): Promise<AnyRecord | null> {
    try {
      if (!ticket) throw new Error('当前没有可保存的工单')
      if (!ticketId) throw new Error('请先选择当前工单后再保存')
      const dir = outputDirOverride !== undefined ? outputDirOverride : saveOutputDir
      const data = await updatePhotoshopTicket(ticketId, ticketWithOutputDir(ticket, dir))
      const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
      setTicket(data.ticket || null)
      setTicketText('')
      setSelected((items) => items.filter((index) => index < nextTasks.length))
      setResult(data)
      await refresh()
      return data.ticket || null
    } catch (err: any) {
      setResult({ ok: false, error: err?.message || '保存失败，请检查工单 JSON 格式' })
      return null
    }
  }

  function activateOutputPathRow() {
    if (saveOutputDir.trim()) {
      if (!ticketId) {
        setResult({ ok: false, error: '请先选择当前工单后再保存' })
        return
      }
      void persistTicket()
      return
    }
    setSavePathPickerOpen(true)
  }

  async function handleSaveOutputDirPicked(path: string) {
    const runExport = pendingExportAfterPathRef.current
    pendingExportAfterPathRef.current = false
    setSaveOutputDir(path)
    if (!ticketId) return
    const saved = await persistTicket(path)
    if (!runExport || !saved) return
    try {
      const data = await exportPhotoshopTicketJson(ticketId, path, saved as Record<string, unknown>)
      if (!data?.ok) throw new Error(data?.error || '导出失败')
      setResult({
        ok: true,
        message: `工单 JSON 已保存到：${data.path}`,
      })
    } catch (err: any) {
      setResult({ ok: false, error: err?.message || '导出工单 JSON 失败' })
    }
  }

  async function exportTicketWithOutputPath() {
    if (!ticket || !ticketId) {
      setResult({ ok: false, error: '当前没有可导出的工单' })
      return
    }
    const dir = saveOutputDir.trim()
    if (!dir) {
      pendingExportAfterPathRef.current = true
      setSavePathPickerOpen(true)
      return
    }
    const saved = await persistTicket()
    if (!saved) return
    try {
      const data = await exportPhotoshopTicketJson(ticketId, dir, saved as Record<string, unknown>)
      if (!data?.ok) throw new Error(data?.error || '导出失败')
      setResult({
        ok: true,
        message: `工单 JSON 已保存到：${data.path}`,
      })
    } catch (err: any) {
      setResult({ ok: false, error: err?.message || '导出工单 JSON 失败' })
    }
  }

  async function execute(dryRun: boolean) {
    if (!selected.length) {
      setExecution('请先勾选至少一个任务')
      return
    }
    if (!ticketId) return
    const currentTicketId = ticketId
    try {
      setExecution(dryRun ? '正在保存工单并执行 Dry Run...' : '正在保存工单并执行，完成后会在 Photoshop 中打开输出 PSD...')
      if (!ticket) throw new Error('当前没有可执行的工单')
      const saved = await updatePhotoshopTicket(currentTicketId, ticketWithOutputDir(ticket, saveOutputDir))
      setTicket(saved.ticket || null)
      setTicketText('')
      setActivePanel('result')
      setResult(saved)
      const started = await executePhotoshopTicket(currentTicketId, dryRun, selected)
      setExecution(started)
      if (started?.ok !== false) {
        const finalState = await waitForPhotoshopExecution(currentTicketId)
        setExecution(finalState)
        try {
          const latest = await fetchPhotoshopTicket(currentTicketId)
          setTicket(latest.ticket || null)
          setTicketText('')
          setResult(latest)
        } catch {
          // Keep the execution state visible even if the final ticket reload fails.
        }
      }
      await refresh()
    } catch (err: any) {
      setExecution({ ok: false, error: err?.message || '执行失败，请检查工单内容' })
    }
  }

  async function waitForPhotoshopExecution(currentTicketId: string) {
    let latest: any = null
    for (let attempt = 0; attempt < 90; attempt += 1) {
      latest = await fetchPhotoshopExecution(currentTicketId)
      const status = String(latest?.state?.status || '')
      if (PHOTOSHOP_EXECUTION_TERMINAL_STATES.has(status)) return latest
      await wait(1000)
    }
    return latest || { ok: false, error: '执行状态轮询超时，请手动刷新执行状态' }
  }

  async function refreshExecution() {
    if (!ticketId) return
    try {
      setExecution(await fetchPhotoshopExecution(ticketId))
    } catch (err: any) {
      setExecution(err?.message || '未找到执行状态')
    }
  }

  useEffect(() => { void refresh() }, [])

  useEffect(() => () => {
    if (translateOutcomeTimerRef.current != null) {
      window.clearTimeout(translateOutcomeTimerRef.current)
      translateOutcomeTimerRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!isScanning || !scanStartedAt) return undefined
    const timer = window.setInterval(() => {
      setScanElapsedSec(Math.floor((Date.now() - scanStartedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [isScanning, scanStartedAt])

  useEffect(() => {
    if (!isScanning || typeof WebSocket === 'undefined') return undefined
    const socket = new WebSocket(wsUrl('/ws/jobs'))
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        const jobs = Array.isArray(payload?.jobs) ? payload.jobs : []
        const runningScan = jobs
          .filter((job: AnyRecord) => (
            ['photoshop_scan', 'photoshop_scan_folder'].includes(job.type)
            && ['pending', 'running'].includes(job.status)
          ))
          .at(-1)
        if (runningScan) {
          setScanJob(runningScan)
        }
      } catch {
        // Ignore malformed websocket frames; the local scan state still keeps the UI responsive.
      }
    }
    return () => socket.close()
  }, [isScanning])

  useEffect(() => {
    void fetchSystemFonts({ limit: 8000 }).then((data) => {
      const names = uniqueStrings((data.items || []).map((item: AnyRecord) => item.name).filter(Boolean))
      setFonts(names)
    }).catch(() => setFonts([]))
  }, [])

  return (
    <AppLayout>
      <div ref={psAppRootRef} className="ps-app">
        <aside className="ps-flow-sidebar" aria-label="Photoshop 工单流程">
          <div className="ps-flow-sidebar-steps">
            <button type="button" className={`ps-flow-step ${activePanel === 'scan' ? 'ps-flow-step--active' : ''}`} onClick={() => setActivePanel('scan')}>
              <span>01</span>
              <div>
                <strong>扫描工单</strong>
                <small>
                  {effectiveScanSource === 'active' ? '当前文档' : effectiveScanSource === 'file' ? '单文件扫描' : '文件夹批量扫描'}
                </small>
              </div>
            </button>
            <button type="button" className={`ps-flow-step ${activePanel === 'import' ? 'ps-flow-step--active' : ''}`} onClick={() => setActivePanel('import')}>
              <span>02</span>
              <div>
                <strong>导入工单</strong>
                <small>{ticketId ? `${ticketId.slice(0, 8)} · ${tasks.length} 个任务` : '扫描后自动导入当前工单'}</small>
                {sourcePsd ? <em>{sourcePsd}</em> : null}
              </div>
            </button>
            <button type="button" className={`ps-flow-step ${activePanel === 'result' ? 'ps-flow-step--active' : ''}`} onClick={() => setActivePanel('result')}>
              <span>03</span>
              <div>
                <strong>执行结果</strong>
                <small>{ticketId ? `${selectedExecutableCount} 个已选择` : '等待当前工单'}</small>
              </div>
            </button>
          </div>
          <div className="ps-flow-sidebar-bottom">
            <button
              type="button"
              className={`dl-nav-item ${miniAiOpen ? 'dl-nav-item--active' : ''}`}
              aria-pressed={miniAiOpen}
              onClick={() => setMiniAiOpen((open) => !open)}
            >
              <AiIcon />
              <span>AI 助手</span>
            </button>
          </div>
        </aside>

        <PhotoshopMiniAiChat
          open={miniAiOpen}
          onClose={() => setMiniAiOpen(false)}
          taskContextLine={psAiContextLine}
          composerSeed={aiComposerSeed}
          onComposerSeedConsumed={clearAiComposerSeed}
        />

        <PhotoshopLocaleRequestDialog
          open={localeRequestOpen}
          portalContainer={psAppRootRef.current}
          onClose={() => setLocaleRequestOpen(false)}
          onConfirm={handleLocaleRequestConfirm}
        />

        <DirectoryPickerDialog
          open={savePathPickerOpen}
          value={saveOutputDir}
          mode="directory"
          title="选择修改后 PSD 的保存目录"
          confirmLabel="确认"
          portalContainer={psAppRootRef.current}
          onClose={() => {
            setSavePathPickerOpen(false)
            pendingExportAfterPathRef.current = false
          }}
          onPick={handleSaveOutputDirPicked}
        />

        <DirectoryPickerDialog
          open={scanSourcePicker !== null}
          value={scanSourcePicker === 'directory' ? psdFolder : psdPath}
          mode={scanSourcePicker === 'directory' ? 'directory' : 'file'}
          title={scanSourcePicker === 'directory' ? '选择包含 PSD/PSB 的文件夹' : '选择 PSD 或 PSB 文件'}
          confirmLabel="确认"
          portalContainer={psAppRootRef.current}
          onClose={() => setScanSourcePicker(null)}
          onPick={(path) => {
            setScanSourcePicker((current) => {
              if (current === 'directory') setPsdFolder(path)
              else if (current === 'file') setPsdPath(path)
              return null
            })
          }}
        />

        <DirectoryPickerDialog
          open={ticketImportPickerOpen}
          value={ticketImportPath}
          mode="file"
          title="选择 Photoshop 工单 JSON 文件"
          confirmLabel="确认"
          portalContainer={psAppRootRef.current}
          onClose={() => setTicketImportPickerOpen(false)}
          onPick={(path) => {
            setTicketImportPath(path)
            setTicketImportPickerOpen(false)
          }}
        />

        <main className="ps-operation">
        <section className={`ps-panel ps-scan-panel ${activePanel === 'scan' ? '' : 'ps-panel--hidden'}`}>
          <div className="ps-section-head">
            <h3>PSD来源</h3>
          </div>
          <div className="ps-form-grid">
            <div className="ps-form-grid-span">
              <Field>
                <div className="ps-language-compact ps-save-path-compact ps-save-path-compact--scan-source">
                  <div className="ps-scan-source-unified">
                    <div
                      className={`ps-scan-mode-switch${isScanning ? ' ps-scan-mode-switch--disabled' : ''}`}
                      role="group"
                      aria-label="选择 PSD 扫描方式"
                    >
                      <button
                        type="button"
                        className="ps-scan-mode-switch__btn"
                        aria-pressed={sourceMode === 'file'}
                        disabled={isScanning}
                        onClick={() => {
                          setSourceMode('file')
                          setPsdFolder('')
                        }}
                      >
                        单文件
                      </button>
                      <button
                        type="button"
                        className="ps-scan-mode-switch__btn"
                        aria-pressed={sourceMode === 'folder'}
                        disabled={isScanning}
                        onClick={() => {
                          setSourceMode('folder')
                          setPsdPath('')
                        }}
                      >
                        文件夹批量
                      </button>
                    </div>
                    {sourceMode === null ? (
                      <div
                        className={`ps-scan-source-pane ps-scan-source-pane--readonly${isScanning ? ' ps-save-path-summary--disabled' : ''}`}
                        role="button"
                        tabIndex={isScanning ? -1 : 0}
                        aria-disabled={isScanning}
                        aria-label="点此选 PSD/PSB；批量请先点「文件夹批量」。无路径则扫描当前文档"
                        onClick={() => {
                          if (isScanning) return
                          setSourceMode('file')
                          setPsdFolder('')
                          setScanSourcePicker('file')
                        }}
                        onKeyDown={(event) => {
                          if (isScanning) return
                          if (event.key !== 'Enter' && event.key !== ' ') return
                          event.preventDefault()
                          setSourceMode('file')
                          setPsdFolder('')
                          setScanSourcePicker('file')
                        }}
                      >
                        <span className="ps-save-path-summary__value ps-save-path-summary__value--empty">
                          点此选 PSD/PSB；批量请先点「文件夹批量」。无路径则扫当前文档。
                        </span>
                      </div>
                    ) : sourceMode === 'file' ? (
                      <div
                        className={`ps-scan-source-pane ps-save-path-summary${isScanning ? ' ps-save-path-summary--disabled' : ''}`}
                        role="button"
                        tabIndex={isScanning ? -1 : 0}
                        aria-disabled={isScanning}
                        aria-label={
                          psdPath.trim()
                            ? `已选 PSD：${psdPath.trim()}，点此重新选择`
                            : '点此选择 PSD 或 PSB；未选路径则扫描 Photoshop 当前打开的文档'
                        }
                        onClick={(event) => {
                          if (isScanning) return
                          if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                          setScanSourcePicker('file')
                        }}
                        onKeyDown={(event) => {
                          if (isScanning) return
                          if (event.key !== 'Enter' && event.key !== ' ') return
                          if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                          event.preventDefault()
                          setScanSourcePicker('file')
                        }}
                      >
                        <PsSavePathSummaryValue
                          path={psdPath}
                          placeholder="点此选择 PSD/PSB；未选路径则扫描当前打开的文档"
                          title={psdPath.trim() || undefined}
                        />
                        {psdPath.trim() ? (
                          <button
                            type="button"
                            className="ps-save-path-summary__clear"
                            aria-label="清除已选 PSD 路径"
                            title="清除"
                            disabled={isScanning}
                            onClick={(event) => {
                              event.preventDefault()
                              event.stopPropagation()
                              setPsdPath('')
                              setSourceMode((m) => (!psdFolder.trim() ? null : m))
                            }}
                          >
                            <span aria-hidden={true}>
                              <CloseIcon />
                            </span>
                          </button>
                        ) : null}
                      </div>
                    ) : (
                      <div
                        className={`ps-scan-source-pane ps-save-path-summary${isScanning ? ' ps-save-path-summary--disabled' : ''}`}
                        role="button"
                        tabIndex={isScanning ? -1 : 0}
                        aria-disabled={isScanning}
                        aria-label={
                          psdFolder.trim()
                            ? `已选文件夹：${psdFolder.trim()}，点此重新选择`
                            : '点此选择文件夹；未选路径则扫描 Photoshop 当前打开的文档'
                        }
                        onClick={(event) => {
                          if (isScanning) return
                          if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                          setScanSourcePicker('directory')
                        }}
                        onKeyDown={(event) => {
                          if (isScanning) return
                          if (event.key !== 'Enter' && event.key !== ' ') return
                          if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                          event.preventDefault()
                          setScanSourcePicker('directory')
                        }}
                      >
                        <PsSavePathSummaryValue
                          path={psdFolder}
                          placeholder="点此选择包含 PSD/PSB 的文件夹；未选路径则扫描当前打开的文档"
                          title={psdFolder.trim() || undefined}
                        />
                        {psdFolder.trim() ? (
                          <button
                            type="button"
                            className="ps-save-path-summary__clear"
                            aria-label="清除已选文件夹路径"
                            title="清除"
                            disabled={isScanning}
                            onClick={(event) => {
                              event.preventDefault()
                              event.stopPropagation()
                              setPsdFolder('')
                              setSourceMode((m) => (!psdPath.trim() ? null : m))
                            }}
                          >
                            <span aria-hidden={true}>
                              <CloseIcon />
                            </span>
                          </button>
                        ) : null}
                      </div>
                    )}
                    <PrimaryButton
                      type="button"
                      className={`ps-scan-source-run${isScanning ? ' ps-scan-source-run--cancel' : ''}`}
                      aria-label={isScanning ? '取消扫描' : '点击扫描'}
                      onClick={() => void (isScanning ? cancelScan() : scan())}
                    >
                      {isScanning ? '取消扫描' : '点击扫描'}
                    </PrimaryButton>
                  </div>
                </div>
              </Field>
            </div>
          </div>
          {isScanning ? (
            <div className="ps-scan-progress" role="status" aria-live="polite">
              <div className="ps-scan-progress-top">
                <span>扫描进行中</span>
                <strong>{formatDuration(scanElapsedSec)}</strong>
              </div>
              <div className="ps-scan-progress-bar" aria-hidden="true"><span /></div>
              <div className="ps-scan-counts" aria-label="Photoshop 扫描计数">
                <span><b>{Number(scanJob?.scan_layer_count || 0)}</b> 已发现文字层</span>
                <span><b>{Number(scanJob?.scan_normal_text_layer_count || 0)}</b> 普通文字</span>
                <span><b>{Number(scanJob?.scan_smart_text_layer_count || 0)}</b> 智能对象文字</span>
                <span><b>{Number(scanJob?.scan_smart_object_count || 0)}</b> 已检查智能对象</span>
              </div>
              <p>{scanJob?.stage || scanProgressMessage(scanElapsedSec, effectiveScanSource)}</p>
              {scanJob?.scan_current_file ? (
                <small>当前文件：{scanJob.scan_current_file}（{scanJob.scan_file_index || 1}/{scanJob.scan_file_total || 1}）</small>
              ) : null}
              <small>看到 Photoshop 打开/关闭智能对象属于正常扫描过程，请不要手动切换或关闭文档。</small>
            </div>
          ) : null}
        </section>

        <div className={`ps-workspace ${activePanel === 'import' ? '' : 'ps-workspace--hidden'}`}>
          <section className="ps-panel ps-ticket-panel">
            <div className="ps-ticket-head">
              <div>
                <h3>{ticketId ? `当前工单：${ticketId}` : '导入工单'}</h3>
              </div>
            </div>

            <div className="ps-import-ticket-row">
              <Field>
                <div className="ps-language-compact ps-save-path-compact ps-save-path-compact--import-ticket">
                  <div className="ps-scan-source-unified">
                    <div className="ps-import-ticket-count-wrap">
                      <span className="ps-ticket-count-badge" aria-label={`${tickets.length} 个工单`}>
                        {tickets.length} 个工单
                      </span>
                    </div>
                    <div
                      className="ps-scan-source-pane ps-save-path-summary"
                      role="button"
                      tabIndex={0}
                      aria-label={
                        ticketImportPath.trim()
                          ? `已选工单文件：${ticketImportPath.trim()}，点此重新选择`
                          : '点此选择 Photoshop 工单 JSON 文件'
                      }
                      onClick={(event) => {
                        if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                        setTicketImportPickerOpen(true)
                      }}
                      onKeyDown={(event) => {
                        if (event.key !== 'Enter' && event.key !== ' ') return
                        if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                        event.preventDefault()
                        setTicketImportPickerOpen(true)
                      }}
                    >
                      <PsSavePathSummaryValue
                        path={ticketImportPath}
                        placeholder="选择工单 JSON（.json）"
                        title={ticketImportPath.trim() || undefined}
                      />
                      {ticketImportPath.trim() ? (
                        <button
                          type="button"
                          className="ps-save-path-summary__clear"
                          aria-label="清除已选工单文件路径"
                          title="清除"
                          onClick={(event) => {
                            event.preventDefault()
                            event.stopPropagation()
                            setTicketImportPath('')
                          }}
                        >
                          <span aria-hidden={true}>
                            <CloseIcon />
                          </span>
                        </button>
                      ) : null}
                    </div>
                    <PrimaryButton
                      type="button"
                      className="ps-scan-source-run"
                      aria-label="导入并设为当前工单"
                      onClick={() => void importTicket()}
                    >
                      导入工单
                    </PrimaryButton>
                  </div>
                </div>
              </Field>
            </div>

            <div className="ps-metrics ps-metrics--in-ticket" aria-label="扫描文字层分类与任务概况">
              <div
                className="ps-metric"
                title="来自扫描阶段：按文字层分类统计；数值等于「普通文字」与「智能对象文字」之和。"
              >
                <span>图层数量</span>
                <strong>{scanTextLayerTotal}</strong>
              </div>
              <div className="ps-metric"><span>普通文字</span><strong>{normalTaskCount}</strong></div>
              <div className="ps-metric"><span>智能对象文字</span><strong>{smartTaskCount}</strong></div>
              <div className="ps-metric"><span>可执行</span><strong>{executableIndexes.length}</strong></div>
            </div>

            <div className="ps-ticket-list">
              {tickets.length ? tickets.map((ticket) => (
                <div
                  className={`ps-ticket ${ticket.ticket_id === ticketId ? 'ps-ticket--active' : ''}`}
                  key={ticket.ticket_id}
                >
                  <button type="button" className="ps-ticket-main" onClick={() => void loadTicket(ticket.ticket_id)}>
                    <span className="ps-ticket-top">
                      <strong>{ticket.ticket_id?.slice(0, 8) || '未命名'}</strong>
                      <small>{ticket.task_count || 0} 个任务</small>
                      <span className="ps-ticket-time">建立：{formatTicketTime(ticket.created_at, ticket.updated_at)}</span>
                    </span>
                    <span className="ps-ticket-path" title={ticket.source_psd ? String(ticket.source_psd) : undefined}>
                      {ticket.source_psd || '未记录来源'}
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label={`删除工单 ${ticket.ticket_id?.slice(0, 8) || '未命名'}`}
                    className="ps-ticket-delete"
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      void deleteTicket(ticket.ticket_id)
                    }}
                  >
                    ×
                  </button>
                </div>
              )) : <div className="ps-empty">暂无工单，请先扫描 PSD。</div>}
            </div>
          </section>

          <section className="ps-panel ps-output-panel">
            <div className="ps-ai-quick-card">
              <div className="ps-ai-quick-intro">
                <h3 className="ps-ai-quick-title">工单需求</h3>
              </div>
              <div className="ps-ai-quick-actions" role="group" aria-label="Photoshop 工单需求快捷指令">
                <button type="button" className="ps-ai-quick-btn" onClick={() => setLocaleRequestOpen(true)}>
                  语种需求
                </button>
                <button
                  type="button"
                  className="ps-ai-quick-btn"
                  disabled={translateBusy || !ticket || !ticketId}
                  aria-busy={translateBusy}
                  title={
                    !ticket || !ticketId
                      ? '请先扫描或导入工单'
                      : '按各任务母版文案（含换行）调用 Ai 写入目标文案并保存；译文须保持与原文相同的行数。若多行被压成一行，请重新扫描工单以更新母版换行后再翻译。'
                  }
                  onClick={() => void runPhotoshopBulkTranslate()}
                >
                  {translateBusy ? '翻译中…' : 'Ai翻译'}
                </button>
                <button type="button" className="ps-ai-quick-btn" onClick={() => pushAiComposerText(PS_AI_PROMPTS.copycheck)}>
                  Ai检查
                </button>
                <button
                  type="button"
                  className="ps-ai-quick-btn"
                  onClick={() => void exportTicketWithOutputPath()}
                  disabled={!ticket || !ticketId}
                  title={
                    !ticket || !ticketId
                      ? '请先扫描或导入工单'
                      : saveOutputDir.trim()
                        ? `将工单 JSON 保存到已选输出目录（${saveOutputDir.trim()}）`
                        : '先选择输出目录并保存工单，再将 JSON 写入该目录'
                  }
                >
                  导出工单
                </button>
              </div>
              {translateUi?.mode === 'running' ? (
                <div
                  className="ps-ai-translate-progress"
                  role="status"
                  aria-live="polite"
                  aria-busy={translateBusy}
                >
                  <div className="ps-ai-translate-progress__phase">
                    <span className="ps-ai-translate-progress__dot" aria-hidden />
                    {translateUi.phase === 'model'
                      ? '正在请求 AI 模型翻译（通常需数秒至数十秒）…'
                      : translateUi.phase === 'save'
                        ? '正在合并译文并保存工单…'
                        : '正在同步工单列表…'}
                  </div>
                  <div className="ps-ai-translate-progress__meta">
                    <span><strong>{translateUi.count}</strong> 条</span>
                    <span title={`任务序号（从 1 开始）：${translateUi.taskNos}`}>
                      任务 <strong>{translateUi.taskNos}</strong>
                    </span>
                    <span title="本批使用的目标区域">{translateUi.localeSample}</span>
                  </div>
                  <div
                    className="ps-ai-translate-progress__preview"
                    title={translateUi.textPreviewFull}
                  >
                    <span className="ps-ai-translate-progress__preview-label">本批首条原文</span>
                    <span className="ps-ai-translate-progress__preview-text">{translateUi.textPreview}</span>
                  </div>
                </div>
              ) : null}
              {translateUi?.mode === 'error' ? (
                <div className="ps-ai-translate-outcome ps-ai-translate-outcome--error" role="alert">
                  <p className="ps-ai-translate-outcome__text">{translateUi.message}</p>
                  <div className="ps-ai-translate-outcome__actions">
                    <button
                      type="button"
                      className="ps-ai-translate-outcome__dismiss"
                      onClick={() => setTranslateUi(null)}
                    >
                      关闭
                    </button>
                  </div>
                </div>
              ) : null}
              {translateUi?.mode === 'success' ? (
                <div className="ps-ai-translate-outcome ps-ai-translate-outcome--success" role="status">
                  <p className="ps-ai-translate-outcome__text">{translateUi.message}</p>
                  <p className="ps-ai-translate-outcome__hint">提示也会写在「执行与回执」里；约数秒后自动收起本条。</p>
                </div>
              ) : null}
              <div className="ps-language-compact ps-save-path-compact">
                <div
                  className="ps-save-path-summary"
                  role="button"
                  tabIndex={0}
                  aria-label={
                    saveOutputDir.trim()
                      ? `输出目录已设为 ${saveOutputDir.trim()}，点此保存工单（不换目录）；需改目录请先清除`
                      : '点此选择输出目录，确认后保存工单；未指定目录时修改后 PSD 与母版 PSD 同目录'
                  }
                  onClick={(event) => {
                    if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                    activateOutputPathRow()
                  }}
                  onKeyDown={(event) => {
                    if (event.key !== 'Enter' && event.key !== ' ') return
                    if ((event.target as HTMLElement).closest('.ps-save-path-summary__clear')) return
                    event.preventDefault()
                    activateOutputPathRow()
                  }}
                >
                  <PsSavePathSummaryValue
                    path={saveOutputDir}
                    placeholder="点此选择输出目录；确认后保存工单（未选目录则与母版 PSD 同目录）"
                    title={
                      saveOutputDir.trim()
                        ? `${saveOutputDir.trim()} — 点击将工单保存到服务器（不弹出目录）。若要更换目录请先点「清除」。`
                        : '选择输出目录后自动保存工单。未选择时修改后的 PSD 默认在母版 PSD 同目录。'
                    }
                  />
                  {saveOutputDir.trim() ? (
                    <button
                      type="button"
                      className="ps-save-path-summary__clear"
                      aria-label="清除已选目录（将改回与母版 PSD 同目录）"
                      title="清除"
                      onClick={(event) => {
                        event.preventDefault()
                        event.stopPropagation()
                        setSaveOutputDir('')
                      }}
                    >
                      <span aria-hidden={true}>
                        <CloseIcon />
                      </span>
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          </section>

          <section className="ps-panel ps-task-panel">
            <div className="ps-section-head">
              <div>
                <h3>当前工单操作</h3>
                <p>按图层逐项改文案、换字体、确认输出；已确认的任务会自动进入执行选择。</p>
              </div>
              <div className="ps-actions">
                <ToolbarButton onClick={() => setSelected(executableIndexes)} disabled={!tasks.length}>选择可执行</ToolbarButton>
                <ToolbarButton onClick={() => setSelected(visibleIndexes.filter((index) => executableIndexes.includes(index)))} disabled={!visibleIndexes.length}>选择当前筛选</ToolbarButton>
                <ToolbarButton onClick={() => setSelected([])} disabled={!tasks.length}>清空选择</ToolbarButton>
              </div>
            </div>
            <div className="ps-task-guide">
              <span title="编辑各任务目标文案（与母版一致时可留空）"><b>1</b> 改目标文案</span>
              <span title="选择目标字体、输出文件名；可按语种筛选后批量设字体"><b>2</b> 字体·输出·批量</span>
              <span title="产品名等勾选「固定」后：不参与 Ai 翻译与批量改字体，执行沿用母版"><b>3</b> 固定文案免译</span>
              <span title="点击「确认修改」后再保存/执行"><b>4</b> 确认后执行</span>
              <em>{selectedExecutableCount}/{executableIndexes.length} 已选可执行</em>
            </div>
            <div className="ps-task-controls">
              <div className="ps-task-controls__search">
                <input
                  className="ps-task-search"
                  aria-label="搜索 Photoshop 任务"
                  value={taskSearch}
                  onChange={(event) => setTaskSearch(event.target.value)}
                  placeholder="搜索原文、图层、智能对象或画板"
                />
              </div>
              <div className="ps-task-controls__filters">
                <div className="ps-task-filter" role="tablist" aria-label="Photoshop 任务分类">
                  {taskFilters.map((filter) => (
                    <button
                      type="button"
                      key={filter.id}
                      className={taskFilter === filter.id ? 'ps-filter--active' : ''}
                      onClick={() => setTaskFilter(filter.id)}
                    >
                      {filter.label}
                      <span>{filterCounts[filter.id]}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="ps-task-controls__bulk">
                <FontPicker
                  compact
                  hideLabels
                  ariaLabel="批量目标字体"
                  emptyLabel="沿用源"
                  value={bulkFont}
                  sourceFont=""
                  fonts={fonts}
                  onChange={setBulkFont}
                />
                <div className="ps-bulk-locale">
                  <select
                    className="ps-bulk-locale-select"
                    aria-label="语种：批量操作限定当前筛选内的任务"
                    value={bulkLocaleFilter}
                    onChange={(event) => setBulkLocaleFilter(event.target.value)}
                  >
                    <optgroup label="语种">
                      <option value="">全部（当前筛选）</option>
                      {bulkLocaleOptions.map((loc) => (
                        <option key={loc} value={loc}>
                          {loc}
                        </option>
                      ))}
                    </optgroup>
                  </select>
                </div>
                <ToolbarButton
                  onClick={applyBulkFontToVisibleTasks}
                  disabled={!bulkFont.trim() || !bulkFontTargetIndexes.length}
                  title={
                    bulkFontTargetIndexes.length < visibleIndexes.length && visibleIndexes.length > 0
                      ? `对 ${bulkFontTargetIndexes.length} 条设置目标字体（已跳过 ${visibleIndexes.length - bulkFontTargetIndexes.length} 条固定文案）`
                      : bulkLocaleFilter.trim()
                        ? `对列表中的 ${bulkFontTargetIndexes.length} 条（语种 ${bulkLocaleFilter}）设置目标字体`
                        : `对当前列表中的 ${bulkFontTargetIndexes.length} 条任务设置目标字体`
                  }
                >
                  批量设置字体
                </ToolbarButton>
                <ToolbarButton
                  onClick={confirmVisibleTasks}
                  disabled={!visibleIndexes.length}
                  title={
                    bulkLocaleFilter.trim()
                      ? `确认当前列表中的 ${visibleIndexes.length} 条（语种 ${bulkLocaleFilter}）`
                      : `确认当前列表中的 ${visibleIndexes.length} 条任务`
                  }
                >
                  批量确认当前筛选
                </ToolbarButton>
              </div>
              {warningTaskCount ? <p className="ps-task-warning">有 {warningTaskCount} 个任务带错误或备注，建议筛选“有错误/警告”后复核。</p> : null}
            </div>
            <div className="ps-task-list">
              {displayedTaskEntries.length ? displayedTaskEntries.map(({ task, index }) => (
                <PhotoshopTaskRow
                  key={index}
                  task={task}
                  index={index}
                  selected={selectedSet.has(index)}
                  ready={executableIndexSet.has(index)}
                  fonts={fonts}
                  aiTranslating={Boolean(translateUi?.mode === 'running' && translateUi.indexes.includes(index))}
                  onUpdate={updateTask}
                  onToggle={toggleTask}
                  onConfirm={confirmTask}
                />
              )) : (
                <div className="ps-empty">
                  {!tasks.length
                    ? '等待扫描或选择工单。'
                    : bulkLocaleFilter.trim()
                      ? `当前分类/搜索下没有语种为「${bulkLocaleFilter}」的任务；请检查各任务「语种」字段或改选「全部」。`
                      : '当前筛选没有匹配任务。'}
                </div>
              )}
            </div>
            <div className="ps-execute-dock" aria-label="工单执行操作">
              <div>
                <strong>{selectedExecutableCount ? `${selectedExecutableCount} 个任务已准备执行` : '确认任务后执行'}</strong>
                <small>确认修改会自动勾选任务；点击右侧按钮会先保存工单，再生成并打开输出 PSD。</small>
              </div>
              <div className="ps-execute-dock-actions">
                <ToolbarButton onClick={() => void persistTicket()} disabled={!ticketId}>只保存</ToolbarButton>
                <PrimaryButton onClick={() => void execute(false)} disabled={!ticketId || !selected.length}>保存并执行</PrimaryButton>
              </div>
            </div>
          </section>
        </div>

        <section className={`ps-panel ps-execute-panel ${activePanel === 'result' ? '' : 'ps-panel--hidden'}`}>
          <div className="ps-section-head">
            <div>
              <h3>执行与回执</h3>
              <p>
                保存确认后的工单，再执行已选择任务。多语言时相同「输出文件名」的任务会在同一份 PSD 上依次处理（一种语言一套成品），再保存到输出目录。
              </p>
            </div>
            <div className="ps-actions">
              <ToolbarButton onClick={() => void persistTicket()} disabled={!ticketId}>保存工单</ToolbarButton>
              <PrimaryButton onClick={() => void execute(false)} disabled={!ticketId || !selected.length}>执行已选任务</PrimaryButton>
              <ToolbarButton onClick={refreshExecution} disabled={!ticketId}>刷新执行状态</ToolbarButton>
              <ToolbarButton onClick={async () => ticketId && setExecution(await cancelPhotoshopExecution(ticketId))} disabled={!ticketId}>取消执行</ToolbarButton>
            </div>
          </div>
          <div className="ps-result-grid">
            <ExecutionSummary result={result} execution={execution} />
          </div>
          <details
            className="ps-json"
            onToggle={(event) => {
              if ((event.currentTarget as HTMLDetailsElement).open && ticket) {
                setTicketText(JSON.stringify(ticket, null, 2))
              }
            }}
          >
            <summary>高级：工单 JSON 及原始执行结果</summary>
            <div className="ps-json-grid">
              <textarea
                value={ticketText}
                onChange={(event) => {
                  const nextText = event.target.value
                  setTicketText(nextText)
                  try {
                    setTicket(JSON.parse(nextText || '{}'))
                  } catch {
                    // Keep the JSON draft editable until the user fixes syntax.
                  }
                }}
                placeholder="工单 JSON"
              />
              <textarea value={JSON.stringify({ result, execution }, null, 2)} readOnly placeholder="执行结果 JSON" />
            </div>
          </details>
        </section>
        </main>
        <AutomationTaskDialogMemo
          open={editingTaskIndex !== null}
          title={`Photoshop 任务 ${(editingTaskIndex ?? 0) + 1}`}
          task={editingTaskIndex !== null ? tasks[editingTaskIndex] : null}
          index={editingTaskIndex ?? -1}
          selected={editingTaskIndex !== null ? selected.includes(editingTaskIndex) : false}
          fonts={fonts}
          accent="blue"
          onClose={closeTaskDialog}
          onSave={saveTaskDialog}
        />
      </div>
    </AppLayout>
  )
}

type PhotoshopTaskRowProps = {
  task: AnyRecord
  index: number
  selected: boolean
  ready: boolean
  fonts: string[]
  aiTranslating?: boolean
  onUpdate: (index: number, patch: AnyRecord) => void
  onToggle: (index: number, checked: boolean) => void
  onConfirm: (index: number) => void
}

const PhotoshopTaskRow = memo(function PhotoshopTaskRow({
  task,
  index,
  selected,
  ready,
  fonts,
  aiTranslating = false,
  onUpdate,
  onToggle,
  onConfirm,
}: PhotoshopTaskRowProps) {
  const smart = isSmartObjectTask(task)
  const preserve = Boolean(task.preserve_copy)
  const sourceText = taskEffectiveSourceText(task)
  const rawTarget = task.target_text
  const hasStoredTarget = rawTarget != null && String(rawTarget).trim() !== ''
  const displayValue = preserve ? sourceText : hasStoredTarget ? String(rawTarget) : sourceText

  const syncTargetFromInput = (value: string) => {
    if (preserve) return
    if (value.trim() === sourceText.trim()) {
      onUpdate(index, { target_text: '' })
    } else {
      onUpdate(index, { target_text: value })
    }
  }

  const togglePreserve = (checked: boolean) => {
    if (checked) {
      onUpdate(index, { preserve_copy: true, target_text: '', target_font: '' })
    } else {
      onUpdate(index, { preserve_copy: false })
    }
  }

  const taskWarning = hasTaskWarning(task)
  const checkState = taskWarning ? 'warning' : ready ? 'ready' : 'pending'
  const checkTitle = taskWarning
    ? `任务 ${index + 1} · 有错误/警告`
    : ready
      ? `任务 ${index + 1} · 可执行`
      : `任务 ${index + 1} · 待修改/待确认`
  const taskFontOptions = useMemo(() => fontOptionsForTask(fonts, task), [fonts, task])

  return (
    <div
      className={`ps-task ${selected ? 'ps-task--selected' : ''} ${smart ? 'ps-task--smart' : ''}${
        preserve ? ' ps-task--preserve-copy' : ''
      }${aiTranslating ? ' ps-task--ai-translating' : ''}`}
    >
      <label className={`ps-task-check ps-task-check--${checkState}`} title={checkTitle}>
        <input
          type="checkbox"
          checked={selected}
          disabled={!ready}
          onChange={(event) => onToggle(index, event.target.checked)}
        />
        <span>{index + 1}</span>
      </label>
      <div className="ps-task-main">
        <div className="ps-task-head">
          <div className="ps-task-head-main">
            <input
              className="ps-task-copy-input"
              aria-label={`文案 ${index + 1}（默认母版原文，改动后为目标文案）`}
              value={displayValue}
              readOnly={preserve}
              onChange={(event) => syncTargetFromInput(event.target.value)}
              placeholder={preserve ? '固定文案：与母版一致，不参与翻译/批量改字体' : '母版原文；可直接编辑，或与原文一致时留空表示未改'}
              title={
                preserve
                  ? '已标记固定文案（如产品名）：执行时沿用母版原文与源字体'
                  : sourceText.trim()
                    ? `母版参考：${sourceText}`
                    : '暂无扫描原文，可手写目标文案'
              }
            />
          </div>
          <div className="ps-task-head-meta">
            <div className="ps-task-badges">
              <em className={smart ? 'ps-badge ps-badge--smart' : 'ps-badge ps-badge--layer'}>{smart ? '智能对象内文字层' : '普通文字层'}</em>
              {preserve ? <em className="ps-badge ps-badge--preserve">固定文案</em> : null}
              {taskWarning ? <em className="ps-badge ps-badge--warning">有错误/警告</em> : null}
            </div>
            <label className="ps-task-preserve" title="产品名等品牌固定用语：不随 Ai 翻译、不参与批量改字体；执行时写回母版原文与源字体">
              <input
                type="checkbox"
                checked={preserve}
                onChange={(event) => togglePreserve(event.target.checked)}
              />
              <span>固定</span>
            </label>
          </div>
        </div>
        <div className="ps-task-toolbar">
          <div className="ps-task-field ps-task-field--fonts">
            <FontPicker
              compact
              hideLabels
              accent={smart ? 'purple' : 'blue'}
              ariaLabel={`目标字体 ${index + 1}`}
              disabled={preserve}
              value={task.target_font || ''}
              sourceFont={task.source_font}
              fonts={taskFontOptions}
              onChange={(font) => onUpdate(index, { target_font: font })}
            />
          </div>
          <div className="ps-task-field ps-task-field--output">
            <input
              aria-label={`输出名称 ${index + 1}`}
              value={task.output_name || ''}
              onChange={(event) => onUpdate(index, { output_name: event.target.value })}
              placeholder="输出 · 默认命名"
            />
          </div>
          <ToolbarButton className="ps-task-confirm-btn" type="button" onClick={() => onConfirm(index)}>确认修改</ToolbarButton>
        </div>
      </div>
    </div>
  )
})

function uniqueStrings(items: unknown[]) {
  return Array.from(new Set(items.map((item) => String(item || '').trim()).filter(Boolean)))
}

function uniqueNumbers(items: number[]) {
  return Array.from(new Set(items))
}

function ticketWithOutputDir(ticket: AnyRecord, outputDir: string) {
  const meta = { ...(ticket.meta || {}) }
  const trimmed = outputDir.trim()
  if (trimmed) meta.output_dir = trimmed
  else delete meta.output_dir
  return { ...ticket, meta }
}

const taskFilters: { id: TaskFilter, label: string }[] = [
  { id: 'all', label: '全部' },
  { id: 'text', label: '普通文字层' },
  { id: 'smart_object_text', label: '智能对象内文字层' },
  { id: 'pending', label: '待确认' },
  { id: 'ready', label: '可执行' },
  { id: 'warning', label: '有错误/警告' },
]

function hasTaskWarning(task: AnyRecord) {
  return task.status === 'error' || Boolean(String(task.notes || '').trim())
}

function matchesTaskFilter(task: AnyRecord, filter: TaskFilter) {
  if (filter === 'all') return true
  if (filter === 'text') return !isSmartObjectTask(task)
  if (filter === 'smart_object_text') return isSmartObjectTask(task)
  if (filter === 'pending') return !isAutomationTaskExecutable(task)
  if (filter === 'ready') return isAutomationTaskExecutable(task)
  return hasTaskWarning(task)
}

function matchesTaskSearch(task: AnyRecord, search: string) {
  const needle = search.trim().toLowerCase()
  if (!needle) return true
  const eff = taskEffectiveSourceText(task)
  return [
    task.layer_name,
    task.smart_object_name,
    task.smart_object_inner_layer_name,
    task.artboard_name,
    task.original_text,
    task.target_text,
    eff,
    task.source_font,
    task.target_font,
  ].some((value) => String(value || '').toLowerCase().includes(needle))
}

function countTasksByFilter(tasks: AnyRecord[]): FilterCounts {
  return taskFilters.reduce((counts, filter) => {
    counts[filter.id] = tasks.filter((task) => matchesTaskFilter(task, filter.id)).length
    return counts
  }, {} as FilterCounts)
}

function formatTicketTime(createdAt: unknown, updatedAt: unknown) {
  const raw = String(createdAt || '').trim()
  const timestamp = raw || (updatedAt ? new Date(Number(updatedAt) * 1000).toISOString() : '')
  if (!timestamp) return '未知时间'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return raw || '未知时间'
  const pad = (value: number) => value.toString().padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return minutes ? `${minutes}分${seconds.toString().padStart(2, '0')}秒` : `${seconds}秒`
}

function scanProgressMessage(elapsedSec: number, sourceMode: 'active' | 'file' | 'folder') {
  const sourceLabel = sourceMode === 'folder' ? 'PSD 文件夹' : sourceMode === 'file' ? 'PSD 文件' : '当前 Photoshop 文档'
  if (elapsedSec < 4) return `正在连接 Photoshop 并读取${sourceLabel}...`
  if (elapsedSec < 12) return '正在收集普通文字层、画板和字体信息...'
  if (elapsedSec < 30) return '正在检查智能对象，Photoshop 可能会短暂打开和关闭内部文档...'
  return '仍在扫描智能对象文字层；大型 PSD 或嵌套智能对象可能需要更久。'
}

function taskIdentityKey(task: AnyRecord) {
  return [
    task.layer_id,
    task.artboard_name,
    task.layer_name,
    task.layer_kind,
    task.smart_object_layer_id,
    task.smart_object_name,
    task.smart_object_inner_layer_name,
    task.original_text,
    task.source_font,
  ].map((item) => String(item || '')).join('|')
}

function fontOptionsForTask(fonts: string[], task: AnyRecord) {
  return uniqueStrings([task.target_font, task.source_font, ...fonts])
}

function masterPsdStemForOutput(ticket: AnyRecord): string {
  const raw = String(ticket?.meta?.source_psd || '').trim()
  if (!raw) return 'output'
  const segments = raw.split(/[/\\]/)
  const base = segments[segments.length - 1] || raw
  const withoutExt = base.replace(/\.(psd|psb)$/i, '')
  const safe = withoutExt.replace(/[/\\:*?"<>|]+/g, '-').trim()
  return safe || 'output'
}

function rebuildTicketForLanguages(ticket: AnyRecord | null, languages: string[]) {
  if (!ticket || !Array.isArray(ticket.tasks)) return null
  const bases = new Map<string, AnyRecord>()
  ticket.tasks.forEach((task: AnyRecord) => {
    const key = taskIdentityKey(task)
    if (!bases.has(key)) bases.set(key, task)
  })

  const nextLanguages = uniqueStrings(languages)
  const masterStem = masterPsdStemForOutput(ticket)
  const nextTasks = Array.from(bases.entries()).flatMap(([key, baseTask]) => {
    if (!nextLanguages.length) {
      const existing = ticket.tasks.find((task: AnyRecord) => taskIdentityKey(task) === key && !task.language) || baseTask
      return [{ ...existing, language: '', output_name: existing.output_name || '' }]
    }
    return nextLanguages.map((language) => {
      const existing = ticket.tasks.find((task: AnyRecord) => taskIdentityKey(task) === key && task.language === language)
      const safeStem = String(language || '')
        .replace(/[/\\:*?"<>|]+/g, '-')
        .replace(/\s+/g, '')
        .trim() || 'lang'
      return {
        ...baseTask,
        ...existing,
        language,
        output_name: existing?.output_name?.trim() || `${masterStem}_${safeStem}.psd`,
      }
    })
  })

  const meta = { ...(typeof ticket.meta === 'object' && ticket.meta ? ticket.meta : {}), target_languages: nextLanguages }
  return {
    ...ticket,
    meta,
    tasks: nextTasks,
  }
}

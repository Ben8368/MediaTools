import { useEffect, useMemo, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  addAERenderQueue,
  cancelAEExecution,
  createAECheckpoint,
  deleteAETicket,
  executeAETicket,
  fetchAECheckpoints,
  fetchAEExecution,
  fetchAERenderStatus,
  fetchAEStatus,
  fetchAETicket,
  fetchAETickets,
  fetchSystemFonts,
  importAETicket,
  scanAEFolder,
  scanAETicket,
  startAERender,
  updateAETicket,
  wsUrl,
} from '@/api'
import {
  Field,
  PathInput,
  PrimaryButton,
  ResultBox,
  ToolbarButton,
} from '@/apps/mediatools/primitives'
import { AutomationTaskDialog } from '@/apps/mediatools/AutomationTaskDialog'
import { FontPicker } from '@/apps/mediatools/FontPicker'
import {
  automationTaskIndexes,
  isAutomationTaskExecutable,
  patchAutomationTask,
} from '@/apps/mediatools/automation'
import type { AnyRecord } from '@/types'

type TaskFilter = 'all' | 'pending' | 'ready' | 'warning'

function ExecutionSummary({ result, execution }: { result: any, execution: any }) {
  if (!result && !execution) return <div className="ae-empty">暂无执行记录。</div>
  
  return (
    <div className="ae-execution-summary">
       {result && (
         <div className="ae-execution-card">
           <h4>执行请求</h4>
           {result.ok ? <p className="success">请求已提交成功</p> : <p className="error">提交失败：{result.error || '未知错误'}</p>}
           {result.message && <p>{result.message}</p>}
         </div>
       )}
       {execution && typeof execution === 'string' ? (
         <div className="ae-execution-card"><p>{execution}</p></div>
       ) : execution && (
         <div className="ae-execution-card">
           <h4>执行状态</h4>
           <p>状态：{execution.state?.status || '未知'}</p>
           {execution.state?.progress !== undefined && <p>进度：{execution.state.progress}%</p>}
           {execution.state?.message && <p>{execution.state.message}</p>}
         </div>
       )}
    </div>
  )
}

export function AEApp() {
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [activePanel, setActivePanel] = useState<'scan' | 'import' | 'result'>('scan')
  const [tickets, setTickets] = useState<AnyRecord[]>([])
  const [ticketId, setTicketId] = useState('')
  const [ticketText, setTicketText] = useState('')
  const [ticketImportPath, setTicketImportPath] = useState('')
  const [sourceMode, setSourceMode] = useState<'file' | 'folder'>('file')
  const [projectPath, setProjectPath] = useState('')
  const [projectFolder, setProjectFolder] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [editingTaskIndex, setEditingTaskIndex] = useState<number | null>(null)
  const [fonts, setFonts] = useState<string[]>([])
  const [result, setResult] = useState<unknown>('等待扫描或选择工单')
  const [execution, setExecution] = useState<unknown>('等待执行')
  const [checkpointLabel, setCheckpointLabel] = useState('')
  const [checkpoints, setCheckpoints] = useState<AnyRecord[]>([])
  const [renderComp, setRenderComp] = useState(1)
  const [renderOutput, setRenderOutput] = useState('')
  const [renderTemplate, setRenderTemplate] = useState('Best Settings')
  const [isScanning, setIsScanning] = useState(false)
  const [scanStartedAt, setScanStartedAt] = useState<number | null>(null)
  const [scanElapsedSec, setScanElapsedSec] = useState(0)
  const [scanJob, setScanJob] = useState<AnyRecord | null>(null)
  const [taskFilter, setTaskFilter] = useState<TaskFilter>('all')
  const [taskSearch, setTaskSearch] = useState('')
  const [bulkFont, setBulkFont] = useState('')

  const parsedTicket = useMemo(() => {
    try {
      return JSON.parse(ticketText || '{}')
    } catch {
      return null
    }
  }, [ticketText])

  const tasks: AnyRecord[] = Array.isArray(parsedTicket?.tasks) ? parsedTicket.tasks : []
  const executableIndexes = automationTaskIndexes(tasks)
  const activeTicket = tickets.find((ticket) => ticket.ticket_id === ticketId)
  const sourceProject = activeTicket?.source_project || parsedTicket?.meta?.source_project || ''
  const selectedExecutableCount = selected.filter((index) => executableIndexes.includes(index)).length
  const warningTaskCount = tasks.filter(hasTaskWarning).length
  const filteredTaskEntries = useMemo(() => (
    tasks
      .map((task, index) => ({ task, index }))
      .filter(({ task }) => matchesTaskFilter(task, taskFilter))
      .filter(({ task }) => matchesTaskSearch(task, taskSearch))
  ), [tasks, taskFilter, taskSearch])
  const visibleIndexes = filteredTaskEntries.map(({ index }) => index)

  function updateTask(index: number, patch: AnyRecord) {
    const nextTicket = patchAutomationTask(parsedTicket, index, patch)
    if (!nextTicket) return
    setTicketText(JSON.stringify(nextTicket, null, 2))
  }

  function updateTasks(indexes: number[], patch: AnyRecord) {
    if (!parsedTicket || !Array.isArray(parsedTicket.tasks)) return
    const indexSet = new Set(indexes)
    const nextTicket = {
      ...parsedTicket,
      tasks: parsedTicket.tasks.map((task: AnyRecord, index: number) => (
        indexSet.has(index) ? { ...task, ...patch } : task
      )),
    }
    setTicketText(JSON.stringify(nextTicket, null, 2))
  }

  function toggleTask(index: number, checked: boolean) {
    setSelected((items) => {
      if (checked) return items.includes(index) ? items : [...items, index]
      return items.filter((item) => item !== index)
    })
  }

  function saveTaskDialog(index: number, patch: AnyRecord, checked: boolean) {
    updateTask(index, patch)
    toggleTask(index, checked)
  }

  function confirmTask(index: number) {
    updateTask(index, { status: 'confirmed' })
    toggleTask(index, true)
  }

  function confirmVisibleTasks() {
    if (!visibleIndexes.length) return
    updateTasks(visibleIndexes, { status: 'confirmed' })
    setSelected((items) => uniqueNumbers([...items, ...visibleIndexes]))
  }

  function applyBulkFontToVisibleTasks() {
    const font = bulkFont.trim()
    if (!font || !visibleIndexes.length) return
    updateTasks(visibleIndexes, { target_font: font })
  }

  async function refresh() {
    const [statusData, ticketData] = await Promise.all([fetchAEStatus(), fetchAETickets()])
    setStatus(statusData)
    setTickets(ticketData.items || [])
  }

  async function loadTicket(nextId: string) {
    setActivePanel('import')
    setTicketId(nextId)
    const data = await fetchAETicket(nextId)
    const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
    const sourceProject = data.ticket?.meta?.source_project || ''
    setTicketText(JSON.stringify(data.ticket, null, 2))
    setProjectPath((current) => current || sourceProject)
    setSelected(automationTaskIndexes(nextTasks))
    setResult(data)
  }

  async function deleteTicket(nextId: string) {
    const data = await deleteAETicket(nextId)
    if (ticketId === nextId) {
      setTicketId('')
      setTicketText('')
      setSelected([])
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
      message: 'After Effects 正在扫描文本图层，请保持 After Effects 打开。',
      source_mode: sourceMode,
    })
    try {
      const data = sourceMode === 'folder'
        ? await scanAEFolder({ directory: projectFolder, recursive: true, max_files: 30 })
        : await scanAETicket({ file_path: projectPath })
      setResult(data)
      if (data.ok) {
        const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
        setTicketId(data.ticket_id)
        setTicketText(JSON.stringify(data.ticket, null, 2))
        setSelected(automationTaskIndexes(nextTasks))
        setActivePanel('import')
        await refresh()
      }
    } catch (err: any) {
      setResult({ ok: false, status: 'error', error: err?.message || 'AE 扫描失败' })
    } finally {
      setIsScanning(false)
      setScanStartedAt(null)
    }
  }

  async function importTicket() {
    if (!ticketImportPath) {
      setResult({ ok: false, error: '请先选择工单 JSON 文件' })
      return
    }
    try {
      const data = await importAETicket(ticketImportPath)
      const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
      const nextSourceProject = data.ticket?.meta?.source_project || ''
      setTicketId(data.ticket_id)
      setTicketText(JSON.stringify(data.ticket, null, 2))
      setProjectPath((current) => current || nextSourceProject)
      setSelected(automationTaskIndexes(nextTasks))
      setActivePanel('import')
      setResult(data)
      await refresh()
    } catch (err: any) {
      setResult({ ok: false, error: err?.message || '导入工单失败' })
    }
  }

  async function save() {
    try {
      const data = await updateAETicket(ticketId, JSON.parse(ticketText || '{}'))
      const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
      setTicketText(JSON.stringify(data.ticket, null, 2))
      setSelected((items) => items.filter((index) => index < nextTasks.length))
      setResult(data)
      await refresh()
    } catch (err: any) {
      setResult({ ok: false, error: err?.message || '保存失败，请检查工单 JSON 格式' })
    }
  }

  async function execute(dryRun: boolean) {
    if (!selected.length) {
      setExecution('请先勾选至少一个任务')
      return
    }
    if (!ticketId) return
    try {
      setExecution('正在保存工单并执行...')
      const saved = await updateAETicket(ticketId, JSON.parse(ticketText || '{}'))
      setTicketText(JSON.stringify(saved.ticket, null, 2))
      setActivePanel('result')
      setResult(saved)
      setExecution(await executeAETicket(ticketId, dryRun, selected))
      await refresh()
    } catch (err: any) {
      setExecution({ ok: false, error: err?.message || '执行失败，请检查工单内容' })
    }
  }

  async function refreshExecution() {
    if (!ticketId) return
    try {
      setExecution(await fetchAEExecution(ticketId))
    } catch (err: any) {
      setExecution(err?.message || '未找到执行状态')
    }
  }

  async function listCheckpoints() {
    if (!projectPath) {
      setResult({ ok: false, error: '请先选择 AE 工程文件' })
      return
    }
    const data = await fetchAECheckpoints(projectPath)
    setCheckpoints(data.checkpoints || data.items || [])
    setResult(data)
  }

  async function createCheckpoint() {
    if (!projectPath) {
      setResult({ ok: false, error: '请先选择 AE 工程文件' })
      return
    }
    const data = await createAECheckpoint({ file_path: projectPath, label: checkpointLabel || 'manual', notes: 'created from MediaTools' })
    setResult(data)
    await listCheckpoints()
  }

  async function addRenderQueue() {
    const data = await addAERenderQueue({
      file_path: projectPath,
      comp_index: renderComp,
      output_path: renderOutput,
      output_module_template: renderTemplate,
    })
    setResult(data)
  }

  async function startRender() {
    setExecution(await startAERender({ file_path: projectPath }))
  }

  async function refreshRenderStatus() {
    if (!projectPath) return
    setExecution(await fetchAERenderStatus(projectPath))
  }

  useEffect(() => { void refresh() }, [])

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
            ['ae_scan', 'ae_scan_folder'].includes(job.type)
            && ['pending', 'running'].includes(job.status)
          ))
          .at(-1)
        if (runningScan) setScanJob(runningScan)
      } catch {
        // Ignore malformed websocket frames; elapsed time still keeps the scan UI useful.
      }
    }
    return () => socket.close()
  }, [isScanning])

  useEffect(() => {
    void fetchSystemFonts({ limit: 8000 }).then((data) => {
      const names = (data.items || []).map((item: AnyRecord) => item.name).filter(Boolean)
      setFonts(names)
    }).catch(() => setFonts([]))
  }, [])

  return (
    <AppLayout>
      <div className="ae-app">
        <aside className="ae-flow-sidebar" aria-label="After Effects 工单流程">
          <button type="button" className={`ae-flow-step ${activePanel === 'scan' ? 'ae-flow-step--active' : ''}`} onClick={() => setActivePanel('scan')}>
            <span>01</span>
            <div>
              <strong>扫描工单</strong>
              <small>{sourceMode === 'file' ? '单文件扫描' : '文件夹批量扫描'}</small>
            </div>
          </button>
          <button type="button" className={`ae-flow-step ${activePanel === 'import' ? 'ae-flow-step--active' : ''}`} onClick={() => setActivePanel('import')}>
            <span>02</span>
            <div>
              <strong>导入工单</strong>
              <small>{ticketId ? `${ticketId.slice(0, 8)} · ${tasks.length} 个任务` : '扫描后自动导入当前工单'}</small>
              {sourceProject ? <em>{sourceProject}</em> : null}
            </div>
          </button>
          <button type="button" className={`ae-flow-step ${activePanel === 'result' ? 'ae-flow-step--active' : ''}`} onClick={() => setActivePanel('result')}>
            <span>03</span>
            <div>
              <strong>执行结果</strong>
              <small>{ticketId ? `${selectedExecutableCount} 个已选择` : '等待当前工单'}</small>
            </div>
          </button>
        </aside>

        <main className="ae-operation">
        <div className={`ae-metrics ${activePanel === 'import' ? '' : 'ae-panel--hidden'}`}>
          <div className="ae-metric"><span>工单数量</span><strong>{tickets.length}</strong></div>
          <div className="ae-metric"><span>内容项</span><strong>{tasks.length}</strong></div>
          <div className="ae-metric"><span>可执行</span><strong>{executableIndexes.length}</strong></div>
          <div className="ae-metric"><span>已选择</span><strong>{selectedExecutableCount}</strong></div>
        </div>

        <section className={`ae-panel ae-scan-panel ${activePanel === 'scan' ? '' : 'ae-panel--hidden'}`}>
          <div className="ae-section-head">
            <div>
              <h3>扫描工单</h3>
              <p>选择 `.aep` 来源并扫描文本图层，扫描成功后会自动导入为当前工单。</p>
            </div>
            <ToolbarButton onClick={() => void refresh()} disabled={isScanning}>刷新状态</ToolbarButton>
          </div>
          <div className="ae-source-tabs" role="tablist" aria-label="After Effects source mode">
            <button className={`ae-source-tab ${sourceMode === 'file' ? 'ae-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('file')} disabled={isScanning}>单文件</button>
            <button className={`ae-source-tab ${sourceMode === 'folder' ? 'ae-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('folder')} disabled={isScanning}>文件夹批量</button>
          </div>
          <div className="ae-form-grid">
            {sourceMode === 'folder' ? (
              <Field label="AE 工程文件夹">
                <PathInput value={projectFolder} onChange={setProjectFolder} mode="directory" placeholder="选择包含 .aep 的文件夹" />
              </Field>
            ) : (
              <Field label="AE 工程文件">
                <PathInput value={projectPath} onChange={setProjectPath} mode="file" placeholder="选择 .aep 工程文件" />
              </Field>
            )}
            <Field label="默认输出路径">
              <input
                value={renderOutput}
                onChange={(event) => setRenderOutput(event.target.value)}
                placeholder="例如 D:\\renders\\preview.mov"
              />
            </Field>
          </div>
          {isScanning ? (
            <div className="ae-scan-progress" role="status" aria-live="polite">
              <div className="ae-scan-progress-top">
                <span>扫描进行中</span>
                <strong>{formatDuration(scanElapsedSec)}</strong>
              </div>
              <div className="ae-scan-progress-bar" aria-hidden="true"><span /></div>
              <p>{scanJob?.stage || scanProgressMessage(scanElapsedSec, sourceMode)}</p>
              <small>分析合成和图层时 After Effects 可能短暂卡顿，请不要手动切换或关闭工程。</small>
            </div>
          ) : null}
          <PrimaryButton onClick={() => void scan()} disabled={isScanning}>{isScanning ? '扫描中，请稍候...' : '扫描并生成工单'}</PrimaryButton>
        </section>

        <div className={`ae-workspace ${activePanel === 'import' ? '' : 'ae-workspace--hidden'}`}>
          <section className="ae-panel ae-ticket-panel">
            <div className="ae-section-head">
              <div>
                <h3>导入工单</h3>
                <p>{ticketId ? `当前工单：${ticketId}` : '扫描成功后会自动导入当前工单，也可以从历史工单中手动导入。'}</p>
              </div>
              <span>{tickets.length} 个</span>
            </div>
            <div className="ae-import-file">
              <Field label="导入工单文件">
                <PathInput value={ticketImportPath} onChange={setTicketImportPath} mode="file" placeholder="选择 After Effects 工单 JSON 文件" />
              </Field>
              <PrimaryButton onClick={importTicket}>导入并设为当前工单</PrimaryButton>
            </div>
            <div className="ae-ticket-list">
              {tickets.length ? tickets.map((ticket) => (
                <div
                  className={`ae-ticket ${ticket.ticket_id === ticketId ? 'ae-ticket--active' : ''}`}
                  key={ticket.ticket_id}
                >
                  <button type="button" className="ae-ticket-main" onClick={() => void loadTicket(ticket.ticket_id)}>
                    <span className="ae-ticket-top">
                      <strong>{ticket.ticket_id?.slice(0, 8) || '未命名'}</strong>
                      <small>{ticket.task_count || 0} 个任务</small>
                    </span>
                    <span className="ae-ticket-time">建立：{formatTicketTime(ticket.created_at, ticket.updated_at)}</span>
                    <span>{ticket.source_project || '未记录工程'}</span>
                  </button>
                  <button
                    type="button"
                    aria-label={`删除工单 ${ticket.ticket_id?.slice(0, 8) || '未命名'}`}
                    className="ae-ticket-delete"
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      void deleteTicket(ticket.ticket_id)
                    }}
                  >
                    ×
                  </button>
                </div>
              )) : <div className="ae-empty">暂无工单，请先扫描 AE 工程。</div>}
            </div>
          </section>

          <section className="ae-panel ae-task-panel">
            <div className="ae-section-head">
              <div>
                <h3>当前工单操作</h3>
                <p>按图层逐项改文案、换字体、确认输出；已确认的任务会自动进入执行选择。</p>
              </div>
              <div className="ae-actions">
                <ToolbarButton onClick={() => setSelected(executableIndexes)} disabled={!tasks.length}>选择可执行</ToolbarButton>
                <ToolbarButton onClick={() => setSelected(visibleIndexes.filter((index) => executableIndexes.includes(index)))} disabled={!visibleIndexes.length}>选择当前筛选</ToolbarButton>
                <ToolbarButton onClick={() => setSelected([])} disabled={!tasks.length}>清空选择</ToolbarButton>
              </div>
            </div>
            <div className="ae-task-guide">
              <span><b>1</b> 填替换文案</span>
              <span><b>2</b> 选择字体和输出名</span>
              <span><b>3</b> 确认后执行</span>
              <em>{selectedExecutableCount}/{executableIndexes.length} 已选可执行</em>
            </div>
            <div className="ae-task-controls">
              <div className="ae-task-controls__search">
                <input
                  className="ae-task-search"
                  aria-label="搜索 AE 任务"
                  value={taskSearch}
                  onChange={(event) => setTaskSearch(event.target.value)}
                  placeholder="搜索原文、图层名、合成或字体"
                />
              </div>
              <div className="ae-task-controls__filters">
                <div className="ae-task-filter" role="tablist" aria-label="AE 任务分类">
                  {taskFilters.map((filter) => (
                    <button
                      type="button"
                      key={filter.id}
                      className={taskFilter === filter.id ? 'ae-filter--active' : ''}
                      onClick={() => setTaskFilter(filter.id)}
                    >
                      {filter.label}
                      <span>{filterCount(tasks, filter.id)}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="ae-task-controls__bulk">
                <FontPicker
                  compact
                  hideLabels
                  ariaLabel="批量目标字体"
                  value={bulkFont}
                  sourceFont=""
                  fonts={fonts}
                  onChange={setBulkFont}
                />
                <ToolbarButton onClick={applyBulkFontToVisibleTasks} disabled={!bulkFont.trim() || !visibleIndexes.length}>批量设置字体</ToolbarButton>
                <ToolbarButton onClick={confirmVisibleTasks} disabled={!visibleIndexes.length}>批量确认当前筛选</ToolbarButton>
              </div>
              {warningTaskCount ? <p className="ae-task-warning">有 {warningTaskCount} 个任务带错误或备注，建议筛选“有错误/警告”后复核。</p> : null}
            </div>
            <div className="ae-task-list">
              {filteredTaskEntries.length ? filteredTaskEntries.map(({ task, index }) => {
                const ready = isAutomationTaskExecutable(task)
                const originalLine = String(task.original_text || '').trim()
                const primaryCopy = originalLine || String(task.layer_name || '').trim() || `任务 ${index + 1}`
                const taskWarning = hasTaskWarning(task)
                const checkState = taskWarning ? 'warning' : ready ? 'ready' : 'pending'
                const checkTitle = taskWarning
                  ? `任务 ${index + 1} · 有错误/警告`
                  : ready
                    ? `任务 ${index + 1} · 可执行`
                    : `任务 ${index + 1} · 待确认`
                return (
                  <div className={`ae-task ${selected.includes(index) ? 'ae-task--selected' : ''}`} key={index}>
                    <label className={`ae-task-check ae-task-check--${checkState}`} title={checkTitle}>
                      <input
                        type="checkbox"
                        checked={selected.includes(index)}
                        disabled={!ready}
                        onChange={(event) => toggleTask(index, event.target.checked)}
                      />
                      <span>{index + 1}</span>
                    </label>
                    <div className="ae-task-main">
                      <div className="ae-task-head">
                        <div className="ae-task-head-main">
                          <input
                            className="ae-task-copy-input"
                            aria-label={`替换文本 ${index + 1}`}
                            value={task.target_text || ''}
                            onChange={(event) => updateTask(index, { target_text: event.target.value })}
                            placeholder={primaryCopy}
                            title={primaryCopy}
                          />
                        </div>
                        <div className="ae-task-badges">
                          <em className={ready ? 'ae-badge ae-badge--ready' : 'ae-badge ae-badge--pending'}>{ready ? '可执行' : '待确认'}</em>
                          {taskWarning ? <em className="ae-badge ae-badge--warning">有错误/警告</em> : null}
                        </div>
                      </div>
                      <div className="ae-task-context">
                        <span>{task.comp_name || '未命名合成'}</span>
                        <span>{task.layer_name || '未命名图层'}</span>
                        <span>{task.source_font || '未知字体'}</span>
                      </div>
                      <div className="ae-task-toolbar">
                        <div className="ae-task-field ae-task-field--fonts">
                          <FontPicker
                            compact
                            hideLabels
                            accent="purple"
                            ariaLabel={`目标字体 ${index + 1}`}
                            value={task.target_font || ''}
                            sourceFont={task.source_font}
                            fonts={fontOptionsForTask(fonts, task)}
                            onChange={(font: string) => updateTask(index, { target_font: font })}
                          />
                        </div>
                        <div className="ae-task-field ae-task-field--output">
                          <input
                            aria-label={`输出名称 ${index + 1}`}
                            value={task.output_name || ''}
                            onChange={(event) => updateTask(index, { output_name: event.target.value })}
                            placeholder="输出 · 默认命名"
                          />
                        </div>
                        <ToolbarButton className="ae-task-confirm-btn" type="button" onClick={() => confirmTask(index)}>确认修改</ToolbarButton>
                      </div>
                    </div>
                  </div>
                )
              }) : <div className="ae-empty">{tasks.length ? '当前筛选没有匹配任务。' : '等待扫描或选择工单。'}</div>}
            </div>
            <div className="ae-execute-dock" aria-label="工单执行操作">
              <div>
                <strong>{selectedExecutableCount ? `${selectedExecutableCount} 个任务已准备执行` : '确认任务后执行'}</strong>
                <small>确认修改会自动勾选任务；点击右侧按钮会先保存工单，再执行。</small>
              </div>
              <div className="ae-execute-dock-actions">
                <ToolbarButton onClick={save} disabled={!ticketId}>只保存</ToolbarButton>
                <PrimaryButton onClick={() => void execute(false)} disabled={!ticketId || !selected.length}>保存并执行</PrimaryButton>
              </div>
            </div>
          </section>
        </div>

        <div className={`ae-tools ${activePanel === 'result' ? '' : 'ae-tools--hidden'}`}>
          <section className="ae-panel">
            <div className="ae-section-head">
              <div>
                <h3>扩展工具：检查点</h3>
                <p>执行前保存工程快照，方便后续回退或比对。</p>
              </div>
            </div>
            <div className="ae-inline-grid">
              <Field label="检查点名称"><input value={checkpointLabel} onChange={(event) => setCheckpointLabel(event.target.value)} placeholder="例如：替换前备份" /></Field>
              <div className="ae-actions ae-actions--bottom">
                <ToolbarButton onClick={createCheckpoint} disabled={!projectPath}>创建检查点</ToolbarButton>
                <ToolbarButton onClick={listCheckpoints} disabled={!projectPath}>查看检查点</ToolbarButton>
              </div>
            </div>
            <div className="ae-checkpoints">
              {checkpoints.slice(0, 4).map((checkpoint) => (
                <div className="ae-checkpoint" key={checkpoint.path || checkpoint.name}>
                  <strong>{checkpoint.name || checkpoint.path}</strong>
                  <span>{checkpoint.path}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="ae-panel">
            <div className="ae-section-head">
              <div>
                <h3>扩展工具：渲染队列</h3>
                <p>把指定合成加入渲染队列，或读取当前队列状态。</p>
              </div>
            </div>
            <div className="ae-render-grid">
              <Field label="合成序号"><input type="number" value={renderComp} onChange={(event) => setRenderComp(Number(event.target.value) || 1)} /></Field>
              <Field label="输出模板"><input value={renderTemplate} onChange={(event) => setRenderTemplate(event.target.value)} /></Field>
              <Field label="输出路径"><PathInput value={renderOutput} onChange={setRenderOutput} mode="any" placeholder="输出视频或工程路径" /></Field>
            </div>
            <div className="ae-actions">
              <ToolbarButton onClick={addRenderQueue} disabled={!projectPath || !renderOutput}>加入渲染队列</ToolbarButton>
              <PrimaryButton onClick={startRender} disabled={!projectPath}>开始渲染</PrimaryButton>
              <ToolbarButton onClick={refreshRenderStatus} disabled={!projectPath}>刷新队列状态</ToolbarButton>
            </div>
          </section>
        </div>

        <section className={`ae-panel ae-execute-panel ${activePanel === 'result' ? '' : 'ae-panel--hidden'}`}>
          <div className="ae-section-head">
            <div>
              <h3>执行与回执</h3>
              <p>保存确认后的工单，再执行已选择任务。</p>
            </div>
            <div className="ae-actions">
              <ToolbarButton onClick={save} disabled={!ticketId}>保存工单</ToolbarButton>
              <PrimaryButton onClick={() => void execute(false)} disabled={!ticketId || !selected.length}>执行已选任务</PrimaryButton>
              <ToolbarButton onClick={refreshExecution} disabled={!ticketId}>刷新执行状态</ToolbarButton>
              <ToolbarButton onClick={async () => ticketId && setExecution(await cancelAEExecution(ticketId))} disabled={!ticketId}>取消执行</ToolbarButton>
            </div>
          </div>
          <div className="ae-result-grid">
            <ExecutionSummary result={result} execution={execution} />
          </div>
          <details className="ae-json">
            <summary>高级：工单 JSON 及原始执行结果</summary>
            <div className="ae-json-grid">
              <textarea value={ticketText} onChange={(event) => setTicketText(event.target.value)} placeholder="工单 JSON" />
              <textarea value={JSON.stringify({ result, execution }, null, 2)} readOnly placeholder="执行结果 JSON" />
            </div>
          </details>
        </section>
        </main>
        <AutomationTaskDialog
          open={editingTaskIndex !== null}
          title={`After Effects 任务 ${(editingTaskIndex ?? 0) + 1}`}
          task={editingTaskIndex !== null ? tasks[editingTaskIndex] : null}
          index={editingTaskIndex ?? -1}
          selected={editingTaskIndex !== null ? selected.includes(editingTaskIndex) : false}
          fonts={fonts}
          accent="purple"
          onClose={() => setEditingTaskIndex(null)}
          onSave={saveTaskDialog}
        />
      </div>
    </AppLayout>
  )
}

function uniqueNumbers(items: number[]) {
  return Array.from(new Set(items))
}

const taskFilters: { id: TaskFilter, label: string }[] = [
  { id: 'all', label: '全部' },
  { id: 'pending', label: '待确认' },
  { id: 'ready', label: '可执行' },
  { id: 'warning', label: '有错误/警告' },
]

function hasTaskWarning(task: AnyRecord) {
  return task.status === 'error' || Boolean(String(task.notes || '').trim())
}

function matchesTaskFilter(task: AnyRecord, filter: TaskFilter) {
  if (filter === 'all') return true
  if (filter === 'pending') return !isAutomationTaskExecutable(task)
  if (filter === 'ready') return isAutomationTaskExecutable(task)
  return hasTaskWarning(task)
}

function matchesTaskSearch(task: AnyRecord, search: string) {
  const needle = search.trim().toLowerCase()
  if (!needle) return true
  return [
    task.layer_name,
    task.comp_name,
    task.original_text,
    task.target_text,
    task.source_font,
    task.target_font,
  ].some((value) => String(value || '').toLowerCase().includes(needle))
}

function filterCount(tasks: AnyRecord[], filter: TaskFilter) {
  return tasks.filter((task) => matchesTaskFilter(task, filter)).length
}

function formatTicketTime(createdAt: unknown, updatedAt: unknown) {
  const raw = String(createdAt || '').trim()
  const updatedRaw = String(updatedAt || '').trim()
  const timestamp = raw || (updatedRaw && /^\d+(\.\d+)?$/.test(updatedRaw) ? new Date(Number(updatedRaw) * 1000).toISOString() : updatedRaw)
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

function scanProgressMessage(elapsedSec: number, sourceMode: 'file' | 'folder') {
  const sourceLabel = sourceMode === 'folder' ? 'AE 工程文件夹' : 'AE 工程文件'
  if (elapsedSec < 4) return `正在连接 After Effects 并读取${sourceLabel}...`
  if (elapsedSec < 12) return '正在收集文本图层、合成和字体信息...'
  if (elapsedSec < 30) return '正在分析合成结构和图层属性...'
  return '仍在扫描合成内容；大型工程或嵌套合成可能需要更久。'
}

function fontOptionsForTask(fonts: string[], task: AnyRecord): string[] {
  return Array.from(
    new Set(
      [task.target_font, task.source_font, ...fonts]
        .map((item) => String(item || '').trim())
        .filter(Boolean),
    ),
  )
}

import { useEffect, useMemo, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  cancelPhotoshopExecution,
  deletePhotoshopTicket,
  executePhotoshopTicket,
  fetchPhotoshopExecution,
  fetchPhotoshopStatus,
  fetchPhotoshopTicket,
  fetchPhotoshopTickets,
  fetchSystemFonts,
  importPhotoshopTicket,
  scanPhotoshopFolder,
  scanPhotoshopTicket,
  updatePhotoshopTicket,
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

type AnyRecord = Record<string, any>
type TaskFilter = 'all' | 'text' | 'smart_object_text' | 'pending' | 'ready' | 'warning'

export function PhotoshopApp() {
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [activePanel, setActivePanel] = useState<'scan' | 'import' | 'result'>('scan')
  const [tickets, setTickets] = useState<AnyRecord[]>([])
  const [ticketId, setTicketId] = useState('')
  const [ticketText, setTicketText] = useState('')
  const [ticketImportPath, setTicketImportPath] = useState('')
  const [sourceMode, setSourceMode] = useState<'active' | 'file' | 'folder'>('active')
  const [psdPath, setPsdPath] = useState('')
  const [psdFolder, setPsdFolder] = useState('')
  const [targetLanguages, setTargetLanguages] = useState<string[]>([])
  const [languageDraft, setLanguageDraft] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [editingTaskIndex, setEditingTaskIndex] = useState<number | null>(null)
  const [taskFilter, setTaskFilter] = useState<TaskFilter>('all')
  const [taskSearch, setTaskSearch] = useState('')
  const [bulkFont, setBulkFont] = useState('')
  const [fonts, setFonts] = useState<string[]>([])
  const [result, setResult] = useState<unknown>('等待扫描或选择工单')
  const [execution, setExecution] = useState<unknown>('等待执行')
  const [isScanning, setIsScanning] = useState(false)
  const [scanStartedAt, setScanStartedAt] = useState<number | null>(null)
  const [scanElapsedSec, setScanElapsedSec] = useState(0)
  const [scanJob, setScanJob] = useState<AnyRecord | null>(null)

  const parsedTicket = useMemo(() => {
    try {
      return JSON.parse(ticketText || '{}')
    } catch {
      return null
    }
  }, [ticketText])

  const tasks: AnyRecord[] = Array.isArray(parsedTicket?.tasks) ? parsedTicket.tasks : []
  const activeTicket = tickets.find((ticket) => ticket.ticket_id === ticketId)
  const ticketLanguages = uniqueStrings(tasks.map((task) => task.language).filter(Boolean))
  const outputNames = uniqueStrings(tasks.map((task) => task.output_name).filter(Boolean))
  const sourcePsd = activeTicket?.source_psd || parsedTicket?.meta?.source_psd || ''
  const sourceLayerCount = uniqueStrings(tasks.map(taskIdentityKey)).length
  const executableIndexes = automationTaskIndexes(tasks)
  const selectedExecutableCount = selected.filter((index) => executableIndexes.includes(index)).length
  const smartTaskCount = tasks.filter(isSmartObjectTask).length
  const normalTaskCount = tasks.length - smartTaskCount
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

  function addTargetLanguages(raw: string) {
    const nextLanguages = raw
      .split(/[,\n，\s]+/)
      .map((item) => item.trim())
      .filter(Boolean)
    if (!nextLanguages.length) return
    setTargetLanguages((items) => uniqueStrings([...items, ...nextLanguages]))
    setLanguageDraft('')
  }

  function removeTargetLanguage(language: string) {
    setTargetLanguages((items) => items.filter((item) => item !== language))
  }

  function applyLanguageCartToTicket() {
    const nextTicket = rebuildTicketForLanguages(parsedTicket, targetLanguages)
    if (!nextTicket) return
    const nextTasks = Array.isArray(nextTicket.tasks) ? nextTicket.tasks : []
    setTicketText(JSON.stringify(nextTicket, null, 2))
    setSelected(automationTaskIndexes(nextTasks))
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
    setTicketText(JSON.stringify(data.ticket, null, 2))
    setTargetLanguages(uniqueStrings(nextTasks.map((task: AnyRecord) => task.language).filter(Boolean)))
    setSelected(automationTaskIndexes(nextTasks))
    setResult(data)
  }

  async function deleteTicket(nextId: string) {
    const data = await deletePhotoshopTicket(nextId)
    if (ticketId === nextId) {
      setTicketId('')
      setTicketText('')
      setSelected([])
      setTargetLanguages([])
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
      source_mode: sourceMode,
    })
    try {
      const data = sourceMode === 'folder'
        ? await scanPhotoshopFolder({
            directory: psdFolder,
            languages: targetLanguages,
            recursive: true,
            max_files: 30,
          })
        : await scanPhotoshopTicket({
            psd_path: sourceMode === 'file' ? psdPath : '',
            languages: targetLanguages,
          })
      setResult(data)
      if (data.ok) {
        const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
        const returnedLanguages = uniqueStrings(nextTasks.map((task: AnyRecord) => task.language).filter(Boolean))
        setTicketId(data.ticket_id)
        setTicketText(JSON.stringify(data.ticket, null, 2))
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

  async function importTicket() {
    if (!ticketImportPath) {
      setResult({ ok: false, error: '请先选择工单 JSON 文件' })
      return
    }
    try {
      const data = await importPhotoshopTicket(ticketImportPath)
      const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
      setTicketId(data.ticket_id)
      setTicketText(JSON.stringify(data.ticket, null, 2))
      setTargetLanguages(uniqueStrings(nextTasks.map((task: AnyRecord) => task.language).filter(Boolean)))
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
      const data = await updatePhotoshopTicket(ticketId, JSON.parse(ticketText || '{}'))
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
      setExecution(dryRun ? '正在保存工单并执行 Dry Run...' : '正在保存工单并执行，完成后会在 Photoshop 中打开输出 PSD...')
      const saved = await updatePhotoshopTicket(ticketId, JSON.parse(ticketText || '{}'))
      setTicketText(JSON.stringify(saved.ticket, null, 2))
      setActivePanel('result')
      setResult(saved)
      setExecution(await executePhotoshopTicket(ticketId, dryRun, selected))
      await refresh()
    } catch (err: any) {
      setExecution({ ok: false, error: err?.message || '执行失败，请检查工单内容' })
    }
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
        if (runningScan) setScanJob(runningScan)
      } catch {
        // Ignore malformed websocket frames; the local scan state still keeps the UI responsive.
      }
    }
    return () => socket.close()
  }, [isScanning])

  useEffect(() => {
    void fetchSystemFonts({ limit: 700 }).then((data) => {
      const names = uniqueStrings((data.items || []).map((item: AnyRecord) => item.name).filter(Boolean))
      setFonts(names)
    }).catch(() => setFonts([]))
  }, [])

  return (
    <AppLayout>
      <div className="ps-app">
        <aside className="ps-flow-sidebar" aria-label="Photoshop 工单流程">
          <button type="button" className={`ps-flow-step ${activePanel === 'scan' ? 'ps-flow-step--active' : ''}`} onClick={() => setActivePanel('scan')}>
            <span>01</span>
            <div>
              <strong>扫描工单</strong>
              <small>{sourceMode === 'active' ? '当前文档' : sourceMode === 'file' ? '单文件扫描' : '文件夹批量扫描'}</small>
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
        </aside>

        <main className="ps-operation">
        <div className={`ps-metrics ${activePanel === 'import' ? '' : 'ps-panel--hidden'}`}>
          <div className="ps-metric"><span>工单数量</span><strong>{tickets.length}</strong></div>
          <div className="ps-metric"><span>普通文字</span><strong>{normalTaskCount}</strong></div>
          <div className="ps-metric"><span>智能对象文字</span><strong>{smartTaskCount}</strong></div>
          <div className="ps-metric"><span>可执行</span><strong>{executableIndexes.length}</strong></div>
        </div>

        <section className={`ps-panel ps-scan-panel ${activePanel === 'scan' ? '' : 'ps-panel--hidden'}`}>
          <div className="ps-section-head">
            <div>
              <h3>扫描工单</h3>
              <p>选择 PSD 来源并扫描文本图层，扫描成功后会自动导入为当前工单。</p>
            </div>
            <ToolbarButton onClick={() => void refresh()} disabled={isScanning}>刷新状态</ToolbarButton>
          </div>
          <div className="ps-source-tabs" role="tablist" aria-label="Photoshop source mode">
            <button className={`ps-source-tab ${sourceMode === 'active' ? 'ps-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('active')} disabled={isScanning}>当前文档</button>
            <button className={`ps-source-tab ${sourceMode === 'file' ? 'ps-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('file')} disabled={isScanning}>单文件</button>
            <button className={`ps-source-tab ${sourceMode === 'folder' ? 'ps-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('folder')} disabled={isScanning}>文件夹批量</button>
          </div>
          <div className="ps-form-grid">
            {sourceMode === 'file' ? (
              <Field label="PSD 文件">
                <PathInput value={psdPath} onChange={setPsdPath} mode="file" placeholder="选择一个 PSD 或 PSB 文件" />
              </Field>
            ) : sourceMode === 'folder' ? (
              <Field label="PSD 文件夹">
                <PathInput value={psdFolder} onChange={setPsdFolder} mode="directory" placeholder="选择包含 PSD/PSB 的文件夹" />
              </Field>
            ) : (
              <Field label="Photoshop 活动文档">
                <input value="留空时读取当前 Photoshop 活动文档" readOnly />
              </Field>
            )}
            <div className="ps-language-hint">
              <span>目标语言</span>
              <strong>{targetLanguages.length ? targetLanguages.join(', ') : '原始任务'}</strong>
              <small>在下方输出购物车中添加语言；留空只生成原始任务。</small>
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
              <p>{scanJob?.stage || scanProgressMessage(scanElapsedSec, sourceMode)}</p>
              {scanJob?.scan_current_file ? (
                <small>当前文件：{scanJob.scan_current_file}（{scanJob.scan_file_index || 1}/{scanJob.scan_file_total || 1}）</small>
              ) : null}
              <small>看到 Photoshop 打开/关闭智能对象属于正常扫描过程，请不要手动切换或关闭文档。</small>
            </div>
          ) : null}
          <PrimaryButton onClick={() => void scan()} disabled={isScanning}>
            {isScanning ? '扫描中，请稍候...' : '扫描并生成工单'}
          </PrimaryButton>
        </section>

        <div className={`ps-workspace ${activePanel === 'import' ? '' : 'ps-workspace--hidden'}`}>
          <section className="ps-panel ps-ticket-panel">
            <div className="ps-ticket-head">
              <div>
                <h3>导入工单</h3>
                <p>{ticketId ? `当前工单：${ticketId}` : '扫描成功后会自动导入当前工单，也可以从历史工单中手动导入。'}</p>
              </div>
              <span>{tickets.length} 个工单</span>
            </div>

            <div className="ps-import-file">
              <Field label="导入工单文件">
                <PathInput value={ticketImportPath} onChange={setTicketImportPath} mode="file" placeholder="选择 Photoshop 工单 JSON 文件" />
              </Field>
              <PrimaryButton onClick={importTicket}>导入并设为当前工单</PrimaryButton>
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
                    </span>
                    <span className="ps-ticket-time">建立：{formatTicketTime(ticket.created_at, ticket.updated_at)}</span>
                    <span>{ticket.source_psd || '未记录来源'}</span>
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
            <div className="ps-output-cart">
              <div className="ps-output-cart-head">
                <div>
                  <strong>目标语言购物车</strong>
                  <small>一个工单可输出多个目标语言。</small>
                </div>
                <em>{targetLanguages.length || 1} 组输出</em>
              </div>
              <div className="ps-language-chips">
                {targetLanguages.length ? targetLanguages.map((language) => (
                  <button type="button" key={language} onClick={() => removeTargetLanguage(language)}>
                    {language}<span>×</span>
                  </button>
                )) : <span className="ps-language-empty">原始任务</span>}
              </div>
              <div className="ps-language-presets" aria-label="常用目标语言">
                {['zh-CN', 'en-US', 'ja-JP', 'ko-KR'].map((language) => (
                  <button type="button" key={language} onClick={() => addTargetLanguages(language)}>{language}</button>
                ))}
              </div>
              <div className="ps-language-add">
                <input
                  value={languageDraft}
                  onChange={(event) => setLanguageDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      addTargetLanguages(languageDraft)
                    }
                  }}
                  placeholder="输入 zh-CN,en-US"
                />
                <ToolbarButton onClick={() => addTargetLanguages(languageDraft)}>添加</ToolbarButton>
              </div>
              <div className="ps-cart-stats">
                <span><b>{sourceLayerCount || tasks.length || 0}</b> 源图层</span>
                <span><b>{targetLanguages.length || ticketLanguages.length || 0}</b> 目标语言</span>
                <span><b>{outputNames.length || (targetLanguages.length ? targetLanguages.length : 0)}</b> 输出文件</span>
              </div>
              <ToolbarButton onClick={applyLanguageCartToTicket} disabled={!ticketId || !tasks.length}>应用到当前工单</ToolbarButton>
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
              <span><b>1</b> 填替换文案</span>
              <span><b>2</b> 选择字体和输出名</span>
              <span><b>3</b> 确认后执行</span>
              <em>{selectedExecutableCount}/{executableIndexes.length} 已选可执行</em>
            </div>
            <div className="ps-task-controls">
              <input
                aria-label="搜索 Photoshop 任务"
                value={taskSearch}
                onChange={(event) => setTaskSearch(event.target.value)}
                placeholder="搜索原文、图层、智能对象或画板"
              />
              <div className="ps-task-filter" role="tablist" aria-label="Photoshop 任务分类">
                {taskFilters.map((filter) => (
                  <button
                    type="button"
                    key={filter.id}
                    className={taskFilter === filter.id ? 'ps-filter--active' : ''}
                    onClick={() => setTaskFilter(filter.id)}
                  >
                    {filter.label}
                    <span>{filterCount(tasks, filter.id)}</span>
                  </button>
                ))}
              </div>
              <div className="ps-task-bulk">
                <FontPicker
                  ariaLabel="批量目标字体"
                  value={bulkFont}
                  sourceFont=""
                  fonts={fonts}
                  onChange={setBulkFont}
                />
                <ToolbarButton onClick={applyBulkFontToVisibleTasks} disabled={!bulkFont.trim() || !visibleIndexes.length}>批量设置字体</ToolbarButton>
                <ToolbarButton onClick={confirmVisibleTasks} disabled={!visibleIndexes.length}>批量确认当前筛选</ToolbarButton>
              </div>
              {warningTaskCount ? <p className="ps-task-warning">有 {warningTaskCount} 个任务带错误或备注，建议筛选“有错误/警告”后复核。</p> : null}
            </div>
            <div className="ps-task-list">
              {filteredTaskEntries.length ? filteredTaskEntries.map(({ task, index }) => {
                const ready = isAutomationTaskExecutable(task)
                const smart = isSmartObjectTask(task)
                return (
                  <div className={`ps-task ${selected.includes(index) ? 'ps-task--selected' : ''} ${smart ? 'ps-task--smart' : ''}`} key={index}>
                    <label className="ps-task-check">
                      <input
                        type="checkbox"
                        checked={selected.includes(index)}
                        disabled={!ready}
                        onChange={(event) => toggleTask(index, event.target.checked)}
                      />
                      <span>{index + 1}</span>
                    </label>
                    <div className="ps-task-main">
                      <div className="ps-task-title">
                        <div>
                          <strong>{smart ? task.smart_object_inner_layer_name || task.layer_name || `任务 ${index + 1}` : task.layer_name || `任务 ${index + 1}`}</strong>
                          <small>{task.language || '未指定语言'} · {task.original_text || '未读取原文'}</small>
                          <div className="ps-task-context">
                            {smart ? (
                              <>
                                <span>智能对象：{task.smart_object_name || '未记录父层'}</span>
                                <span>内部文字层：{task.smart_object_inner_layer_name || task.layer_name || '未记录内层'}</span>
                              </>
                            ) : <span>普通文字层：{task.layer_name || '未命名图层'}</span>}
                            <span>画板：{task.artboard_name || '未记录画板'}</span>
                            {task.notes ? <span>备注：{task.notes}</span> : null}
                          </div>
                        </div>
                        <div className="ps-task-badges">
                          <em className={smart ? 'ps-badge ps-badge--smart' : 'ps-badge ps-badge--layer'}>{smart ? '智能对象内文字层' : '普通文字层'}</em>
                          <em className={hasTaskWarning(task) ? 'ps-badge ps-badge--warning' : ready ? 'ps-badge ps-badge--ready' : 'ps-badge'}>{hasTaskWarning(task) ? '有错误/警告' : ready ? '可执行' : '待确认'}</em>
                        </div>
                      </div>
                      <div className="ps-task-preview">
                        <label>
                          <b>替换</b>
                          <textarea
                            aria-label={`替换文本 ${index + 1}`}
                            value={task.target_text || ''}
                            onChange={(event) => updateTask(index, { target_text: event.target.value })}
                            placeholder="待填写"
                          />
                        </label>
                        <FontPicker
                          ariaLabel={`目标字体 ${index + 1}`}
                          value={task.target_font || ''}
                          sourceFont={task.source_font}
                          fonts={fontOptionsForTask(fonts, task)}
                          onChange={(font) => updateTask(index, { target_font: font })}
                        />
                        <label>
                          <b>输出</b>
                          <input
                            aria-label={`输出名称 ${index + 1}`}
                            value={task.output_name || ''}
                            onChange={(event) => updateTask(index, { output_name: event.target.value })}
                            placeholder="默认命名"
                          />
                        </label>
                        <ToolbarButton onClick={() => confirmTask(index)}>确认修改</ToolbarButton>
                      </div>
                    </div>
                  </div>
                )
              }) : <div className="ps-empty">{tasks.length ? '当前筛选没有匹配任务。' : '等待扫描或选择工单。'}</div>}
            </div>
            <div className="ps-execute-dock" aria-label="工单执行操作">
              <div>
                <strong>{selectedExecutableCount ? `${selectedExecutableCount} 个任务已准备执行` : '确认任务后执行'}</strong>
                <small>确认修改会自动勾选任务；点击右侧按钮会先保存工单，再生成并打开输出 PSD。</small>
              </div>
              <div className="ps-execute-dock-actions">
                <ToolbarButton onClick={save} disabled={!ticketId}>只保存</ToolbarButton>
                <ToolbarButton onClick={() => void execute(true)} disabled={!ticketId || !selected.length}>Dry Run</ToolbarButton>
                <PrimaryButton onClick={() => void execute(false)} disabled={!ticketId || !selected.length}>保存并执行</PrimaryButton>
              </div>
            </div>
          </section>
        </div>

        <section className={`ps-panel ps-execute-panel ${activePanel === 'result' ? '' : 'ps-panel--hidden'}`}>
          <div className="ps-section-head">
            <div>
              <h3>执行与回执</h3>
              <p>保存确认后的工单，再执行已选择任务；Dry Run 可先检查将要执行的内容。</p>
            </div>
            <div className="ps-actions">
              <ToolbarButton onClick={save} disabled={!ticketId}>保存工单</ToolbarButton>
              <PrimaryButton onClick={() => void execute(false)} disabled={!ticketId || !selected.length}>执行已选任务</PrimaryButton>
              <ToolbarButton onClick={() => void execute(true)} disabled={!ticketId || !selected.length}>Dry Run</ToolbarButton>
              <ToolbarButton onClick={refreshExecution} disabled={!ticketId}>刷新执行状态</ToolbarButton>
              <ToolbarButton onClick={async () => ticketId && setExecution(await cancelPhotoshopExecution(ticketId))} disabled={!ticketId}>取消执行</ToolbarButton>
            </div>
          </div>
          <div className="ps-result-grid">
            <ResultBox value={result} />
            <ResultBox value={execution} />
          </div>
          <details className="ps-json">
            <summary>高级：工单 JSON</summary>
            <textarea value={ticketText} onChange={(event) => setTicketText(event.target.value)} />
          </details>
        </section>
        </main>
        <AutomationTaskDialog
          open={editingTaskIndex !== null}
          title={`Photoshop 任务 ${(editingTaskIndex ?? 0) + 1}`}
          task={editingTaskIndex !== null ? tasks[editingTaskIndex] : null}
          index={editingTaskIndex ?? -1}
          selected={editingTaskIndex !== null ? selected.includes(editingTaskIndex) : false}
          fonts={fonts}
          accent="blue"
          onClose={() => setEditingTaskIndex(null)}
          onSave={saveTaskDialog}
        />
      </div>
    </AppLayout>
  )
}

function uniqueStrings(items: unknown[]) {
  return Array.from(new Set(items.map((item) => String(item || '').trim()).filter(Boolean)))
}

function uniqueNumbers(items: number[]) {
  return Array.from(new Set(items))
}

const taskFilters: { id: TaskFilter, label: string }[] = [
  { id: 'all', label: '全部' },
  { id: 'text', label: '普通文字层' },
  { id: 'smart_object_text', label: '智能对象内文字层' },
  { id: 'pending', label: '待确认' },
  { id: 'ready', label: '可执行' },
  { id: 'warning', label: '有错误/警告' },
]

function isSmartObjectTask(task: AnyRecord) {
  return task.layer_kind === 'smart_object_text' || Number(task.smart_object_layer_id || 0) > 0
}

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
  return [
    task.layer_name,
    task.smart_object_name,
    task.smart_object_inner_layer_name,
    task.artboard_name,
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

function rebuildTicketForLanguages(ticket: AnyRecord | null, languages: string[]) {
  if (!ticket || !Array.isArray(ticket.tasks)) return null
  const bases = new Map<string, AnyRecord>()
  ticket.tasks.forEach((task: AnyRecord) => {
    const key = taskIdentityKey(task)
    if (!bases.has(key)) bases.set(key, task)
  })

  const nextLanguages = uniqueStrings(languages)
  const nextTasks = Array.from(bases.entries()).flatMap(([key, baseTask]) => {
    if (!nextLanguages.length) {
      const existing = ticket.tasks.find((task: AnyRecord) => taskIdentityKey(task) === key && !task.language) || baseTask
      return [{ ...existing, language: '', output_name: existing.output_name || '' }]
    }
    return nextLanguages.map((language) => {
      const existing = ticket.tasks.find((task: AnyRecord) => taskIdentityKey(task) === key && task.language === language)
      return {
        ...baseTask,
        ...existing,
        language,
        output_name: existing?.output_name || `${language}.psd`,
      }
    })
  })

  return {
    ...ticket,
    tasks: nextTasks,
  }
}

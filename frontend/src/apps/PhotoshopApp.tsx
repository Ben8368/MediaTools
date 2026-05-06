import { useEffect, useMemo, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  cancelPhotoshopExecution,
  executePhotoshopTicket,
  fetchPhotoshopExecution,
  fetchPhotoshopStatus,
  fetchPhotoshopTicket,
  fetchPhotoshopTickets,
  fetchSystemFonts,
  scanPhotoshopFolder,
  scanPhotoshopTicket,
  updatePhotoshopTicket,
} from '@/api'
import {
  Field,
  PathInput,
  PrimaryButton,
  ResultBox,
  ToolbarButton,
} from '@/apps/mediatools/primitives'
import { AutomationTaskDialog } from '@/apps/mediatools/AutomationTaskDialog'
import {
  automationTaskIndexes,
  isAutomationTaskExecutable,
  patchAutomationTask,
} from '@/apps/mediatools/automation'

type AnyRecord = Record<string, any>

export function PhotoshopApp() {
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [tickets, setTickets] = useState<AnyRecord[]>([])
  const [ticketId, setTicketId] = useState('')
  const [ticketText, setTicketText] = useState('')
  const [sourceMode, setSourceMode] = useState<'active' | 'file' | 'folder'>('active')
  const [psdPath, setPsdPath] = useState('')
  const [psdFolder, setPsdFolder] = useState('')
  const [languages, setLanguages] = useState('zh-CN,en-US')
  const [selected, setSelected] = useState<number[]>([])
  const [editingTaskIndex, setEditingTaskIndex] = useState<number | null>(null)
  const [fonts, setFonts] = useState<string[]>([])
  const [result, setResult] = useState<unknown>('等待扫描或选择工单')
  const [execution, setExecution] = useState<unknown>('等待执行')

  const parsedTicket = useMemo(() => {
    try {
      return JSON.parse(ticketText || '{}')
    } catch {
      return null
    }
  }, [ticketText])

  const tasks: AnyRecord[] = Array.isArray(parsedTicket?.tasks) ? parsedTicket.tasks : []
  const executableIndexes = automationTaskIndexes(tasks)
  const selectedExecutableCount = selected.filter((index) => executableIndexes.includes(index)).length
  const activeTicket = tickets.find((ticket) => ticket.ticket_id === ticketId)
  const automationReady = Boolean(status?.available)
  const appRunning = Boolean(status?.app_running)
  const serviceLabel = automationReady ? '服务正常' : '服务异常'
  const serviceMessage = automationReady ? '自动化接口已就绪' : '自动化不可用'
  const appLabel = appRunning ? '软件已打开' : '软件未打开'
  const appMessage = appRunning ? 'Photoshop 运行中' : 'Photoshop 未运行'

  function updateTask(index: number, patch: AnyRecord) {
    const nextTicket = patchAutomationTask(parsedTicket, index, patch)
    if (!nextTicket) return
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

  async function refresh() {
    const [statusData, ticketData] = await Promise.all([fetchPhotoshopStatus(), fetchPhotoshopTickets()])
    setStatus(statusData)
    setTickets(ticketData.items || [])
  }

  async function loadTicket(nextId: string) {
    setTicketId(nextId)
    const data = await fetchPhotoshopTicket(nextId)
    const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
    setTicketText(JSON.stringify(data.ticket, null, 2))
    setSelected(automationTaskIndexes(nextTasks))
    setResult(data)
  }

  async function scan() {
    const languageList = languages.split(',').map((item) => item.trim()).filter(Boolean)
    const data = sourceMode === 'folder'
      ? await scanPhotoshopFolder({
          directory: psdFolder,
          languages: languageList,
          recursive: true,
          max_files: 30,
        })
      : await scanPhotoshopTicket({
          psd_path: sourceMode === 'file' ? psdPath : '',
          languages: languageList,
        })
    setResult(data)
    if (data.ok) {
      const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
      setTicketId(data.ticket_id)
      setTicketText(JSON.stringify(data.ticket, null, 2))
      setSelected(automationTaskIndexes(nextTasks))
      await refresh()
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
    setExecution(await executePhotoshopTicket(ticketId, dryRun, selected))
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
    void fetchSystemFonts({ limit: 700 }).then((data) => {
      const names = (data.items || []).map((item: AnyRecord) => item.name).filter(Boolean)
      setFonts(names)
    }).catch(() => setFonts([]))
  }, [])

  return (
    <AppLayout>
      <div className="ps-app">
        <section className="ps-hero">
          <div>
            <div className="ps-eyebrow">Adobe Automation</div>
            <h2>Photoshop 自动化</h2>
            <p>扫描 PSD 文本图层，生成可确认的工单；逐项修改替换文本、字体和输出名后，再提交给 Photoshop 执行。</p>
          </div>
          <div className={`ps-ready ${automationReady && appRunning ? 'ps-ready--online' : 'ps-ready--offline'}`}>
            <div className="ps-ready-line">
              <span>{serviceLabel}</span>
              <small>{serviceMessage}</small>
            </div>
            <div className="ps-ready-line">
              <span>{appLabel}</span>
              <small>{appMessage}</small>
            </div>
          </div>
        </section>

        <div className="ps-metrics">
          <div className="ps-metric"><span>工单数量</span><strong>{tickets.length}</strong></div>
          <div className="ps-metric"><span>内容项</span><strong>{tasks.length}</strong></div>
          <div className="ps-metric"><span>可执行</span><strong>{executableIndexes.length}</strong></div>
          <div className="ps-metric"><span>已选择</span><strong>{selectedExecutableCount}</strong></div>
        </div>

        <section className="ps-panel ps-scan-panel">
          <div className="ps-section-head">
            <div>
              <h3>1. 选择来源</h3>
              <p>可以选择 PSD 文件；留空时读取当前 Photoshop 活动文档。</p>
            </div>
            <ToolbarButton onClick={() => void refresh()}>刷新状态</ToolbarButton>
          </div>
          <div className="ps-source-tabs" role="tablist" aria-label="Photoshop source mode">
            <button className={`ps-source-tab ${sourceMode === 'active' ? 'ps-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('active')}>当前文档</button>
            <button className={`ps-source-tab ${sourceMode === 'file' ? 'ps-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('file')}>单文件</button>
            <button className={`ps-source-tab ${sourceMode === 'folder' ? 'ps-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('folder')}>文件夹批量</button>
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
            <Field label="语言">
              <input value={languages} onChange={(event) => setLanguages(event.target.value)} placeholder="zh-CN,en-US" />
            </Field>
          </div>
          <PrimaryButton onClick={scan}>扫描并生成工单</PrimaryButton>
        </section>

        <div className="ps-workspace">
          <section className="ps-panel">
            <div className="ps-section-head">
              <div>
                <h3>2. 选择工单</h3>
                <p>{activeTicket?.source_psd || '选择已有工单，或先扫描一个 PSD 文件。'}</p>
              </div>
              <span>{tickets.length} 个</span>
            </div>
            <div className="ps-ticket-list">
              {tickets.length ? tickets.map((ticket) => (
                <button
                  className={`ps-ticket ${ticket.ticket_id === ticketId ? 'ps-ticket--active' : ''}`}
                  key={ticket.ticket_id}
                  onClick={() => void loadTicket(ticket.ticket_id)}
                >
                  <strong>{ticket.ticket_id?.slice(0, 8) || '未命名'}</strong>
                  <span>{ticket.source_psd || '未记录来源'}</span>
                  <small>{ticket.task_count || 0} 个任务</small>
                </button>
              )) : <div className="ps-empty">暂无工单，请先扫描 PSD。</div>}
            </div>
          </section>

          <section className="ps-panel">
            <div className="ps-section-head">
              <div>
                <h3>3. 确认任务</h3>
                <p>逐项确认要替换的文本、字体和输出名；标记为跳过的任务不会执行。</p>
              </div>
              <div className="ps-actions">
                <ToolbarButton onClick={() => setSelected(executableIndexes)} disabled={!tasks.length}>选择可执行</ToolbarButton>
                <ToolbarButton onClick={() => setSelected([])} disabled={!tasks.length}>清空选择</ToolbarButton>
              </div>
            </div>
            <div className="ps-task-list">
              {tasks.length ? tasks.map((task, index) => {
                const ready = isAutomationTaskExecutable(task)
                return (
                  <div className={`ps-task ${selected.includes(index) ? 'ps-task--selected' : ''}`} key={index}>
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
                          <strong>{task.layer_name || `任务 ${index + 1}`}</strong>
                          <small>{task.language || '未指定语言'} · {task.original_text || '未读取原文'}</small>
                        </div>
                        <em className={ready ? 'ps-badge ps-badge--ready' : 'ps-badge'}>{ready ? '可执行' : '待确认'}</em>
                      </div>
                      <div className="ps-task-preview">
                        <span><b>替换</b>{task.target_text || '待填写'}</span>
                        <span><b>字体</b>{task.target_font || task.source_font || '未指定'}</span>
                        <span><b>输出</b>{task.output_name || '默认命名'}</span>
                        <ToolbarButton onClick={() => setEditingTaskIndex(index)}>确认修改</ToolbarButton>
                      </div>
                    </div>
                  </div>
                )
              }) : <div className="ps-empty">等待扫描或选择工单。</div>}
            </div>
          </section>
        </div>

        <section className="ps-panel ps-execute-panel">
          <div className="ps-section-head">
            <div>
              <h3>4. 执行与回执</h3>
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

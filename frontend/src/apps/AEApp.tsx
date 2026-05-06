import { useEffect, useMemo, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  addAERenderQueue,
  cancelAEExecution,
  createAECheckpoint,
  executeAETicket,
  fetchAECheckpoints,
  fetchAEExecution,
  fetchAERenderStatus,
  fetchAEStatus,
  fetchAETicket,
  fetchAETickets,
  fetchSystemFonts,
  scanAEFolder,
  scanAETicket,
  startAERender,
  updateAETicket,
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

export function AEApp() {
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [tickets, setTickets] = useState<AnyRecord[]>([])
  const [ticketId, setTicketId] = useState('')
  const [ticketText, setTicketText] = useState('')
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
  const selectedExecutableCount = selected.filter((index) => executableIndexes.includes(index)).length
  const automationReady = Boolean(status?.available)
  const appRunning = Boolean(status?.app_running)
  const serviceLabel = automationReady ? '服务正常' : '服务异常'
  const serviceMessage = automationReady ? '自动化接口已就绪' : '自动化不可用'
  const appLabel = appRunning ? '软件已打开' : '软件未打开'
  const appMessage = appRunning ? 'After Effects 运行中' : 'After Effects 未运行'

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
    const [statusData, ticketData] = await Promise.all([fetchAEStatus(), fetchAETickets()])
    setStatus(statusData)
    setTickets(ticketData.items || [])
  }

  async function loadTicket(nextId: string) {
    setTicketId(nextId)
    const data = await fetchAETicket(nextId)
    const nextTasks = Array.isArray(data.ticket?.tasks) ? data.ticket.tasks : []
    const sourceProject = data.ticket?.meta?.source_project || ''
    setTicketText(JSON.stringify(data.ticket, null, 2))
    setProjectPath((current) => current || sourceProject)
    setSelected(automationTaskIndexes(nextTasks))
    setResult(data)
  }

  async function scan() {
    const data = sourceMode === 'folder'
      ? await scanAEFolder({ directory: projectFolder, recursive: true, max_files: 30 })
      : await scanAETicket({ file_path: projectPath })
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
    setExecution(await executeAETicket(ticketId, dryRun, selected))
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
    void fetchSystemFonts({ limit: 700 }).then((data) => {
      const names = (data.items || []).map((item: AnyRecord) => item.name).filter(Boolean)
      setFonts(names)
    }).catch(() => setFonts([]))
  }, [])

  return (
    <AppLayout>
      <div className="ae-app">
        <section className="ae-hero">
          <div>
            <div className="ae-eyebrow">Adobe Automation</div>
            <h2>After Effects 自动化</h2>
            <p>扫描 AE 工程中的文本图层，生成可确认的工单；逐项修改替换文本、字体和输出工程后，再提交给 AE 执行。</p>
          </div>
          <div className={`ae-ready ${automationReady && appRunning ? 'ae-ready--online' : 'ae-ready--offline'}`}>
            <div className="ae-ready-line">
              <span>{serviceLabel}</span>
              <small>{serviceMessage}</small>
            </div>
            <div className="ae-ready-line">
              <span>{appLabel}</span>
              <small>{appMessage}</small>
            </div>
          </div>
        </section>

        <div className="ae-metrics">
          <div className="ae-metric"><span>工单数量</span><strong>{tickets.length}</strong></div>
          <div className="ae-metric"><span>内容项</span><strong>{tasks.length}</strong></div>
          <div className="ae-metric"><span>可执行</span><strong>{executableIndexes.length}</strong></div>
          <div className="ae-metric"><span>已选择</span><strong>{selectedExecutableCount}</strong></div>
        </div>

        <section className="ae-panel">
          <div className="ae-section-head">
            <div>
              <h3>1. 选择来源</h3>
              <p>选择 `.aep` 工程文件后扫描文本图层，系统会生成可确认的 AE 工单。</p>
            </div>
            <ToolbarButton onClick={() => void refresh()}>刷新状态</ToolbarButton>
          </div>
          <div className="ae-source-tabs" role="tablist" aria-label="After Effects source mode">
            <button className={`ae-source-tab ${sourceMode === 'file' ? 'ae-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('file')}>单文件</button>
            <button className={`ae-source-tab ${sourceMode === 'folder' ? 'ae-source-tab--active' : ''}`} type="button" onClick={() => setSourceMode('folder')}>文件夹批量</button>
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
          <PrimaryButton onClick={scan}>扫描并生成工单</PrimaryButton>
        </section>

        <div className="ae-workspace">
          <section className="ae-panel">
            <div className="ae-section-head">
              <div>
                <h3>2. 选择工单</h3>
                <p>{activeTicket?.source_project || '选择已有工单，或先扫描一个 AE 工程。'}</p>
              </div>
              <span>{tickets.length} 个</span>
            </div>
            <div className="ae-ticket-list">
              {tickets.length ? tickets.map((ticket) => (
                <button
                  className={`ae-ticket ${ticket.ticket_id === ticketId ? 'ae-ticket--active' : ''}`}
                  key={ticket.ticket_id}
                  onClick={() => void loadTicket(ticket.ticket_id)}
                >
                  <strong>{ticket.ticket_id?.slice(0, 8) || '未命名'}</strong>
                  <span>{ticket.source_project || '未记录工程'}</span>
                  <small>{ticket.task_count || 0} 个任务 · {ticket.confirmed_count || 0} 已确认</small>
                </button>
              )) : <div className="ae-empty">暂无工单，请先扫描 AE 工程。</div>}
            </div>
          </section>

          <section className="ae-panel">
            <div className="ae-section-head">
              <div>
                <h3>3. 确认任务</h3>
                <p>逐项确认要替换的文本、字体和输出工程；标记为跳过的任务不会执行。</p>
              </div>
              <div className="ae-actions">
                <ToolbarButton onClick={() => setSelected(executableIndexes)} disabled={!tasks.length}>选择可执行</ToolbarButton>
                <ToolbarButton onClick={() => setSelected([])} disabled={!tasks.length}>清空选择</ToolbarButton>
              </div>
            </div>
            <div className="ae-task-list">
              {tasks.length ? tasks.map((task, index) => {
                const ready = isAutomationTaskExecutable(task)
                return (
                  <div className={`ae-task ${selected.includes(index) ? 'ae-task--selected' : ''}`} key={index}>
                    <label className="ae-task-check">
                      <input
                        type="checkbox"
                        checked={selected.includes(index)}
                        disabled={!ready}
                        onChange={(event) => toggleTask(index, event.target.checked)}
                      />
                      <span>{index + 1}</span>
                    </label>
                    <div className="ae-task-main">
                      <div className="ae-task-title">
                        <div>
                          <strong>{task.layer_name || `任务 ${index + 1}`}</strong>
                          <small>{task.comp_name || '未命名合成'} · {task.source_font || '未知字体'} · {task.original_text || '未读取原文'}</small>
                        </div>
                        <em className={ready ? 'ae-badge ae-badge--ready' : 'ae-badge'}>{ready ? '可执行' : '待确认'}</em>
                      </div>
                      <div className="ae-task-preview">
                        <span><b>替换</b>{task.target_text || '待填写'}</span>
                        <span><b>字体</b>{task.target_font || task.source_font || '未指定'}</span>
                        <span><b>输出</b>{task.output_name || '默认命名'}</span>
                        <ToolbarButton onClick={() => setEditingTaskIndex(index)}>确认修改</ToolbarButton>
                      </div>
                    </div>
                  </div>
                )
              }) : <div className="ae-empty">等待扫描或选择工单。</div>}
            </div>
          </section>
        </div>

        <div className="ae-tools">
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

        <section className="ae-panel ae-execute-panel">
          <div className="ae-section-head">
            <div>
              <h3>4. 执行与回执</h3>
              <p>保存确认后的工单，再执行已选择任务；Dry Run 可先检查将要执行的内容。</p>
            </div>
            <div className="ae-actions">
              <ToolbarButton onClick={save} disabled={!ticketId}>保存工单</ToolbarButton>
              <PrimaryButton onClick={() => void execute(false)} disabled={!ticketId || !selected.length}>执行已选任务</PrimaryButton>
              <ToolbarButton onClick={() => void execute(true)} disabled={!ticketId || !selected.length}>Dry Run</ToolbarButton>
              <ToolbarButton onClick={refreshExecution} disabled={!ticketId}>刷新执行状态</ToolbarButton>
              <ToolbarButton onClick={async () => ticketId && setExecution(await cancelAEExecution(ticketId))} disabled={!ticketId}>取消执行</ToolbarButton>
            </div>
          </div>
          <div className="ae-result-grid">
            <ResultBox value={result} />
            <ResultBox value={execution} />
          </div>
          <details className="ae-json">
            <summary>高级：工单 JSON</summary>
            <textarea value={ticketText} onChange={(event) => setTicketText(event.target.value)} />
          </details>
        </section>
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

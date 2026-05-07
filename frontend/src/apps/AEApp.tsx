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
                    <span>{ticket.source_project || '未记录工程'}</span>
                    <small>{ticket.confirmed_count || 0} 已确认</small>
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

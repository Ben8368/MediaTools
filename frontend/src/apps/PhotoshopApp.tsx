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
  const activeTicket = tickets.find((ticket) => ticket.ticket_id === ticketId)
  const ticketLanguages = uniqueStrings(tasks.map((task) => task.language).filter(Boolean))
  const outputNames = uniqueStrings(tasks.map((task) => task.output_name).filter(Boolean))
  const sourcePsd = activeTicket?.source_psd || parsedTicket?.meta?.source_psd || ''
  const sourceLayerCount = uniqueStrings(tasks.map(taskIdentityKey)).length
  const executableIndexes = automationTaskIndexes(tasks)
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

  function confirmTask(index: number) {
    updateTask(index, { status: 'confirmed' })
    toggleTask(index, true)
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
        <section className="ps-hero">
          <div>
            <div className="ps-eyebrow">Adobe Automation</div>
            <h2>Photoshop 自动化</h2>
            <p>左侧按扫描工单、导入工单组织流程；右侧完成来源扫描、当前工单确认和执行。</p>
          </div>
        </section>

        <div className="ps-metrics">
          <div className="ps-metric"><span>工单数量</span><strong>{tickets.length}</strong></div>
          <div className="ps-metric"><span>内容项</span><strong>{tasks.length}</strong></div>
          <div className="ps-metric"><span>可执行</span><strong>{executableIndexes.length}</strong></div>
          <div className="ps-metric"><span>已选择</span><strong>{selectedExecutableCount}</strong></div>
        </div>

        <section className={`ps-panel ps-scan-panel ${activePanel === 'scan' ? '' : 'ps-panel--hidden'}`}>
          <div className="ps-section-head">
            <div>
              <h3>扫描工单</h3>
              <p>选择 PSD 来源并扫描文本图层，扫描成功后会自动导入为当前工单。</p>
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
            <div className="ps-language-hint">
              <span>目标语言</span>
              <strong>{targetLanguages.length ? targetLanguages.join(', ') : '原始任务'}</strong>
              <small>在下方输出购物车中添加语言；留空只生成原始任务。</small>
            </div>
          </div>
          <PrimaryButton onClick={scan}>扫描并生成工单</PrimaryButton>
        </section>

        <div className="ps-workspace">
          <section className={`ps-panel ps-ticket-panel ${activePanel === 'import' ? '' : 'ps-panel--hidden'}`}>
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

          <section className={`ps-panel ps-output-panel ${activePanel === 'import' ? '' : 'ps-panel--hidden'}`}>
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
                        <label>
                          <b>替换</b>
                          <textarea
                            aria-label={`替换文本 ${index + 1}`}
                            value={task.target_text || ''}
                            onChange={(event) => updateTask(index, { target_text: event.target.value })}
                            placeholder="待填写"
                          />
                        </label>
                        <label>
                          <b>字体</b>
                          <select
                            aria-label={`目标字体 ${index + 1}`}
                            value={task.target_font || ''}
                            onChange={(event) => updateTask(index, { target_font: event.target.value })}
                          >
                            <option value="">
                              {task.source_font ? `沿用源字体：${task.source_font}` : '沿用源字体'}
                            </option>
                            {fontOptionsForTask(fonts, task).map((font) => (
                              <option value={font} key={font}>{font}</option>
                            ))}
                          </select>
                        </label>
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
              }) : <div className="ps-empty">等待扫描或选择工单。</div>}
            </div>
          </section>
        </div>

        <section className="ps-panel ps-execute-panel">
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

function taskIdentityKey(task: AnyRecord) {
  return [
    task.layer_id,
    task.artboard_name,
    task.layer_name,
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

import { useCallback, useEffect, useMemo, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  cancelTask,
  clearTaskRecords,
  fetchAssets,
  getActiveTasks,
  getModules,
  getSystemStatus,
  getWeeklyHistory,
  getWorkspace,
  runDecryptor,
  runEncoder,
  setWorkspace,
} from '@/api'
import { CategoryIcon, DeleteIcon, PlusIcon, RetryIcon, SearchIcon, SelectAllIcon, StatusIcon, StopIcon } from '@/apps/downloader/icons'
import { formatRelativeTime, mergeTasks } from '@/apps/downloader/helpers'
import type { DownloadTask } from '@/apps/downloader/types'
import {
  Field,
  PathInput,
  PrimaryButton,
  ResultBox,
  ToolbarButton,
} from '@/apps/mediatools/primitives'
import type { AnyRecord } from '@/types'

type DecryptCategory = 'all' | 'running' | 'completed' | 'pending' | 'stopped' | 'error'

const DECRYPT_CATEGORIES: Array<{ key: DecryptCategory; label: string; icon: string }> = [
  { key: 'all', label: '全部', icon: 'grid' },
  { key: 'running', label: '解密中', icon: 'download' },
  { key: 'completed', label: '已完成', icon: 'check' },
  { key: 'pending', label: '等待', icon: 'idle' },
  { key: 'stopped', label: '已停止', icon: 'pause' },
  { key: 'error', label: '错误', icon: 'error' },
]

function isDecryptTask(task: DownloadTask) {
  return task.type === 'decrypt'
}

function getDecryptCategory(task: DownloadTask): DecryptCategory {
  if (task.status === 'running') return 'running'
  if (task.status === 'completed') return 'completed'
  if (task.status === 'pending') return 'pending'
  if (task.status === 'failed') return 'error'
  if (task.status === 'cancelled' || task.status === 'paused') return 'stopped'
  return 'pending'
}

function isDecryptCancellable(task: DownloadTask) {
  return task.status === 'pending' || task.status === 'running'
}

function isDecryptClearable(task: DownloadTask) {
  return task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled' || task.status === 'paused'
}

function buildDecryptRetryPayload(task: DownloadTask): Record<string, unknown> | null {
  const params = task.params ?? {}
  const inputPath = typeof params.input_path === 'string' ? params.input_path : ''
  if (!inputPath) return null
  return {
    input_type: typeof params.input_type === 'string' ? params.input_type : '单文件',
    input_path: inputPath,
    output_dir: typeof params.output_dir === 'string' ? params.output_dir : '',
    remove_source: typeof params.remove_source === 'boolean' ? params.remove_source : false,
    add_to_assets: typeof params.add_to_assets === 'boolean' ? params.add_to_assets : false,
  }
}

export function DashboardApp() {
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [modules, setModules] = useState<AnyRecord[]>([])
  const [workspace, setWorkspaceState] = useState<AnyRecord | null>(null)

  async function refresh() {
    const [statusData, moduleData, workspaceData] = await Promise.all([getSystemStatus(), getModules(), getWorkspace()])
    setStatus(statusData)
    setModules(moduleData.modules || moduleData.items || [])
    setWorkspaceState(workspaceData)
  }

  useEffect(() => { void refresh() }, [])

  return (
    <AppLayout>
      <div className="tool-app">
        <section className="tool-hero">
          <div>
            <div className="tool-eyebrow">MediaTools Console</div>
            <h2>控制台</h2>
            <p>集中查看后端、模块和当前工作区状态，确认自动化链路是否可用。</p>
          </div>
          <div className={`tool-ready ${status?.ok === false ? 'tool-ready--warn' : 'tool-ready--online'}`}>
            <span>{status?.ok === false ? '异常' : '在线'}</span>
            <small>{workspace?.project_root || '默认工作区'}</small>
          </div>
        </section>
        <div className="tool-metrics">
          <div className="tool-metric"><span>后端状态</span><strong>{status?.ok === false ? '异常' : '在线'}</strong></div>
          <div className="tool-metric"><span>模块数量</span><strong>{modules.length || 0}</strong></div>
          <div className="tool-metric"><span>工作区</span><strong>{workspace?.project_root ? '已设置' : '默认'}</strong></div>
          <div className="tool-metric"><span>任务中心</span><strong>已连接</strong></div>
        </div>
        <section className="tool-panel">
          <div className="tool-section-head">
            <div>
              <h3>模块状态</h3>
              <p>按服务能力列出当前可用模块。</p>
            </div>
            <ToolbarButton onClick={() => void refresh()}>刷新</ToolbarButton>
          </div>
          <div className="tool-module-grid">
            {modules.map((item) => (
              <div className="tool-module" key={item.id || item.name}>
                <div><strong>{item.name || item.id}</strong><span>{item.desc || '-'}</span></div>
                <em>{item.status || (item.dep_ok ? 'online' : 'offline')}</em>
              </div>
            ))}
          </div>
        </section>
        <section className="tool-panel">
          <div className="tool-section-head"><h3>工作区详情</h3></div>
          <ResultBox value={workspace || '正在读取工作区'} />
        </section>
      </div>
    </AppLayout>
  )
}

export function EncoderApp() {
  const [inputPath, setInputPath] = useState('')
  const [outputPath, setOutputPath] = useState('')
  const [codec, setCodec] = useState('H.264 (AVC)')
  const [crf, setCrf] = useState(23)
  const [preset, setPreset] = useState('medium')
  const [result, setResult] = useState<unknown>('等待转码')

  async function submit() {
    setResult('正在提交转码任务...')
    try {
      setResult(await runEncoder({ input_path: inputPath, output_path: outputPath || undefined, codec, crf, preset }))
    } catch (err: any) {
      setResult(err?.message || '转码失败')
    }
  }

  return (
    <AppLayout>
      <div className="tool-app">
        <section className="tool-hero">
          <div>
            <div className="tool-eyebrow">Video Encoder</div>
            <h2>视频转码</h2>
            <p>为剪辑、上传和归档生成稳定的 H.264/H.265 输出，并进入任务中心跟踪进度。</p>
          </div>
          <div className="tool-ready"><span>{codec.includes('265') ? 'HEVC' : 'AVC'}</span><small>CRF {crf} / {preset}</small></div>
        </section>
        <div className="tool-workspace">
          <section className="tool-panel">
            <div className="tool-section-head"><div><h3>转码参数</h3><p>输出路径留空时由后端生成默认文件。</p></div></div>
            <Field label="输入文件"><PathInput value={inputPath} onChange={setInputPath} mode="file" /></Field>
            <Field label="输出文件"><PathInput value={outputPath} onChange={setOutputPath} mode="any" /></Field>
            <div className="tool-form-grid">
              <Field label="编码"><select value={codec} onChange={(event) => setCodec(event.target.value)}><option>H.264 (AVC)</option><option>H.265 (HEVC)</option><option value="Audio Only">Audio Only</option></select></Field>
              <Field label="CRF"><input type="number" min={0} max={51} value={crf} onChange={(event) => setCrf(Number(event.target.value))} /></Field>
              <Field label="预设"><select value={preset} onChange={(event) => setPreset(event.target.value)}><option>slow</option><option>medium</option><option>fast</option><option>veryfast</option></select></Field>
            </div>
            <PrimaryButton onClick={submit} disabled={!inputPath}>开始转码</PrimaryButton>
          </section>
          <section className="tool-panel">
            <div className="tool-section-head"><h3>任务回执</h3></div>
            <ResultBox value={result} />
          </section>
        </div>
      </div>
    </AppLayout>
  )
}

export function DecryptorApp() {
  const [inputType, setInputType] = useState('单文件')
  const [inputPath, setInputPath] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [result, setResult] = useState<unknown>('等待提交')
  const [activeTasks, setActiveTasks] = useState<DownloadTask[]>([])
  const [historyTasks, setHistoryTasks] = useState<DownloadTask[]>([])
  const [selectedCategory, setSelectedCategory] = useState<DecryptCategory>('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const isBatchMode = inputType === '文件夹批量'

  const refreshDecryptTasks = useCallback(async () => {
    const [activeRes, historyRes] = await Promise.all([getActiveTasks(), getWeeklyHistory()])
    const running = ((activeRes.tasks || []) as DownloadTask[]).filter(isDecryptTask).sort((a, b) => b.created_at - a.created_at)
    const history = ((historyRes.tasks || []) as DownloadTask[]).filter(isDecryptTask).sort((a, b) => b.created_at - a.created_at)
    setActiveTasks(running)
    setHistoryTasks(history)
  }, [])

  useEffect(() => {
    void refreshDecryptTasks()
    const timer = window.setInterval(() => {
      void refreshDecryptTasks()
    }, 2500)
    return () => window.clearInterval(timer)
  }, [refreshDecryptTasks])

  const allTasks = useMemo(() => mergeTasks(activeTasks, historyTasks), [activeTasks, historyTasks])
  const stats = useMemo(() => {
    const next: Record<DecryptCategory, number> = { all: allTasks.length, running: 0, completed: 0, pending: 0, stopped: 0, error: 0 }
    allTasks.forEach((task) => {
      next[getDecryptCategory(task)] += 1
    })
    return next
  }, [allTasks])
  const selectedTasks = useMemo(() => allTasks.filter((task) => selectedIds.has(task.id)), [allTasks, selectedIds])
  const filteredTasks = useMemo(() => {
    const keyword = searchText.trim().toLowerCase()
    return allTasks.filter((task) => {
      if (selectedCategory !== 'all' && getDecryptCategory(task) !== selectedCategory) return false
      if (!keyword) return true
      return [task.name, task.stage, task.status].some((value) => String(value || '').toLowerCase().includes(keyword))
    })
  }, [allTasks, searchText, selectedCategory])
  const cancellableSelected = selectedTasks.filter(isDecryptCancellable)
  const retryableSelected = selectedTasks.filter((task) => buildDecryptRetryPayload(task))
  const clearableSelected = selectedTasks.filter(isDecryptClearable)
  const clearableTasks = allTasks.filter(isDecryptClearable)
  const allVisibleSelected = filteredTasks.length > 0 && filteredTasks.every((task) => selectedIds.has(task.id))

  function selectInputType(nextType: string) {
    if (nextType === inputType) return
    setInputType(nextType)
    setInputPath('')
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleSelectAllVisible() {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (allVisibleSelected) filteredTasks.forEach((task) => next.delete(task.id))
      else filteredTasks.forEach((task) => next.add(task.id))
      return next
    })
  }

  async function submit() {
    const nextInputPath = inputPath.trim()
    if (!nextInputPath) return
    setResult('正在提交解密任务...')
    try {
      setResult(await runDecryptor({ input_type: inputType, input_path: nextInputPath, output_dir: outputDir.trim() || undefined, remove_source: false, add_to_assets: false }))
      setShowAddForm(false)
      await refreshDecryptTasks()
    } catch (err: any) {
      setResult(err?.message || '解密失败')
    }
  }

  async function stopSelected() {
    const targets = cancellableSelected
    if (!targets.length) return
    await Promise.allSettled(targets.map((task) => cancelTask(task.id)))
    setSelectedIds(new Set())
    await refreshDecryptTasks()
  }

  async function startSelected() {
    const payloads = retryableSelected.map(buildDecryptRetryPayload).filter(Boolean) as Record<string, unknown>[]
    if (!payloads.length) return
    setResult('正在重新提交选中任务...')
    const results = await Promise.allSettled(payloads.map((payload) => runDecryptor(payload)))
    const failed = results.find((item) => item.status === 'rejected') as PromiseRejectedResult | undefined
    setResult(failed ? failed.reason?.message || '重新提交失败' : '已重新提交选中任务')
    setSelectedIds(new Set())
    await refreshDecryptTasks()
  }

  async function clearRecords() {
    const targets = (clearableSelected.length ? clearableSelected : clearableTasks).map((task) => task.id)
    if (!targets.length) return
    await clearTaskRecords({ ids: targets, terminal_only: true })
    setSelectedIds(new Set())
    setSelectedTaskId(null)
    await refreshDecryptTasks()
  }

  return (
    <AppLayout>
      <div className="decryptor-app dl-app">
        <aside className="dl-sidebar decryptor-sidebar">
          <nav className="dl-nav">
            {DECRYPT_CATEGORIES.map((item) => (
              <button
                key={item.key}
                type="button"
                className={selectedCategory === item.key ? 'dl-nav-item dl-nav-item--active' : 'dl-nav-item'}
                onClick={() => setSelectedCategory(item.key)}
              >
                <CategoryIcon name={item.icon} />
                <span>{item.label}</span>
                <small>{stats[item.key]}</small>
              </button>
            ))}
          </nav>
        </aside>
        <main className={`dl-panel decryptor-panel ${showAddForm ? 'decryptor-panel--with-form' : ''}`}>
          <div className="dl-toolbar">
            <button className="dl-btn dl-btn--primary" type="button" onClick={() => setShowAddForm((value) => !value)}>
              <PlusIcon />
              {showAddForm ? '收起表单' : '添加任务'}
            </button>
            <button className="dl-btn" type="button" disabled={!retryableSelected.length} onClick={startSelected}>
              <RetryIcon />
              启动
            </button>
            <button className="dl-btn" type="button" disabled={!cancellableSelected.length} onClick={stopSelected}>
              <StopIcon />
              停止
            </button>
            <button className="dl-btn" type="button" disabled={filteredTasks.length === 0} onClick={toggleSelectAllVisible}>
              <SelectAllIcon />
              {allVisibleSelected ? '取消' : '全选'}
            </button>
            <button className="dl-btn" type="button" disabled={clearableSelected.length === 0 && clearableTasks.length === 0} onClick={clearRecords}>
              <DeleteIcon />
              {clearableSelected.length ? '清除所选' : '清除记录'}
            </button>
            <div className="dl-toolbar-spacer" />
            <div className="dl-search">
              <SearchIcon />
              <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="搜索任务名称" />
            </div>
          </div>

          <div className="dl-stage decryptor-stage">
            {showAddForm && (
              <section className="tool-panel decryptor-form">
                <div className="tool-section-head">
                  <div>
                    <h3>解密设置</h3>
                    <p>{isBatchMode ? '选择输入文件夹，系统会扫描其中可处理的加密音频。' : '选择加密音频文件；输出目录可留空，将保存到与源文件相同的文件夹。'}</p>
                  </div>
                </div>

                <Field label="输入类型">
                  <div className="tool-segmented" role="group" aria-label="输入类型">
                    {['单文件', '文件夹批量'].map((item) => (
                      <button
                        key={item}
                        type="button"
                        className={inputType === item ? 'tool-segmented-item tool-segmented-item--active' : 'tool-segmented-item'}
                        onClick={() => selectInputType(item)}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </Field>

                <div className="tool-mode-fields">
                  <Field label={isBatchMode ? '输入文件夹' : '输入文件'}>
                    <PathInput
                      key={inputType}
                      value={inputPath}
                      onChange={setInputPath}
                      mode={isBatchMode ? 'directory' : 'file'}
                      placeholder={isBatchMode ? '选择包含加密音频的文件夹' : '选择需要解密的音频文件'}
                    />
                  </Field>
                  <Field label={isBatchMode ? '输出文件夹' : '输出文件夹（可选）'}>
                    <PathInput
                      value={outputDir}
                      onChange={setOutputDir}
                      mode="directory"
                      placeholder={isBatchMode ? '选择批量解密输出目录，留空则输出到输入文件夹内' : '留空时输出到源文件所在目录'}
                    />
                  </Field>
                </div>

                <div className="decryptor-form-actions">
                  <PrimaryButton onClick={submit} disabled={!inputPath.trim()}>开始解密</PrimaryButton>
                  <ToolbarButton type="button" onClick={() => setShowAddForm(false)}>取消</ToolbarButton>
                </div>
              </section>
            )}

            <div className="dl-body">
              <div className="dl-content">
                <section className="dl-table decryptor-table">
                  <div className="dl-head">
                    <span className="dl-col-status" />
                    <span className="dl-col-name">任务名称</span>
                    <span className="dl-col-progress">进度</span>
                    <span className="dl-col-time">时间</span>
                  </div>
                  <div className="dl-list">
                    {filteredTasks.length === 0 && (
                      <div className="dl-empty">
                        <p>暂无解密任务</p>
                        <small>点击“添加任务”提交单文件或文件夹批量解密。</small>
                      </div>
                    )}
                    {filteredTasks.map((task) => (
                      <div
                        key={task.id}
                        className={`dl-row ${selectedIds.has(task.id) ? 'dl-row--selected' : ''} ${selectedTaskId === task.id ? 'dl-row--focused' : ''}`}
                        onClick={() => setSelectedTaskId(task.id)}
                      >
                        <span className="dl-col-status">
                          <input
                            type="checkbox"
                            aria-label={`select-decrypt-task-${task.id}`}
                            checked={selectedIds.has(task.id)}
                            onChange={() => toggleSelect(task.id)}
                            onClick={(event) => event.stopPropagation()}
                          />
                          <StatusIcon status={task.status} />
                        </span>
                        <span className="dl-col-name">
                          <strong>{task.name || '音频解密任务'}</strong>
                          <small>{task.stage || task.status}</small>
                        </span>
                        <span className="dl-col-progress">
                          <div className="dl-progress-bar">
                            <div className="dl-progress-fill" style={{ width: `${Math.min(100, Math.max(0, task.progress || 0))}%` }} />
                          </div>
                          <span className="dl-progress-text">{(task.progress || 0).toFixed(0)}%</span>
                        </span>
                        <span className="dl-col-time">{formatRelativeTime(task.created_at)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="decryptor-receipt">
                    <ResultBox value={result} />
                  </div>
                </section>
              </div>
            </div>
          </div>
        </main>
      </div>
    </AppLayout>
  )
}

export function AssetsApp() {
  const [directory, setDirectory] = useState('')
  const [keyword, setKeyword] = useState('')
  const [assetType, setAssetType] = useState('')
  const [result, setResult] = useState<AnyRecord>({ items: [] })
  const items: AnyRecord[] = result.items || []

  async function scan() {
    try {
      setResult(await fetchAssets({ directory, keyword, asset_type: assetType }))
    } catch (err: any) {
      setResult({ items: [], error: err?.message || '扫描失败' })
    }
  }

  useEffect(() => { void scan() }, [])

  return (
    <AppLayout>
      <div className="tool-app">
        <section className="tool-hero">
          <div>
            <div className="tool-eyebrow">Asset Library</div>
            <h2>素材库</h2>
            <p>扫描工作区或指定目录，按类型和关键词筛选视频、音频、图片和字幕素材。</p>
          </div>
          <div className="tool-ready"><span>{items.length}</span><small>当前结果</small></div>
        </section>
        <section className="tool-panel">
          <div className="tool-section-head">
            <div><h3>扫描筛选</h3><p>留空目录时使用当前工作区。</p></div>
          </div>
          <div className="tool-filter-grid">
            <Field label="扫描目录"><PathInput value={directory} onChange={setDirectory} mode="directory" placeholder="留空则使用当前工作区" /></Field>
            <Field label="关键词"><input value={keyword} onChange={(event) => setKeyword(event.target.value)} /></Field>
            <Field label="类型"><select value={assetType} onChange={(event) => setAssetType(event.target.value)}><option value="">全部</option><option value="video">视频</option><option value="audio">音频</option><option value="image">图片</option><option value="subtitle">字幕</option></select></Field>
          </div>
          <PrimaryButton onClick={scan}>扫描素材</PrimaryButton>
        </section>
        <section className="tool-panel">
          <div className="tool-section-head"><div><h3>扫描结果</h3><p>{result.error || `显示前 ${Math.min(items.length, 80)} 项`}</p></div></div>
          <div className="tool-asset-list">
            {items.slice(0, 80).map((item: AnyRecord) => (
              <div className="tool-asset-row" key={item.path || item.name}>
                <strong>{item.name}</strong><span>{item.type || '-'} · {item.size_mb ?? item.size ?? 0} {item.size_mb !== undefined ? 'MB' : 'bytes'}</span><em>{item.directory || item.path}</em>
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppLayout>
  )
}

export function WorkspaceApp() {
  const [projectRoot, setProjectRoot] = useState('')
  const [result, setResult] = useState<unknown>('正在读取工作区')

  async function refresh() {
    const data = await getWorkspace()
    setProjectRoot(data.project_root || '')
    setResult(data)
  }

  async function save() {
    setResult(await setWorkspace(projectRoot))
  }

  useEffect(() => { void refresh() }, [])

  return (
    <AppLayout>
      <div className="tool-app">
        <section className="tool-hero">
          <div>
            <div className="tool-eyebrow">Workspace</div>
            <h2>工作区设置</h2>
            <p>切换 MediaTools 项目根目录，下载、分析、导出和日志都会按工作区隔离。</p>
          </div>
          <div className="tool-ready"><span>Workspace</span><small>{projectRoot || '默认工作区'}</small></div>
        </section>
        <div className="tool-workspace">
          <section className="tool-panel">
            <div className="tool-section-head"><div><h3>项目根目录</h3><p>建议选择专门的 MediaTools 项目目录。</p></div></div>
            <Field label="项目根目录"><PathInput value={projectRoot} onChange={setProjectRoot} mode="directory" /></Field>
            <div className="tool-actions">
              <PrimaryButton onClick={save} disabled={!projectRoot}>切换工作区</PrimaryButton>
              <ToolbarButton onClick={() => void refresh()}>刷新</ToolbarButton>
            </div>
          </section>
          <section className="tool-panel">
            <div className="tool-section-head"><h3>当前配置</h3></div>
            <ResultBox value={result} />
          </section>
        </div>
      </div>
    </AppLayout>
  )
}

export { PhotoshopApp } from './PhotoshopApp'

export { WorkbenchApp } from './WorkbenchApp'

export { AuditorApp } from './AuditorApp'

export { AEApp } from './AEApp'

export { FileManagerApp } from './FileManagerApp'

export { AgentApp } from './AIAssistantApp'

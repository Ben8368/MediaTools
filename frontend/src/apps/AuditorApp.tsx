import { useEffect, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  fetchAuditorConfig,
  fetchAuditorStatus,
  runAuditorOnce,
  updateAuditorConfig,
} from '@/api'
import {
  Field,
  PathInput,
  PrimaryButton,
  ResultBox,
  ToolbarButton,
} from '@/apps/mediatools/primitives'
import type { AnyRecord } from '@/types'

export function AuditorApp() {
  const [status, setStatus] = useState<AnyRecord | null>(null)
  const [config, setConfig] = useState<AnyRecord>({})
  const [folderText, setFolderText] = useState('')
  const [newFolder, setNewFolder] = useState('')
  const [result, setResult] = useState<unknown>('等待扫描')

  const folders = folderText.split('\n').map((item) => item.trim()).filter(Boolean)

  async function refresh() {
    const [statusData, configData] = await Promise.all([fetchAuditorStatus(), fetchAuditorConfig()])
    const nextConfig = configData.config || {}
    setStatus(statusData)
    setConfig(nextConfig)
    setFolderText((nextConfig.watch_folders || []).join('\n'))
  }

  async function save() {
    const nextConfig = { ...config, watch_folders: folders, enabled: Boolean(config.enabled) }
    const data = await updateAuditorConfig(nextConfig)
    setConfig(data.config || nextConfig)
    setResult(data)
  }

  async function runOnce() {
    setResult(await runAuditorOnce())
  }

  function addFolder() {
    const value = newFolder.trim()
    if (!value) return
    setFolderText((current) => [...current.split('\n').map((item) => item.trim()).filter(Boolean), value].join('\n'))
    setNewFolder('')
  }

  useEffect(() => { void refresh() }, [])

  return (
    <AppLayout>
      <div className="au-app">
        <section className="au-hero">
          <div>
            <div className="au-eyebrow">Asset Auditor</div>
            <h2>素材审核</h2>
            <p>配置监控目录，执行一次性扫描，生成工作区审核清单与运行快照。</p>
          </div>
          <div className={`au-ready ${status?.available ? 'au-ready--online' : 'au-ready--offline'}`}>
            <span>{status?.available ? '可用' : '未就绪'}</span>
            <small>{status?.module_status || status?.integration_mode || 'service_module'}</small>
          </div>
        </section>

        <div className="au-metrics">
          <div className="au-metric"><span>监控目录</span><strong>{folders.length}</strong></div>
          <div className="au-metric"><span>状态</span><strong>{config.enabled ? '启用' : '停用'}</strong></div>
          <div className="au-metric"><span>输出</span><strong>{config.output_backend || 'local'}</strong></div>
          <div className="au-metric"><span>模型</span><strong>{config.model || '-'}</strong></div>
        </div>

        <div className="au-workspace">
          <section className="au-panel">
            <div className="au-section-head">
              <div>
                <h3>审核配置</h3>
                <p>每行一个目录，扫描结果会写入当前工作区。</p>
              </div>
              <ToolbarButton onClick={() => void refresh()}>刷新</ToolbarButton>
            </div>
            <div className="au-inline">
              <Field label="添加目录"><PathInput value={newFolder} onChange={setNewFolder} mode="directory" /></Field>
              <ToolbarButton onClick={addFolder}>加入列表</ToolbarButton>
            </div>
            <Field label="监控目录">
              <textarea value={folderText} onChange={(event) => setFolderText(event.target.value)} placeholder="每行一个需要审核的目录" />
            </Field>
            <div className="au-form-grid">
              <Field label="输出方式"><input value={config.output_backend || 'local'} onChange={(event) => setConfig((current) => ({ ...current, output_backend: event.target.value }))} /></Field>
              <Field label="工作簿名"><input value={config.local_workbook_name || 'auditor.xlsx'} onChange={(event) => setConfig((current) => ({ ...current, local_workbook_name: event.target.value }))} /></Field>
              <Field label="模型"><input value={config.model || ''} onChange={(event) => setConfig((current) => ({ ...current, model: event.target.value }))} placeholder="留空使用默认模型" /></Field>
            </div>
            <label className="au-check"><input type="checkbox" checked={Boolean(config.enabled)} onChange={(event) => setConfig((current) => ({ ...current, enabled: event.target.checked }))} /> 启用审核配置</label>
            <div className="au-actions">
              <PrimaryButton onClick={save}>保存配置</PrimaryButton>
              <ToolbarButton onClick={runOnce}>执行一次扫描</ToolbarButton>
            </div>
          </section>

          <section className="au-panel">
            <div className="au-section-head">
              <div>
                <h3>运行位置</h3>
                <p>这些路径由后端按当前工作区生成。</p>
              </div>
            </div>
            <div className="au-path-list">
              <div><span>配置</span><strong>{status?.config_path || '-'}</strong></div>
              <div><span>清单</span><strong>{status?.last_scan_path || '-'}</strong></div>
              <div><span>日志</span><strong>{status?.logs_dir || '-'}</strong></div>
              <div><span>工作簿</span><strong>{status?.workbook_path || '-'}</strong></div>
            </div>
            <ResultBox value={result} />
          </section>
        </div>
      </div>
    </AppLayout>
  )
}

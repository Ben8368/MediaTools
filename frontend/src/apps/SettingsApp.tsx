import { useState } from 'react'

import { AppLayout } from '@/AppLayout'
import { testAgentConnection } from '@/api'
import { Field, PrimaryButton, ToolbarButton } from '@/apps/mediatools/primitives'
import { useModelConfig } from '@/modelConfigStore'

type TestResult = { ok: boolean; message: string } | null

export function SettingsApp() {
  const { config, setConfig } = useModelConfig()
  const [baseUrl, setBaseUrl] = useState(config.baseUrl)
  const [model, setModel] = useState(config.model)
  const [apiKey, setApiKey] = useState(config.apiKey)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult>(null)

  const dirty = baseUrl !== config.baseUrl || model !== config.model || apiKey !== config.apiKey

  function save() {
    setConfig({ baseUrl, model, apiKey })
    setTestResult(null)
  }

  function reset() {
    setBaseUrl(config.baseUrl)
    setModel(config.model)
    setApiKey(config.apiKey)
    setTestResult(null)
  }

  async function testConnection() {
    if (testing) return
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testAgentConnection({
        base_url: baseUrl || undefined,
        model: model || undefined,
        api_key: apiKey || undefined,
      })
      setTestResult({ ok: Boolean(result?.ok), message: result?.message || (result?.ok ? '连接成功' : '连接失败') })
    } catch (err: any) {
      setTestResult({ ok: false, message: err?.message || '请求失败' })
    } finally {
      setTesting(false)
    }
  }

  return (
    <AppLayout>
      <div className="settings-app">
        <aside className="settings-sidebar">
          <nav className="settings-nav">
            <button className="settings-nav-item settings-nav-item--active">
              <SettingsIcon />
              <span>模型配置</span>
            </button>
          </nav>
        </aside>

        <main className="settings-panel">
          <div className="settings-toolbar">
            <div>
              <h2>AI 模型配置</h2>
              <p>覆盖后端默认的 LLM 接入参数。留空时使用服务端配置。</p>
            </div>
            <div className="settings-badge">
              <span>临时配置</span>
              <small>刷新后失效</small>
            </div>
          </div>

          <div className="settings-content">
            <section className="settings-card">
              <div className="settings-section-head">
                <h3>连接参数</h3>
                <p>这些参数会自动带入 AI 助手和 Agent 请求。</p>
              </div>
              <Field label="Base URL">
                <input
                  type="url"
                  value={baseUrl}
                  onChange={(event) => setBaseUrl(event.target.value)}
                  placeholder="https://api.openai.com/v1"
                />
              </Field>
              <Field label="模型">
                <input
                  type="text"
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                  placeholder="gpt-4o"
                />
              </Field>
              <Field label="API Key">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="sk-..."
                  autoComplete="off"
                />
              </Field>
              <div className="settings-actions">
                <PrimaryButton onClick={save} disabled={!dirty}>保存到会话</PrimaryButton>
                <ToolbarButton onClick={reset} disabled={!dirty}>撤销</ToolbarButton>
                <ToolbarButton onClick={() => void testConnection()} disabled={testing}>
                  {testing ? '测试中...' : '测试连接'}
                </ToolbarButton>
              </div>
              {testResult && (
                <div className={`settings-result ${testResult.ok ? 'settings-result--ok' : 'settings-result--error'}`}>
                  {testResult.message}
                </div>
              )}
            </section>

            <section className="settings-card settings-card--summary">
              <div className="settings-section-head">
                <h3>当前生效配置</h3>
                <p>保存后立即作用于当前前端会话。</p>
              </div>
              <ConfigRow label="Base URL" value={config.baseUrl || '使用服务端默认'} />
              <ConfigRow label="模型" value={config.model || '使用服务端默认'} />
              <ConfigRow label="API Key" value={config.apiKey ? `••••••••${config.apiKey.slice(-4)}` : '使用服务端默认'} />
            </section>
          </div>
        </main>
      </div>
    </AppLayout>
  )
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="settings-config-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

const SettingsIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
    <path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 01-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 01-4 0v-.1a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 01-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 010-4h.1a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 012.8-2.8l.1.1a1.7 1.7 0 001.8.3 1.7 1.7 0 001-1.5V3a2 2 0 014 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 012.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8 1.7 1.7 0 001.5 1h.1a2 2 0 010 4h-.1a1.7 1.7 0 00-1.5 1z" />
  </svg>
)

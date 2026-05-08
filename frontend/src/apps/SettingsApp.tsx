import { useEffect, useRef, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import { runAgent, testAgentConnection } from '@/api'
import { Field, PrimaryButton, ToolbarButton } from '@/apps/mediatools/primitives'
import { useModelConfig } from '@/modelConfigStore'

type TestResult = { ok: boolean; message: string } | null

type ProbeMessage = { id: string; role: 'user' | 'assistant'; content: string }

const PROBE_INTRO_MESSAGE: ProbeMessage = {
  id: 'settings-probe-intro',
  role: 'assistant',
  content:
    '在此处发送一条消息，将使用上方表单里的 Base URL、模型与 API Key 调用 Agent（无需先保存）。适合快速确认模型能否正常回复。',
}

export function SettingsApp() {
  const { config, hasSavedConfig, isLoading, saveConfig, clearSavedConfig, loadConfig } = useModelConfig()
  const [baseUrl, setBaseUrl] = useState(config.baseUrl)
  const [model, setModel] = useState(config.model)
  const [apiKey, setApiKey] = useState(config.apiKey)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [testResult, setTestResult] = useState<TestResult>(null)
  const [probeMessages, setProbeMessages] = useState<ProbeMessage[]>([PROBE_INTRO_MESSAGE])
  const [probeDraft, setProbeDraft] = useState('')
  const [probeSending, setProbeSending] = useState(false)
  const probeListRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  useEffect(() => {
    setBaseUrl(config.baseUrl)
    setModel(config.model)
    setApiKey(config.apiKey)
  }, [config])

  const dirty = baseUrl !== config.baseUrl || model !== config.model || apiKey !== config.apiKey

  async function save() {
    if (saving) return
    setTestResult(null)
    setSaving(true)
    try {
      await saveConfig({
        baseUrl: baseUrl.trim(),
        model: model.trim(),
        apiKey: apiKey.trim(),
      })
      setTestResult({ ok: true, message: '配置已保存' })
    } catch (err: any) {
      setTestResult({ ok: false, message: err?.message || '保存失败' })
    } finally {
      setSaving(false)
    }
  }

  async function clearSaved() {
    if (clearing) return
    setTestResult(null)
    setClearing(true)
    try {
      await clearSavedConfig()
      setTestResult({ ok: true, message: '配置已清除' })
    } catch (err: any) {
      setTestResult({ ok: false, message: err?.message || '清除失败' })
    } finally {
      setClearing(false)
    }
  }

  const canClearSaved = hasSavedConfig || dirty || Boolean(config.baseUrl || config.model || config.apiKey)

  useEffect(() => {
    const el = probeListRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [probeMessages, probeSending])

  function clearProbeConversation() {
    setProbeMessages([PROBE_INTRO_MESSAGE])
    setProbeDraft('')
  }

  async function sendProbeMessage() {
    const task = probeDraft.trim()
    if (!task || probeSending || isLoading) return

    const userMessage: ProbeMessage = { id: crypto.randomUUID(), role: 'user', content: task }
    setProbeDraft('')
    setProbeSending(true)
    setProbeMessages((items) => [...items, userMessage])

    try {
      const payload: Record<string, unknown> = { task }
      const u = baseUrl.trim()
      const m = model.trim()
      const k = apiKey.trim()
      if (u) payload.base_url = u
      if (m) payload.model = m
      if (k) payload.api_key = k

      const result = await runAgent(payload)
      const answer =
        result?.answer || result?.message || result?.summary || JSON.stringify(result, null, 2)
      setProbeMessages((items) => [
        ...items,
        { id: crypto.randomUUID(), role: 'assistant', content: String(answer) },
      ])
    } catch (err: any) {
      setProbeMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: err?.message || 'Agent 请求失败',
        },
      ])
    } finally {
      setProbeSending(false)
    }
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

  const badgeSubtitleDefault = isLoading
    ? '正在从服务器加载配置'
    : hasSavedConfig
      ? '已持久化到服务器'
      : '未保存自定义模型'

  useEffect(() => {
    if (!testResult) return
    const ms = testResult.ok ? 3200 : 9000
    const id = window.setTimeout(() => setTestResult(null), ms)
    return () => window.clearTimeout(id)
  }, [testResult])

  const badgeSubtitle = testResult?.message ?? badgeSubtitleDefault
  const badgeModifier = testResult ? (testResult.ok ? 'settings-badge--notice-ok' : 'settings-badge--notice-error') : ''

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
            <div className={['settings-badge', badgeModifier].filter(Boolean).join(' ')}>
              <span>{isLoading ? '加载中...' : hasSavedConfig ? '已保存配置' : '服务端默认'}</span>
              <small>{badgeSubtitle}</small>
            </div>
          </div>

          <div className="settings-content">
            <section className="settings-card">
              <div className="settings-section-head settings-section-head--with-model">
                <div className="settings-section-head__copy">
                  <h3>连接参数</h3>
                  <p>这些参数会自动带入 AI 助手和 Agent 请求，保存后持久存储于服务器。</p>
                </div>
                <div className="settings-section-head__model">
                  <input
                    type="text"
                    aria-label="模型"
                    value={model}
                    onChange={(event) => setModel(event.target.value)}
                    placeholder="模型，例如 gpt-4o"
                    disabled={isLoading}
                  />
                </div>
              </div>
              <div className="settings-fields-inline">
                <Field label="Base URL">
                  <input
                    type="url"
                    value={baseUrl}
                    onChange={(event) => setBaseUrl(event.target.value)}
                    placeholder="https://api.openai.com/v1"
                    disabled={isLoading}
                  />
                </Field>
                <Field label="API Key">
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(event) => setApiKey(event.target.value)}
                    placeholder="sk-..."
                    autoComplete="off"
                    disabled={isLoading}
                  />
                </Field>
              </div>
              <div className="settings-actions">
                <PrimaryButton onClick={save} disabled={!dirty || saving}>
                  {saving ? '保存中...' : '保存'}
                </PrimaryButton>
                <ToolbarButton onClick={clearSaved} disabled={!canClearSaved || clearing}>
                  {clearing ? '清除中...' : '清除保存'}
                </ToolbarButton>
                <ToolbarButton onClick={() => void testConnection()} disabled={testing}>
                  {testing ? '测试中...' : '测试连接'}
                </ToolbarButton>
              </div>
            </section>

            <section className="settings-card settings-chat-probe" aria-label="对话验证">
              <header className="settings-chat-probe__header">
                <h3>对话验证</h3>
                <p>临时会话，仅用于在当前页面快速试一句；不会写入 AI 助手侧边栏的历史会话。</p>
              </header>

              <div className="settings-chat-probe__panel">
                <div ref={probeListRef} className="settings-chat-probe__thread">
                  {probeMessages.map((message) => (
                    <article key={message.id} className={`ai-message ai-message--${message.role}`}>
                      <span>{message.role === 'user' ? '你' : 'AI'}</span>
                      <p>{message.content}</p>
                    </article>
                  ))}
                  {probeSending && (
                    <article className="ai-message ai-message--assistant settings-chat-probe__typing">
                      <span>AI</span>
                      <p>正在调用 Agent...</p>
                    </article>
                  )}
                </div>

                <div className="settings-chat-probe__composer">
                  <div className="settings-chat-probe__composer-shell">
                    <textarea
                      className="settings-chat-probe__input"
                      value={probeDraft}
                      onChange={(event) => setProbeDraft(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) void sendProbeMessage()
                      }}
                      placeholder="输入一句话试试模型回复…"
                      disabled={isLoading || probeSending}
                      rows={2}
                    />
                    <div className="settings-chat-probe__composer-foot">
                      <span className="settings-chat-probe__hint">Ctrl+Enter 发送</span>
                      <div className="settings-chat-probe__actions">
                        <ToolbarButton type="button" onClick={clearProbeConversation} disabled={probeSending}>
                          清空对话
                        </ToolbarButton>
                        <PrimaryButton
                          type="button"
                          onClick={() => void sendProbeMessage()}
                          disabled={!probeDraft.trim() || probeSending || isLoading}
                        >
                          {probeSending ? '发送中...' : '发送'}
                        </PrimaryButton>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </AppLayout>
  )
}

const SettingsIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
    <path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 01-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 01-4 0v-.1a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 01-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 010-4h.1a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 012.8-2.8l.1.1a1.7 1.7 0 001.8.3 1.7 1.7 0 001-1.5V3a2 2 0 014 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 012.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8 1.7 1.7 0 001.5 1h.1a2 2 0 010 4h-.1a1.7 1.7 0 00-1.5 1z" />
  </svg>
)

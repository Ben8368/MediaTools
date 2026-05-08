import { useCallback, useEffect, useRef, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import { runAgent, testAgentConnection } from '@/api'
import { Field, PrimaryButton } from '@/apps/mediatools/primitives'
import { useModelConfig } from '@/modelConfigStore'

type TestResult = { ok: boolean; message: string } | null

type ProbeMessage = { id: string; role: 'user' | 'assistant'; content: string }

function trimCfg(c: { baseUrl: string; model: string; apiKey: string }) {
  return {
    baseUrl: c.baseUrl.trim(),
    model: c.model.trim(),
    apiKey: c.apiKey.trim(),
  }
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
  const [probeMessages, setProbeMessages] = useState<ProbeMessage[]>([])
  const [probeDraft, setProbeDraft] = useState('')
  const [probeSending, setProbeSending] = useState(false)
  const probeListRef = useRef<HTMLDivElement>(null)

  const persistFromForm = useCallback(async () => {
    setSaving(true)
    setTestResult(null)
    try {
      await saveConfig(trimCfg({ baseUrl, model, apiKey }))
      setTestResult({ ok: true, message: '已保存' })
    } catch (err: any) {
      setTestResult({ ok: false, message: err?.message || '保存失败' })
    } finally {
      setSaving(false)
    }
  }, [apiKey, baseUrl, model, saveConfig])

  useEffect(() => {
    loadConfig()
  }, [])

  useEffect(() => {
    setBaseUrl(config.baseUrl)
    setModel(config.model)
    setApiKey(config.apiKey)
  }, [config])

  useEffect(() => {
    if (isLoading) return
    const next = trimCfg({ baseUrl, model, apiKey })
    const cur = trimCfg(config)
    if (next.baseUrl === cur.baseUrl && next.model === cur.model && next.apiKey === cur.apiKey) return

    const id = window.setTimeout(() => {
      void persistFromForm()
    }, 480)
    return () => window.clearTimeout(id)
  }, [apiKey, baseUrl, config, isLoading, model, persistFromForm])

  const trimmedLive = trimCfg({ baseUrl, model, apiKey })
  const canClearSaved =
    hasSavedConfig || Boolean(trimmedLive.baseUrl || trimmedLive.model || trimmedLive.apiKey)

  useEffect(() => {
    const el = probeListRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [probeMessages, probeSending])

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
      const ok = Boolean(result?.ok)
      setTestResult({
        ok,
        message: ok ? '测试通过' : result?.message || '连接失败',
      })
    } catch (err: any) {
      setTestResult({ ok: false, message: err?.message || '请求失败' })
    } finally {
      setTesting(false)
    }
  }

  useEffect(() => {
    if (!testResult) return
    const shortFlash =
      testResult.ok &&
      (testResult.message === '已保存' ||
        testResult.message === '已自动保存' ||
        testResult.message === '测试通过')
    const ms = !testResult.ok ? 9000 : shortFlash ? 2200 : 3200
    const id = window.setTimeout(() => setTestResult(null), ms)
    return () => window.clearTimeout(id)
  }, [testResult])

  const badgeLine = (() => {
    if (testResult) return testResult.message
    if (isLoading) return '正在加载配置…'
    if (testing) return '正在测试连接…'
    if (saving) return '正在保存…'
    return '测试连接'
  })()

  const badgeModifier = testResult ? (testResult.ok ? 'settings-badge--notice-ok' : 'settings-badge--notice-error') : ''

  const badgeHitTitle =
    testResult !== null || saving || testing || isLoading
      ? badgeLine
      : '测试连接 · 使用当前表单中的 Base URL、模型与 API Key'

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
              <p>覆盖后端默认的 LLM 接入参数。留空时使用服务端配置。修改后自动保存。</p>
            </div>
            <div className={['settings-badge settings-badge--interactive', badgeModifier].filter(Boolean).join(' ')}>
              <button
                type="button"
                className="settings-badge__hit"
                onClick={() => void testConnection()}
                disabled={testing || isLoading}
                title={badgeHitTitle}
                aria-label="测试模型连接"
              >
                <span className="settings-badge__line">{badgeLine}</span>
              </button>
            </div>
          </div>

          <div className="settings-content">
            <section className="settings-card">
              <div className="settings-fields-inline settings-fields-inline--triple">
                <Field label="Base URL">
                  <input
                    type="url"
                    value={baseUrl}
                    onChange={(event) => setBaseUrl(event.target.value)}
                    placeholder="https://api.openai.com/v1"
                    disabled={isLoading}
                  />
                </Field>
                <Field label="模型">
                  <input
                    type="text"
                    aria-label="模型"
                    value={model}
                    onChange={(event) => setModel(event.target.value)}
                    placeholder="例如 gpt-4o"
                    disabled={isLoading}
                  />
                </Field>
                <Field label="API Key">
                  <div className="settings-field-with-clear">
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(event) => setApiKey(event.target.value)}
                      placeholder="sk-..."
                      autoComplete="off"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="settings-field-with-clear__btn"
                      onClick={() => void clearSaved()}
                      disabled={!canClearSaved || clearing}
                      aria-label="清除保存"
                      title="清除保存"
                    >
                      ×
                    </button>
                  </div>
                </Field>
              </div>

              <div className="settings-chat-probe" aria-label="对话验证">
                <div className="settings-chat-probe__panel">
                  <div ref={probeListRef} className="settings-chat-probe__thread">
                    {probeMessages.map((message) => (
                      <article key={message.id} className={`ai-message ai-message--${message.role}`}>
                        {message.role === 'assistant' && <span>AI</span>}
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
                      <input
                        type="text"
                        className="settings-chat-probe__input"
                        value={probeDraft}
                        onChange={(event) => setProbeDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key !== 'Enter') return
                          event.preventDefault()
                          void sendProbeMessage()
                        }}
                        placeholder="试一句…"
                        title="Enter 发送"
                        disabled={isLoading || probeSending}
                      />
                      <div className="settings-chat-probe__composer-side">
                        <PrimaryButton
                          type="button"
                          className="settings-chat-probe__send"
                          onClick={() => void sendProbeMessage()}
                          disabled={!probeDraft.trim() || probeSending || isLoading}
                        >
                          {probeSending ? '发送中' : '发送'}
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

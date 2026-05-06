import { useEffect, useMemo, useState } from 'react'

import { runAgent } from '@/api'
import { useModelConfig } from '@/modelConfigStore'

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

type ChatSession = {
  id: string
  title: string
  updatedAt: string
  messages: ChatMessage[]
}

const AI_SESSION_STORAGE_KEY = 'mediatools.ai.sessions'
const AI_ACTIVE_SESSION_STORAGE_KEY = 'mediatools.ai.activeSession'

const nowText = () => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

function makeSession(index = 1): ChatSession {
  const id = crypto.randomUUID()
  return {
    id,
    title: index === 1 ? '新的媒体任务' : `会话 ${index}`,
    updatedAt: nowText(),
    messages: [
      {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '你好，我可以帮你串联下载、转码、字幕分析、素材整理和 Adobe 自动化。描述目标后，我会调用后端 Agent 执行。',
      },
    ],
  }
}

function loadStoredSessions(): ChatSession[] {
  try {
    const raw = window.localStorage.getItem(AI_SESSION_STORAGE_KEY)
    if (!raw) return [makeSession()]
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return [makeSession()]
    const sessions = parsed.filter((session): session is ChatSession => (
      session &&
      typeof session.id === 'string' &&
      typeof session.title === 'string' &&
      typeof session.updatedAt === 'string' &&
      Array.isArray(session.messages)
    ))
    return sessions
  } catch {
    return [makeSession()]
  }
}

export function AgentApp() {
  const { config: modelConfig } = useModelConfig()
  const [sessions, setSessions] = useState<ChatSession[]>(loadStoredSessions)
  const [activeId, setActiveId] = useState(() => {
    const storedActiveId = window.localStorage.getItem(AI_ACTIVE_SESSION_STORAGE_KEY) || ''
    return storedActiveId || ''
  })
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const activeModel = modelConfig.model || '服务端默认'
  const modelMode = modelConfig.baseUrl ? '自定义接入' : '默认接入'

  useEffect(() => {
    if (!sessions.length) {
      setActiveId('')
      return
    }
    if (!activeId || !sessions.some((session) => session.id === activeId)) {
      setActiveId(sessions[0].id)
    }
  }, [activeId, sessions])

  useEffect(() => {
    window.localStorage.setItem(AI_SESSION_STORAGE_KEY, JSON.stringify(sessions))
  }, [sessions])

  useEffect(() => {
    if (activeId) window.localStorage.setItem(AI_ACTIVE_SESSION_STORAGE_KEY, activeId)
    else window.localStorage.removeItem(AI_ACTIVE_SESSION_STORAGE_KEY)
  }, [activeId])

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeId) || sessions[0],
    [activeId, sessions],
  )

  function createSession() {
    const next = makeSession(sessions.length + 1)
    setSessions((items) => [next, ...items])
    setActiveId(next.id)
    setDraft('')
  }

  function deleteSession(sessionId: string) {
    if (activeId === sessionId) setDraft('')
    setSessions((items) => {
      const remaining = items.filter((session) => session.id !== sessionId)
      if (activeId === sessionId) setActiveId(remaining[0]?.id || '')
      return remaining
    })
  }

  function updateSession(sessionId: string, updater: (session: ChatSession) => ChatSession) {
    setSessions((items) => items.map((session) => session.id === sessionId ? updater(session) : session))
  }

  async function submit() {
    const task = draft.trim()
    if (!task || !activeSession || submitting) return

    const sessionId = activeSession.id
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: task }
    setDraft('')
    setSubmitting(true)
    updateSession(sessionId, (session) => ({
      ...session,
      title: session.messages.length <= 1 ? task.slice(0, 18) || session.title : session.title,
      updatedAt: nowText(),
      messages: [...session.messages, userMessage],
    }))

    try {
      const payload: Record<string, unknown> = { task }
      if (modelConfig.baseUrl) payload.base_url = modelConfig.baseUrl
      if (modelConfig.model) payload.model = modelConfig.model
      if (modelConfig.apiKey) payload.api_key = modelConfig.apiKey
      const result = await runAgent(payload)
      const answer = result?.answer || result?.message || result?.summary || JSON.stringify(result, null, 2)
      updateSession(sessionId, (session) => ({
        ...session,
        updatedAt: nowText(),
        messages: [...session.messages, { id: crypto.randomUUID(), role: 'assistant', content: String(answer) }],
      }))
    } catch (err: any) {
      updateSession(sessionId, (session) => ({
        ...session,
        updatedAt: nowText(),
        messages: [...session.messages, { id: crypto.randomUUID(), role: 'assistant', content: err?.message || 'Agent 请求失败' }],
      }))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="ai-app">
      <aside className="ai-sidebar">
        <button className="ai-new-session" onClick={createSession}>新建会话</button>
        <nav className="ai-session-list">
        {!sessions.length && <div className="ai-session-empty">暂无会话，点击上方新建会话开始。</div>}
        {sessions.map((session) => (
          <div key={session.id} className={`ai-session ${session.id === activeSession?.id ? 'ai-session--active' : ''}`}>
            <button
              type="button"
              className="ai-session-main"
              onClick={() => setActiveId(session.id)}
            >
              <span className="ai-session-copy">
                <span>{session.title}</span>
                <small>{session.messages.length} 条消息 · {session.updatedAt}</small>
              </span>
            </button>
            <button
              type="button"
              aria-label={`删除会话 ${session.title}`}
              className="ai-session-delete"
              onPointerDown={(event) => event.stopPropagation()}
              onMouseDown={(event) => event.stopPropagation()}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                deleteSession(session.id)
              }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    event.stopPropagation()
                    deleteSession(session.id)
                  }
                }}
              >
                ×
              </button>
            </div>
          ))}
        </nav>
      </aside>

      <main className="ai-chat">
        <header className="ai-chat-head">
          <div>
            <h2>{activeSession?.title || 'AI 助手'}</h2>
            <p>用自然语言调度 MediaTools 后端能力。</p>
          </div>
          <div className="ai-model-badge">
            <span>{activeModel}</span>
            <small>{modelMode}</small>
          </div>
        </header>

        <section className="ai-message-list">
          <div className="ai-model-context" aria-label={`当前模型 ${activeModel}`}>
            <span>当前模型</span>
            <strong>{activeModel}</strong>
            <small>{modelMode}</small>
          </div>
          {activeSession?.messages.map((message) => (
            <article key={message.id} className={`ai-message ai-message--${message.role}`}>
              <span>{message.role === 'user' ? '你' : 'AI'}</span>
              <p>{message.content}</p>
            </article>
          ))}
          {submitting && (
            <article className="ai-message ai-message--assistant">
              <span>AI</span>
              <p>正在调用 Agent...</p>
            </article>
          )}
        </section>

        <footer className="ai-composer">
          <div className="ai-composer-box">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) void submit()
              }}
              placeholder="例如：下载这个 YouTube 视频，转成 H.264，并把字幕转换成 SRT"
            />
            <div className="ai-composer-actions">
              <small>Ctrl Enter</small>
              <button onClick={() => void submit()} disabled={!draft.trim() || submitting}>
                {submitting ? '发送中...' : '发送'}
              </button>
            </div>
          </div>
        </footer>
      </main>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'

import { runAgent } from '@/api'
import { useModelConfig } from '@/modelConfigStore'

type ChatMessage = { id: string; role: 'user' | 'assistant'; content: string }

type DownloaderMiniAiChatProps = {
  open: boolean
  onClose: () => void
  /** 附在每次 Agent 提问前的隐式上下文（如当前选中任务），不在界面展示 */
  taskContextLine: string | null
}

export function DownloaderMiniAiChat({ open, onClose, taskContextLine }: DownloaderMiniAiChatProps) {
  const { config: modelConfig } = useModelConfig()
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: 'welcome',
      role: 'assistant',
      content:
        '我是下载辅助助手。你可以问我链接解析、参数选择、失败排查，或让我根据当前列表任务给建议。',
    },
  ])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const threadRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const el = threadRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, sending, open])

  useEffect(() => {
    if (!open) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  async function send() {
    const text = draft.trim()
    if (!text || sending) return

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text }
    setDraft('')
    setSending(true)
    setMessages((items) => [...items, userMessage])

    const contextBlock = taskContextLine ? `[下载器上下文]\n${taskContextLine}\n\n` : ''
    const taskPayload = `${contextBlock}用户问题：\n${text}`

    try {
      const payload: Record<string, unknown> = { task: taskPayload }
      if (modelConfig.baseUrl) payload.base_url = modelConfig.baseUrl
      if (modelConfig.model) payload.model = modelConfig.model
      if (modelConfig.apiKey) payload.api_key = modelConfig.apiKey

      const result = await runAgent(payload)
      const answer = result?.answer || result?.message || result?.summary || JSON.stringify(result, null, 2)
      setMessages((items) => [
        ...items,
        { id: crypto.randomUUID(), role: 'assistant', content: String(answer) },
      ])
    } catch (err: any) {
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: err?.message || 'Agent 请求失败',
        },
      ])
    } finally {
      setSending(false)
    }
  }

  if (!open) return null

  return (
    <div className="dl-mini-ai" role="dialog" aria-label="所选任务 · 下载辅助对话">
      <header className="dl-mini-ai__head">
        <span className="dl-mini-ai__title">所选任务</span>
        <button type="button" className="dl-mini-ai__close" onClick={onClose} aria-label="关闭">
          ×
        </button>
      </header>
      <div ref={threadRef} className="dl-mini-ai__thread">
        {messages.map((message) => (
          <article key={message.id} className={`ai-message ai-message--${message.role}`}>
            {message.role === 'assistant' ? <span>AI</span> : <span className="dl-mini-ai__peer-label" aria-hidden="true" />}
            <p>{message.content}</p>
          </article>
        ))}
        {sending && (
          <article className="ai-message ai-message--assistant dl-mini-ai__typing">
            <span>AI</span>
            <p>正在调用 Agent...</p>
          </article>
        )}
      </div>
      <div className="dl-mini-ai__composer">
        <div className="dl-mini-ai__composer-inner">
          <textarea
            className="dl-mini-ai__input"
            rows={1}
            placeholder="描述问题或粘贴链接…"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void send()
              }
            }}
            disabled={sending}
          />
          <button
            type="button"
            className="dl-btn dl-btn--primary dl-mini-ai__send"
            onClick={() => void send()}
            disabled={!draft.trim() || sending}
          >
            {sending ? '发送中' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}

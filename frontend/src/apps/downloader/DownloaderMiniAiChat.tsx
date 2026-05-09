import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

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
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [draftLinesLayout, setDraftLinesLayout] = useState(1)
  const [horizOverflow, setHorizOverflow] = useState(false)

  const logicalLineCount = draft.length === 0 ? 0 : draft.split(/\r\n|\r|\n/).length

  const measureDraft = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    setHorizOverflow(el.scrollWidth > el.clientWidth + 2)
    const linePx =
      Number.parseFloat(getComputedStyle(el).lineHeight) || Number.parseFloat(String(getComputedStyle(el).fontSize)) * 1.35 || 17
    const wrappedLines = Math.max(1, Math.round(el.scrollHeight / Math.max(linePx, 12)))
    setDraftLinesLayout(wrappedLines)
  }, [])

  const displayLineCount = draft.length === 0 ? 0 : Math.max(logicalLineCount, draftLinesLayout)

  useLayoutEffect(() => {
    if (!open) return
    measureDraft()
  }, [draft, open, measureDraft])

  useEffect(() => {
    if (!open) return
    const wrapEl = textareaRef.current?.closest('.dl-mini-ai__input-wrap')
    if (!wrapEl || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => measureDraft())
    ro.observe(wrapEl)
    return () => ro.disconnect()
  }, [open, measureDraft])

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
          <div className="dl-mini-ai__input-wrap">
            <textarea
              ref={textareaRef}
              className="dl-mini-ai__input"
              rows={1}
              placeholder="描述问题或粘贴链接…"
              value={draft}
              aria-describedby={draft.length > 0 ? 'dl-mini-ai-draft-stats' : undefined}
              title={
                draft
                  ? `约 ${displayLineCount} 行（含自动换行）·${draft.length} 字`
                  : 'Enter 发送，Shift+Enter 换行；宽条内仅单行展示，可看右侧行数摘要'
              }
              spellCheck={false}
              onChange={(event) => setDraft(event.target.value)}
              onInput={measureDraft}
              onScroll={measureDraft}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void send()
                }
              }}
              disabled={sending}
            />
          </div>
          {draft.length > 0 && (
            <div id="dl-mini-ai-draft-stats" className="dl-mini-ai__draft-stats" aria-live="polite">
              {displayLineCount > 1 || logicalLineCount > 1 ? (
                <>
                  <span>{Math.max(displayLineCount, logicalLineCount)}行</span>
                  <span aria-hidden="true">·</span>
                </>
              ) : null}
              <span>{draft.length}字</span>
              {horizOverflow ? (
                <>
                  <span aria-hidden="true">·</span>
                  <abbr className="dl-mini-ai__draft-stats-hint" title="可向左右拖拽查看首尾">
                    ↔
                  </abbr>
                </>
              ) : null}
            </div>
          )}
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

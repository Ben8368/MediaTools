import { memo, useEffect, useState } from 'react'

import { FontPicker } from '@/apps/mediatools/FontPicker'
import { PrimaryButton, ToolbarButton } from '@/apps/mediatools/primitives'
import type { AnyRecord } from '@/types'

type AutomationTaskDialogProps = {
  open: boolean
  title: string
  task: AnyRecord | null
  index: number
  selected: boolean
  fonts: string[]
  accent?: 'blue' | 'purple'
  onClose: () => void
  onSave: (index: number, patch: AnyRecord, selected: boolean) => void
}

export function AutomationTaskDialog({
  open,
  title,
  task,
  index,
  selected,
  fonts,
  accent = 'blue',
  onClose,
  onSave,
}: AutomationTaskDialogProps) {
  const [draft, setDraft] = useState<AnyRecord>({})

  useEffect(() => {
    if (open && task) setDraft({ ...task })
  }, [open, task])

  if (!open || !task) return null

  const save = (nextSelected = selected, statusPatch?: string) => {
    const patch = {
      target_text: draft.target_text || '',
      target_font: draft.target_font || '',
      output_name: draft.output_name || '',
      status: statusPatch || draft.status || 'pending',
      preserve_copy: Boolean(draft.preserve_copy),
    }
    onSave(index, patch, nextSelected)
    onClose()
  }

  return (
    <div className="automation-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className={`automation-dialog automation-dialog--${accent}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="automation-dialog-head">
          <div>
            <span>任务确认</span>
            <h3>{title}</h3>
            <p>确认替换文本、字体和输出名后再加入执行队列。</p>
          </div>
          <button className="automation-dialog-close" type="button" onClick={onClose} aria-label="关闭">×</button>
        </header>

        <div className="automation-dialog-grid">
          <label>
            原始文本
            <textarea value={draft.original_text || ''} readOnly />
          </label>
          <label>
            替换文本
            <textarea
              value={draft.target_text || ''}
              readOnly={Boolean(draft.preserve_copy)}
              onChange={(event) => setDraft({ ...draft, target_text: event.target.value })}
            />
          </label>
          <label>
            当前字体
            <input value={draft.source_font || draft.font || ''} readOnly />
          </label>
          <FontPicker
            label="目标字体"
            ariaLabel="目标字体"
            value={draft.target_font || ''}
            sourceFont={draft.source_font || draft.font || ''}
            fonts={fonts}
            accent={accent}
            disabled={Boolean(draft.preserve_copy)}
            onChange={(font) => setDraft({ ...draft, target_font: font })}
          />
          <label className="automation-dialog-preserve">
            <span>
              <input
                type="checkbox"
                checked={Boolean(draft.preserve_copy)}
                onChange={(event) => {
                  const v = event.target.checked
                  setDraft({
                    ...draft,
                    preserve_copy: v,
                    ...(v ? { target_text: '', target_font: '' } : {}),
                  })
                }}
              />
              固定文案（产品名等：不参与 Ai 翻译与批量改字体，执行沿用母版）
            </span>
          </label>
          <label>
            输出名称
            <input value={draft.output_name || ''} onChange={(event) => setDraft({ ...draft, output_name: event.target.value })} />
          </label>
          <label>
            状态
            <select value={draft.status || 'pending'} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>
              <option value="pending">待确认</option>
              <option value="confirmed">确认执行</option>
              <option value="skip">跳过</option>
            </select>
          </label>
        </div>

        <footer className="automation-dialog-actions">
          <ToolbarButton onClick={() => save(false, 'skip')}>标记跳过</ToolbarButton>
          <ToolbarButton onClick={() => save(selected)}>保存</ToolbarButton>
          <PrimaryButton onClick={() => save(true, 'confirmed')}>确认并选择</PrimaryButton>
        </footer>
      </section>
    </div>
  )
}

export const AutomationTaskDialogMemo = memo(AutomationTaskDialog)

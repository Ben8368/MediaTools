import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

import { CloseIcon } from '@/apps/file-manager/controls'

export type PhotoshopLocalePreset = {
  code: string
  label: string
  bcp47: string
}

/** 与界面展示一致的 8 种预设（code 为用户可见缩写） */
export const PHOTOSHOP_LOCALE_PRESETS: PhotoshopLocalePreset[] = [
  { code: 'EN', label: '英语', bcp47: 'en-US' },
  { code: 'JP', label: '日语', bcp47: 'ja-JP' },
  { code: 'KR', label: '韩语', bcp47: 'ko-KR' },
  { code: 'SC', label: '简中', bcp47: 'zh-CN' },
  { code: 'TC', label: '繁中', bcp47: 'zh-TW' },
  { code: 'PT', label: '葡语', bcp47: 'pt-BR' },
  { code: 'ES', label: '西语', bcp47: 'es-ES' },
  { code: 'ID', label: '印尼', bcp47: 'id-ID' },
]

export type PhotoshopLocaleRequestResult = {
  presets: PhotoshopLocalePreset[]
  customRaw: string
}

type PhotoshopLocaleRequestDialogProps = {
  open: boolean
  portalContainer?: HTMLElement | null
  onClose: () => void
  onConfirm: (result: PhotoshopLocaleRequestResult) => void | Promise<void>
}

export function PhotoshopLocaleRequestDialog({
  open,
  portalContainer,
  onClose,
  onConfirm,
}: PhotoshopLocaleRequestDialogProps) {
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(() => new Set())
  const [customExtra, setCustomExtra] = useState('')

  useEffect(() => {
    if (!open) return
    setSelectedCodes(new Set())
    setCustomExtra('')
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  const togglePreset = useCallback((code: string) => {
    setSelectedCodes((prev) => {
      const next = new Set(prev)
      if (next.has(code)) next.delete(code)
      else next.add(code)
      return next
    })
  }, [])

  const handleConfirm = useCallback(() => {
    const presets = PHOTOSHOP_LOCALE_PRESETS.filter((item) => selectedCodes.has(item.code))
    onConfirm({ presets, customRaw: customExtra })
  }, [customExtra, onConfirm, selectedCodes])

  if (!open) return null

  const dialog = (
    <div className="fm-picker fm-picker--app-root" role="presentation" onClick={onClose}>
      <div
        className="fm-picker__panel fm-picker__panel--compact"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ps-locale-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="fm-picker__header">
          <div>
            <strong id="ps-locale-dialog-title">语种需求</strong>
            <p className="ps-locale-dialog__hint">确认后写入当前工单并保存；执行时每语种输出对应文件名的 PSD（可在任务表中改 output_name）。</p>
          </div>
          <button type="button" className="fm-icon-btn" title="关闭" aria-label="关闭" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>

        <div className="fm-picker__content fm-picker__content--compact ps-locale-dialog__body">
          <div className="ps-locale-presets" role="group" aria-label="语种预设">
            {PHOTOSHOP_LOCALE_PRESETS.map((item) => {
              const on = selectedCodes.has(item.code)
              return (
                <button
                  key={item.code}
                  type="button"
                  className={`ps-locale-preset ${on ? 'ps-locale-preset--active' : ''}`}
                  aria-pressed={on}
                  onClick={() => togglePreset(item.code)}
                >
                  <span className="ps-locale-preset__label">{item.label}</span>
                  <span className="ps-locale-preset__code">{item.code}</span>
                </button>
              )
            })}
          </div>
          <label className="ps-locale-custom">
            <span>补充语种（预设未列出时）</span>
            <input
              value={customExtra}
              onChange={(e) => setCustomExtra(e.target.value)}
              title="与工单里目标语言字段保持一致更易执行；可用 BCP 47（如 fr-FR、de-DE）或简短拉丁字母码、中文语种名，多项用逗号分隔"
              placeholder="推荐与工单一致：fr-FR、de-DE；或简短码 FR、DE 及中文名如泰语（逗号分隔）"
              spellCheck={false}
              autoComplete="off"
            />
          </label>
        </div>

        <div className="fm-picker__footer">
          <div className="fm-picker__selection">
            <strong>已选预设</strong>
            <span>
              {selectedCodes.size
                ? [...selectedCodes].sort().join('、')
                : '未选择'}
            </span>
          </div>
          <div className="fm-picker__footer-actions">
            <button type="button" className="fm-action-btn" onClick={onClose}>
              取消
            </button>
            <button
              type="button"
              className="fm-action-btn fm-action-btn--primary"
              onClick={handleConfirm}
            >
              确认
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  return portalContainer ? createPortal(dialog, portalContainer) : dialog
}

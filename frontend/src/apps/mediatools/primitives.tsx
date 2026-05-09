import { useRef, useState } from 'react'

import { DirectoryPickerDialog } from '@/apps/FileManagerApp'

export function ResultBox({ value }: { value: unknown }) {
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  return <pre className="mt-result">{text}</pre>
}

export function Field({ label, children }: { label?: string; children: React.ReactNode }) {
  return (
    <div className="mt-field">
      {label ? <span className="mt-field__label">{label}</span> : null}
      {children}
    </div>
  )
}

export function ToolbarButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={`mt-btn ${props.className || ''}`} />
}

export function PrimaryButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={`mt-btn mt-btn--primary ${props.className || ''}`} />
}

export function PathInput({
  value,
  onChange,
  mode = 'file',
  placeholder,
}: {
  value: string
  onChange: (value: string) => void
  mode?: 'file' | 'directory' | 'any'
  placeholder?: string
}) {
  const [open, setOpen] = useState(false)
  const [portalContainer, setPortalContainer] = useState<HTMLElement | null>(null)
  const rootRef = useRef<HTMLDivElement>(null)

  function openPicker() {
    const root = rootRef.current?.closest('.dl-app, .ps-app, .ae-app, .tool-app, .wb-app, .au-app, .fm-app')
    setPortalContainer(root instanceof HTMLElement ? root : null)
    setOpen(true)
  }

  return (
    <>
      <div className="mt-path-input" ref={rootRef}>
        <input
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
        />
        <ToolbarButton type="button" onClick={openPicker}>
          {mode === 'directory' ? '浏览目录' : '浏览文件'}
        </ToolbarButton>
      </div>
      <DirectoryPickerDialog
        open={open}
        value={value}
        mode={mode}
        title={mode === 'directory' ? '选择目录' : '选择文件'}
        confirmLabel="确认"
        portalContainer={portalContainer}
        onClose={() => setOpen(false)}
        onPick={onChange}
      />
    </>
  )
}

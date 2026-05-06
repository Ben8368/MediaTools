import { useState } from 'react'

export function AppLayout({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="app-surface">
      {title && (
        <div className="app-surface__header">
          <h2>{title}</h2>
        </div>
      )}
      <div className="app-surface__body">{children}</div>
    </div>
  )
}

export function SidebarItem({ icon, label, active }: { icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 12px', borderRadius: '8px',
      cursor: 'pointer', fontSize: '13px',
      background: active ? 'var(--fnos-brand-light)' : 'transparent',
      color: active ? 'var(--fnos-brand)' : 'var(--fnos-text-1)',
      fontWeight: active ? 600 : 400,
    }}>
      {icon}
      <span>{label}</span>
    </div>
  )
}

export function StatCard({ label, value, percent, color }: { label: string; value: string; percent?: number; color?: string }) {
  return (
    <div style={{ background: 'var(--fnos-surface)', borderRadius: '12px', padding: '16px' }}>
      <div style={{ fontSize: '12px', color: 'var(--fnos-text-2)', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontSize: '22px', fontWeight: 600, color: color || 'var(--fnos-text-0)' }}>{value}</div>
      {percent !== undefined && (
        <div style={{ width: '100%', height: '4px', background: 'var(--fnos-fill)', borderRadius: '2px', marginTop: '8px', overflow: 'hidden' }}>
          <div style={{ width: `${percent}%`, height: '100%', background: percent > 80 ? 'var(--fnos-danger)' : 'var(--fnos-brand)', borderRadius: '2px' }}/>
        </div>
      )}
    </div>
  )
}

export function Toggle({ defaultChecked }: { defaultChecked?: boolean }) {
  const [on, setOn] = useState(defaultChecked ?? false)
  return (
    <div onClick={() => setOn(!on)} style={{
      width: '40px', height: '22px', borderRadius: '11px', cursor: 'pointer', position: 'relative',
      background: on ? 'var(--fnos-brand)' : 'var(--fnos-fill-2)',
      transition: 'background 0.2s',
    }}>
      <div style={{
        width: '18px', height: '18px', borderRadius: '9px', background: 'white',
        position: 'absolute', top: '2px', left: on ? '20px' : '2px',
        transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,.2)',
      }}/>
    </div>
  )
}

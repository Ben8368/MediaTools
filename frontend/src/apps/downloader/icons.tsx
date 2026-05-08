export function CategoryIcon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      {name === 'grid' && (
        <>
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </>
      )}
      {name === 'download' && (
        <>
          <path d="M12 4v12" />
          <path d="M7 11l5 5 5-5" />
          <path d="M4 19h16" />
        </>
      )}
      {name === 'check' && <path d="M20 6L9 17l-5-5" />}
      {name === 'active' && (
        <>
          <path d="M22 12h-4" />
          <path d="M2 12h4" />
          <path d="M12 2v4" />
          <path d="M12 18v4" />
          <circle cx="12" cy="12" r="4" />
        </>
      )}
      {name === 'idle' && (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4l3 3" />
        </>
      )}
      {name === 'pause' && (
        <>
          <rect x="6" y="4" width="4" height="16" />
          <rect x="14" y="4" width="4" height="16" />
        </>
      )}
      {name === 'error' && (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </>
      )}
    </svg>
  )
}

export function StatusIcon({ status }: { status: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={`dl-status-icon dl-status-icon--${status}`}>
      {status === 'running' && <path d="M5 3l14 9-14 9V3z" />}
      {status === 'pending' && (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4l3 3" />
        </>
      )}
      {status === 'completed' && (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M8 12l3 3 5-5" />
        </>
      )}
      {(status === 'failed' || status === 'cancelled' || status === 'paused') && (
        <>
          <circle cx="12" cy="12" r="10" />
          <path d="M15 9l-6 6M9 9l6 6" />
        </>
      )}
    </svg>
  )
}

export const PlusIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M12 5v14M5 12h14" />
  </svg>
)

export const StopIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <rect x="6" y="6" width="12" height="12" rx="2" />
  </svg>
)

export const RetryIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 0115.5-6.36L21 8" />
    <path d="M21 3v5h-5" />
    <path d="M21 12a9 9 0 01-15.5 6.36L3 16" />
    <path d="M8 16H3v5" />
  </svg>
)

export const DeleteIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
  </svg>
)

export const SelectAllIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="4" width="16" height="16" rx="3" />
    <path d="M8 12l2.5 2.5L16 9" />
  </svg>
)

export const SearchIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <circle cx="11" cy="11" r="8" />
    <path d="M21 21l-4.35-4.35" />
  </svg>
)

/** 星芒群，与侧栏其它描线图标一致，表示 AI */
export const AiIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2.5l1.2 4.1L17.3 8l-4.1 1.4L12 13.5l-1.2-4.1L6.7 8l4.1-1.4L12 2.5z" />
    <path d="M18.5 15l.6 1.9 1.9.6-1.9.6L18.5 20l-.6-1.9-1.9-.6 1.9-.6L18.5 15z" />
    <path d="M5 13.5l.5 1.6L7 15.5l-1.5.4L5 17.5l-.5-1.6-1.5-.4L4.5 15l1.5-.4L5 13.5z" />
  </svg>
)

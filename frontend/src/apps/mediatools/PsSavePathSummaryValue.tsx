import { useLayoutEffect, useRef, useState } from 'react'

const LEADING_ELLIPSIS = '\u2026'

function createWidthMeasurer(styleSource: HTMLElement) {
  const span = document.createElement('span')
  span.setAttribute('aria-hidden', 'true')
  const cs = getComputedStyle(styleSource)
  span.style.fontFamily = cs.fontFamily
  span.style.fontSize = cs.fontSize
  span.style.fontWeight = cs.fontWeight
  span.style.fontStyle = cs.fontStyle
  span.style.letterSpacing = cs.letterSpacing
  span.style.fontVariantNumeric = cs.fontVariantNumeric
  span.style.whiteSpace = 'nowrap'
  span.style.position = 'absolute'
  span.style.left = '-99999px'
  span.style.top = '0'
  span.style.pointerEvents = 'none'
  document.body.appendChild(span)
  return {
    measure(text: string) {
      span.textContent = text
      return span.getBoundingClientRect().width
    },
    dispose() {
      span.remove()
    },
  }
}

/** 在不超过 maxWidth 的前提下尽量保留路径尾部；必要时加前导省略号 */
export function fitPathWithLeadingEllipsis(path: string, maxWidthPx: number, styleSource: HTMLElement): string {
  if (!path || maxWidthPx <= 2) return path
  const m = createWidthMeasurer(styleSource)
  try {
    const slack = 2
    const budget = Math.max(0, maxWidthPx - slack)
    if (m.measure(path) <= budget) return path
    let lo = 0
    let hi = path.length
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2)
      const candidate = LEADING_ELLIPSIS + path.slice(mid)
      if (m.measure(candidate) <= budget) hi = mid
      else lo = mid + 1
    }
    if (lo >= path.length) return LEADING_ELLIPSIS
    return LEADING_ELLIPSIS + path.slice(lo)
  } finally {
    m.dispose()
  }
}

type Props = {
  path: string
  placeholder: string
  title?: string
}

export function PsSavePathSummaryValue({ path, placeholder, title }: Props) {
  const trimmed = path.trim()
  const isEmpty = !trimmed
  const ref = useRef<HTMLSpanElement>(null)
  const [display, setDisplay] = useState(() => (path.trim() ? path.trim() : placeholder))

  useLayoutEffect(() => {
    if (isEmpty) {
      setDisplay(placeholder)
      return
    }
    const el = ref.current
    if (!el) return
    setDisplay(trimmed)

    const apply = () => {
      const w = el.clientWidth
      if (w <= 0) return
      setDisplay(fitPathWithLeadingEllipsis(trimmed, w, el))
    }

    apply()
    const ro = new ResizeObserver(apply)
    ro.observe(el)
    return () => ro.disconnect()
  }, [trimmed, isEmpty, placeholder])

  return (
    <span
      ref={ref}
      className={`ps-save-path-summary__value${isEmpty ? ' ps-save-path-summary__value--empty' : ''}`}
      title={title}
    >
      {isEmpty ? placeholder : display}
    </span>
  )
}

import { useEffect, useMemo, useState } from 'react'

type FontPickerProps = {
  label?: string
  ariaLabel: string
  value: string
  fonts: string[]
  sourceFont?: string
  emptyLabel?: string
  accent?: 'blue' | 'purple'
  compact?: boolean
  /** 隐藏列标题，仅保留控件本身（任务行等紧凑场景） */
  hideLabels?: boolean
  /** 为 true 时不可展开列表、不可改选（如固定文案行） */
  disabled?: boolean
  onChange: (value: string) => void
}

type FontVariant = {
  value: string
  family: string
  style: string
  order: number
  italic: boolean
  weight: number
}

const STYLE_PATTERNS = [
  ['ExtraLight Italic', 200, true],
  ['ExtraLight', 200, false],
  ['SemiBold Italic', 600, true],
  ['SemiBold', 600, false],
  ['ExtraBold Italic', 800, true],
  ['ExtraBold', 800, false],
  ['Black Italic', 900, true],
  ['Black', 900, false],
  ['Bold Italic', 700, true],
  ['Bold', 700, false],
  ['Medium Italic', 500, true],
  ['Medium', 500, false],
  ['Light Italic', 300, true],
  ['Light', 300, false],
  ['Thin Italic', 100, true],
  ['Thin', 100, false],
  ['Regular Italic', 400, true],
  ['Italic', 400, true],
  ['Regular', 400, false],
] as const

const STYLE_ORDER = ['Thin', 'ExtraLight', 'Light', 'Regular', 'Italic', 'Medium', 'SemiBold', 'Bold', 'ExtraBold', 'Black']

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function styleSuffixPattern(style: string) {
  return style.split(/\s+/).map(escapeRegExp).join('[\\s_-]*')
}

function uniqueFonts(fonts: string[]) {
  return Array.from(new Set(fonts.map((font) => String(font || '').trim()).filter(Boolean)))
}

function displayFamilyName(family: string) {
  return family
    .replace(/[-_]+/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
}

function parseFont(font: string): FontVariant {
  const cleaned = font.trim()
  let family = cleaned
  let style = 'Regular'
  let weight = 400
  let italic = false

  const match = STYLE_PATTERNS.find(([name]) => {
    const suffix = styleSuffixPattern(name)
    return new RegExp(`[\\s_-]+${suffix}$`, 'i').test(cleaned)
      || new RegExp(`${suffix}$`, 'i').test(cleaned.replace(/([a-z])([A-Z])/g, '$1 $2'))
  })

  if (match) {
    const suffix = styleSuffixPattern(match[0])
    family = cleaned
      .replace(new RegExp(`[\\s_-]+${suffix}$`, 'i'), '')
      .replace(new RegExp(`${suffix}$`, 'i'), '')
      .replace(/[-_\s]+$/, '')
      || cleaned
    style = match[0]
    weight = match[1]
    italic = match[2]
  }

  const styleBase = style.replace(' Italic', '')
  const order = STYLE_ORDER.indexOf(styleBase) === -1 ? 99 : STYLE_ORDER.indexOf(styleBase)
  return { value: cleaned, family: displayFamilyName(family), style, order, italic, weight }
}

/** 含空格检索时按词同时匹配（如「noto sc」可命中「Noto Sans SC」） */
function fontMatchesQuery(parsed: FontVariant, needle: string): boolean {
  const q = needle.trim().toLowerCase()
  if (!q) return true
  const hay = `${parsed.family} ${parsed.value}`.toLowerCase()
  const tokens = q.split(/\s+/).filter(Boolean)
  return tokens.length > 0 && tokens.every((t) => hay.includes(t))
}

function buildGroups(fonts: string[], query: string) {
  const needle = query.trim()
  const groups = new Map<string, FontVariant[]>()
  uniqueFonts(fonts).forEach((font) => {
    const parsed = parseFont(font)
    if (!fontMatchesQuery(parsed, needle)) return
    const list = groups.get(parsed.family) || []
    if (!list.some((item) => item.value === parsed.value)) list.push(parsed)
    groups.set(parsed.family, list)
  })
  return Array.from(groups.entries())
    .map(([family, variants]) => ({
      family,
      variants: variants.sort((a, b) => a.order - b.order || Number(a.italic) - Number(b.italic) || a.value.localeCompare(b.value)),
    }))
    .sort((a, b) => a.family.localeCompare(b.family))
}

export function FontPicker({
  label = '字体',
  ariaLabel,
  value,
  fonts,
  sourceFont,
  emptyLabel,
  accent = 'blue',
  compact = false,
  hideLabels = false,
  disabled = false,
  onChange,
}: FontPickerProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  useEffect(() => {
    if (disabled) setOpen(false)
  }, [disabled])

  const allFonts = useMemo(() => uniqueFonts([value, sourceFont || '', ...fonts]), [fonts, sourceFont, value])
  const groups = useMemo(() => buildGroups(allFonts, query), [allFonts, query])

  const currentFont = value ? parseFont(value) : null
  const sourceFontInfo = sourceFont ? parseFont(sourceFont) : null

  const currentFamily = currentFont?.family || ''

  const defaultEmptyLabel = emptyLabel || (sourceFontInfo ? `沿用源字体：${sourceFontInfo.family}` : '沿用源字体')

  const closeMenus = () => {
    setOpen(false)
  }

  const handleFamilyChange = (newFamily: string) => {
    if (disabled) return
    if (!newFamily) {
      onChange('')
      setQuery('')
      setOpen(false)
      return
    }
    const allGroups = buildGroups(allFonts, '')
    const group = allGroups.find((g) => g.family === newFamily)
    if (group && group.variants.length > 0) {
      onChange(group.family)
    } else {
      onChange(newFamily)
    }
    setQuery('')
    setOpen(false)
  }

  const halfClass = `font-picker-half ${hideLabels ? 'font-picker-half--nolabel' : ''}`
  const locked = disabled

  return (
    <div
      className={`font-picker-split font-picker-split--${accent} ${compact ? 'font-picker-split--compact' : ''}${
        locked ? ' font-picker-split--disabled' : ''
      }`}
      onBlur={(event) => {
        if (locked) return
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) closeMenus()
      }}
    >
      <label className={halfClass}>
        {!hideLabels ? <b>{label}</b> : null}
        <div className={`font-picker ${open ? 'font-picker--open' : 'font-picker--closed'} ${currentFamily ? 'font-picker--selected' : ''}`}>
          {!open && (
            <div className="font-picker-summary" aria-hidden="true">
              <span>{currentFamily || defaultEmptyLabel}</span>
            </div>
          )}
          <input
            aria-label={ariaLabel}
            readOnly={locked}
            disabled={locked}
            value={open && !locked ? query : currentFamily}
            onChange={(event) => {
              if (locked) return
              setQuery(event.target.value)
              setOpen(true)
            }}
            onKeyDown={(event) => {
              if (locked) return
              if (event.key !== 'Enter') return
              event.preventDefault()
              const firstMatch = groups[0]?.family
              if (firstMatch) handleFamilyChange(firstMatch)
            }}
            onFocus={() => {
              if (locked) return
              setQuery('')
              setOpen(true)
            }}
            placeholder={currentFamily || defaultEmptyLabel}
          />
          <button
            type="button"
            aria-label="展开字体列表"
            disabled={locked}
            onClick={() => {
              if (locked) return
              setOpen((next) => !next)
            }}
          >
            ⌄
          </button>
          {open && !locked && (
            <div className="font-picker-menu" role="listbox">
              <button
                type="button"
                role="option"
                aria-selected={!currentFamily}
                className={`font-picker-option ${!currentFamily ? 'font-picker-option--active' : ''}`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => handleFamilyChange('')}
              >
                <span>{defaultEmptyLabel}</span>
              </button>
              {groups.map((group) => (
                <button
                  type="button"
                  role="option"
                  aria-selected={currentFamily === group.family}
                  className={`font-picker-option ${currentFamily === group.family ? 'font-picker-option--active' : ''}`}
                  key={group.family}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleFamilyChange(group.family)}
                >
                  <span>{group.family}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </label>
    </div>
  )
}

import { useMemo, useState } from 'react'

type FontPickerProps = {
  label?: string
  ariaLabel: string
  value: string
  fonts: string[]
  sourceFont?: string
  emptyLabel?: string
  accent?: 'blue' | 'purple'
  compact?: boolean
  /** 隐藏「字体家族」「字重」列标题，仅保留控件本身（任务行等紧凑场景） */
  hideLabels?: boolean
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

function buildGroups(fonts: string[], query: string) {
  const needle = query.trim().toLowerCase()
  const groups = new Map<string, FontVariant[]>()
  uniqueFonts(fonts).forEach((font) => {
    const parsed = parseFont(font)
    if (needle && !parsed.family.toLowerCase().includes(needle)) return
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
    .slice(0, 60)
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
  onChange,
}: FontPickerProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [styleOpen, setStyleOpen] = useState(false)
  const [styleQuery, setStyleQuery] = useState('')
  
  const allFonts = useMemo(() => uniqueFonts([value, sourceFont || '', ...fonts]), [fonts, sourceFont, value])
  const groups = useMemo(() => buildGroups(allFonts, query), [allFonts, query])
  
  const currentFont = value ? parseFont(value) : null
  const sourceFontInfo = sourceFont ? parseFont(sourceFont) : null
  
  const currentFamily = currentFont?.family || ''
  const currentStyle = currentFont?.style || ''
  
  const activeFamily = currentFamily || sourceFontInfo?.family || ''
  const activeGroup = useMemo(() => {
    let group = groups.find(g => g.family === activeFamily)
    if (!group) {
      const allGroups = buildGroups(allFonts, '')
      group = allGroups.find(g => g.family === activeFamily)
    }
    return group
  }, [groups, allFonts, activeFamily])
  
  const availableStyles = activeGroup?.variants || []

  const filteredStyles = useMemo(() => {
    const needle = styleQuery.trim().toLowerCase()
    if (!needle) return availableStyles
    return availableStyles.filter(
      (variant) =>
        variant.style.toLowerCase().includes(needle)
        || variant.value.toLowerCase().includes(needle),
    )
  }, [availableStyles, styleQuery])

  const defaultEmptyLabel = emptyLabel || (sourceFontInfo ? `沿用源字体：${sourceFontInfo.family}` : '沿用源字体')

  const closedStyleInputValue = currentFont?.style || sourceFontInfo?.style || ''

  const styleSummary =
    currentFont?.style
    || (sourceFontInfo && !value.trim() ? sourceFontInfo.style : '')
    || '字重'

  const weightPickerDisabled = !sourceFont?.trim() && !currentFamily

  const closeMenus = () => {
    setOpen(false)
    setStyleOpen(false)
  }

  const handleFamilyChange = (newFamily: string) => {
    if (!newFamily) {
      onChange('')
      setQuery('')
      setOpen(false)
      return
    }
    const allGroups = buildGroups(allFonts, '')
    const group = allGroups.find(g => g.family === newFamily)
    if (group && group.variants.length > 0) {
      const matchedStyle = group.variants.find(v => v.style === currentStyle)
      onChange(matchedStyle ? matchedStyle.value : group.variants[0].value)
    } else {
      onChange(newFamily)
    }
    setQuery('')
    setOpen(false)
  }

  const handleStylePick = (nextValue: string) => {
    onChange(nextValue)
    setStyleQuery('')
    setStyleOpen(false)
  }

  const halfClass = `font-picker-half ${hideLabels ? 'font-picker-half--nolabel' : ''}`

  return (
    <div
      className={`font-picker-split font-picker-split--${accent} ${compact ? 'font-picker-split--compact' : ''}`}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) closeMenus()
      }}
    >
      <label className={halfClass}>
        {!hideLabels ? <b>{label}家族</b> : null}
        <div className={`font-picker ${open ? 'font-picker--open' : 'font-picker--closed'} ${currentFamily ? 'font-picker--selected' : ''}`}>
          {!open && (
            <div className="font-picker-summary" aria-hidden="true">
              <span>{currentFamily || defaultEmptyLabel}</span>
            </div>
          )}
          <input
            aria-label={`${ariaLabel} 家族`}
            value={open ? query : currentFamily}
            onChange={(event) => {
              setQuery(event.target.value)
              setOpen(true)
              setStyleOpen(false)
            }}
            onKeyDown={(event) => {
              if (event.key !== 'Enter') return
              event.preventDefault()
              const firstMatch = groups[0]?.family
              if (firstMatch) handleFamilyChange(firstMatch)
            }}
            onFocus={() => {
              setQuery('')
              setOpen(true)
              setStyleOpen(false)
            }}
            placeholder={currentFamily || defaultEmptyLabel}
          />
          <button
            type="button"
            aria-label="展开字体列表"
            onClick={() => {
              setOpen((next) => !next)
              setStyleOpen(false)
            }}
          >
            ⌄
          </button>
          {open && (
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
      <label className={halfClass}>
        {!hideLabels ? <b>字重</b> : null}
        <div
          className={`font-picker ${styleOpen ? 'font-picker--open' : 'font-picker--closed'} ${closedStyleInputValue ? 'font-picker--selected' : ''}`}
        >
          {!styleOpen && (
            <div className="font-picker-summary" aria-hidden="true">
              <span>{styleSummary}</span>
            </div>
          )}
          <input
            aria-label={`${ariaLabel} 字重`}
            disabled={weightPickerDisabled}
            value={styleOpen ? styleQuery : closedStyleInputValue}
            onChange={(event) => {
              setStyleQuery(event.target.value)
              setStyleOpen(true)
              setOpen(false)
            }}
            onKeyDown={(event) => {
              if (event.key !== 'Enter') return
              event.preventDefault()
              const pick = filteredStyles[0]
              if (pick) {
                handleStylePick(pick.value)
                return
              }
              if (!value.trim() && sourceFontInfo) handleStylePick('')
            }}
            onFocus={() => {
              setStyleQuery('')
              setStyleOpen(true)
              setOpen(false)
            }}
            placeholder={styleSummary}
          />
          <button
            type="button"
            aria-label="展开字重列表"
            disabled={weightPickerDisabled}
            onClick={() => {
              if (weightPickerDisabled) return
              setStyleOpen((next) => !next)
              setOpen(false)
            }}
          >
            ⌄
          </button>
          {styleOpen && !weightPickerDisabled && (
            <div className="font-picker-menu" role="listbox">
              {!value.trim() && sourceFontInfo ? (
                <button
                  type="button"
                  role="option"
                  aria-selected={!value.trim()}
                  className={`font-picker-option ${!value.trim() ? 'font-picker-option--active' : ''}`}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleStylePick('')}
                >
                  <span>沿用源字重：{sourceFontInfo.style}</span>
                </button>
              ) : null}
              {filteredStyles.map((variant) => (
                <button
                  type="button"
                  role="option"
                  aria-selected={currentFont?.value === variant.value}
                  className={`font-picker-option ${currentFont?.value === variant.value ? 'font-picker-option--active' : ''}`}
                  key={variant.value}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleStylePick(variant.value)}
                >
                  <span>{variant.style}</span>
                </button>
              ))}
              {!filteredStyles.length && (Boolean(value.trim()) || !sourceFontInfo) ? (
                <div className="font-picker-empty">没有匹配的字重</div>
              ) : null}
            </div>
          )}
        </div>
      </label>
    </div>
  )
}

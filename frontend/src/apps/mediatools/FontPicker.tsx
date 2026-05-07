import { useMemo, useState } from 'react'

type FontPickerProps = {
  label?: string
  ariaLabel: string
  value: string
  fonts: string[]
  sourceFont?: string
  emptyLabel?: string
  accent?: 'blue' | 'purple'
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
    if (needle && !`${parsed.family} ${parsed.style} ${parsed.value}`.toLowerCase().includes(needle)) return
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
  emptyLabel = sourceFont ? `沿用源字体：${sourceFont}` : '沿用源字体',
  accent = 'blue',
  onChange,
}: FontPickerProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const allFonts = useMemo(() => uniqueFonts([value, sourceFont || '', ...fonts]), [fonts, sourceFont, value])
  const groups = useMemo(() => buildGroups(allFonts, query), [allFonts, query])
  const current = value || ''
  const currentFont = current ? parseFont(current) : null
  const sourceFontInfo = !current && sourceFont ? parseFont(sourceFont) : null
  const summaryFont = currentFont || sourceFontInfo
  const inputValue = open ? query : currentFont ? `${currentFont.family} / ${currentFont.style}` : ''
  const inputPlaceholder = sourceFont ? `选择目标字体，默认沿用 ${sourceFont}` : '选择目标字体'
  const chooseFont = (font: string) => {
    onChange(font)
    setQuery('')
    setOpen(false)
  }

  return (
    <div className={`font-picker-field font-picker-field--${accent}`} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false)
    }}>
      <b>{label}</b>
      <div className={`font-picker ${open ? 'font-picker--open' : 'font-picker--closed'} ${currentFont ? 'font-picker--selected' : ''}`}>
        {!open && (
          <div className="font-picker-summary" aria-hidden="true">
            <span>{summaryFont?.family || '选择目标字体'}</span>
            <strong>{currentFont ? currentFont.style : sourceFontInfo ? `沿用源字体 · ${sourceFontInfo.style}` : '未选择'}</strong>
          </div>
        )}
        <input
          aria-label={ariaLabel}
          value={inputValue}
          onChange={(event) => {
            setQuery(event.target.value)
            setOpen(true)
          }}
          onKeyDown={(event) => {
            if (event.key !== 'Enter') return
            event.preventDefault()
            const firstMatch = groups[0]?.variants[0]?.value
            chooseFont(firstMatch || query.trim())
          }}
          onFocus={() => {
            setQuery('')
            setOpen(true)
          }}
          placeholder={inputPlaceholder}
        />
        <button type="button" aria-label="展开字体列表" onClick={() => setOpen((next) => !next)}>⌄</button>
        {open && (
          <div className="font-picker-menu" role="listbox">
            <button
              type="button"
              role="option"
              aria-selected={!current}
              className={`font-picker-option ${!current ? 'font-picker-option--active' : ''}`}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => chooseFont('')}
            >
              <span>{emptyLabel}</span>
              <em>Source</em>
            </button>
            {groups.map((group) => (
              <section className="font-picker-group" key={group.family}>
                <div className="font-picker-family">
                  <strong>{group.family}</strong>
                  <small>{group.variants.length} 个字重</small>
                </div>
                {group.variants.map((variant) => (
                  <button
                    type="button"
                    role="option"
                    aria-label={variant.value}
                    aria-selected={current === variant.value}
                    className={`font-picker-option ${current === variant.value ? 'font-picker-option--active' : ''}`}
                    key={variant.value}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => chooseFont(variant.value)}
                  >
                    <span>{variant.style}</span>
                    <em style={{ fontWeight: variant.weight, fontStyle: variant.italic ? 'italic' : 'normal' }}>Sample</em>
                  </button>
                ))}
              </section>
            ))}
            {groups.length === 0 && <div className="font-picker-empty">没有匹配字体，按 Enter 使用输入的字体名</div>}
          </div>
        )}
      </div>
    </div>
  )
}

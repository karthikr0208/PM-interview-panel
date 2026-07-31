import { describe, expect, it } from 'vitest'
import { globSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

// Regression guard for the design foundation (Story 1.5). ARCHITECTURE §8 is
// the authority on every value asserted here — if this test ever needs to
// change, the token table in ARCHITECTURE §8 (or a dated Decisions entry
// superseding it) should already have changed first, not the other way
// around.

const here = path.dirname(fileURLToPath(import.meta.url))
const css = readFileSync(path.join(here, 'index.css'), 'utf-8')
const packageJson = readFileSync(
  path.join(here, '..', 'package.json'),
  'utf-8',
)

// Declaration-only view of the stylesheet, comments stripped. The rules
// below (no serif, no pure-black shadow) are about what is DECLARED, not
// about what prose in a comment happens to mention — this file's own
// comments say "no serif" and "not pure black" in plain English, which
// would otherwise trip the very checks meant to catch a real regression.
const cssDeclarations = css.replace(/\/\*[\s\S]*?\*\//g, '')

// ARCHITECTURE §8 "Design tokens" table, exact hex values, both modes.
const ARCHITECTURE_TOKENS = {
  'light background': '#FBFBFA',
  'light surface': '#FFFFFF',
  'light border': '#E6E6E3',
  'light text primary': '#16171A',
  'light text secondary': '#6B6D73',
  'light accent': '#3A63D0',
  'dark background': '#0E0F11',
  'dark surface': '#17181B',
  'dark border': '#26282D',
  'dark text primary': '#ECEDEF',
  'dark text secondary': '#8B8E96',
  'dark accent': '#6E92E8',
  success: '#2E7D5B',
  warning: '#B7791F',
  error: '#B3452C',
}

describe('src/index.css — design token guard', () => {
  it.each(Object.entries(ARCHITECTURE_TOKENS))(
    'declares the ARCHITECTURE §8 %s token with its exact value',
    (_label, hex) => {
      expect(css).toContain(hex)
    },
  )

  it('declares no serif font family anywhere', () => {
    // Matches a bare "serif" that is not part of "sans-serif" (v1 §3 Rule 1
    // bans serif outright on dashboard/software UI; "no serif anywhere" is
    // a CLAUDE.md / ARCHITECTURE §8 requirement, not a preference).
    const bareSerif = /(?<!sans-)serif/gi
    expect(cssDeclarations.match(bareSerif)).toBeNull()
  })

  it('self-hosts Geist and Geist Mono via @font-face, not a third-party CDN', () => {
    expect(css).toMatch(/@font-face/)
    expect(css).toContain("font-family: 'Geist'")
    expect(css).toContain("font-family: 'Geist Mono'")
    expect(css).not.toMatch(/fonts\.googleapis\.com/)
    expect(css).not.toMatch(/fonts\.gstatic\.com/)
  })

  it('provides a mono utility for numerals so widths do not jitter', () => {
    expect(css).toMatch(/\.mono-num/)
    expect(css).toMatch(/--font-mono/)
  })

  it('exposes the standard easing curve and a 150-200ms duration range', () => {
    expect(css).toContain('cubic-bezier(0.16, 1, 0.3, 1)')
    // Every declared --duration-* token must fall inside 150-200ms.
    const durations = [...css.matchAll(/--duration-[\w-]+:\s*(\d+)ms/g)].map(
      (m) => Number(m[1]),
    )
    expect(durations.length).toBeGreaterThan(0)
    for (const ms of durations) {
      expect(ms).toBeGreaterThanOrEqual(150)
      expect(ms).toBeLessThanOrEqual(200)
    }
  })

  it('respects prefers-reduced-motion by reducing durations to near-zero', () => {
    expect(css).toMatch(/prefers-reduced-motion:\s*reduce/)
  })

  it('never uses a pure-black rgba(0, 0, 0, ...) shadow', () => {
    expect(cssDeclarations).not.toMatch(/rgba\(\s*0,\s*0,\s*0,/)
  })

  it('sets light mode as the default palette (no dark-only :root)', () => {
    // The unconditional :root block must come before the
    // prefers-color-scheme: dark override, and must itself carry the light
    // background value rather than the dark one.
    const rootIndex = css.indexOf(':root {')
    const darkMediaIndex = css.indexOf('prefers-color-scheme: dark')
    expect(rootIndex).toBeGreaterThanOrEqual(0)
    expect(darkMediaIndex).toBeGreaterThan(rootIndex)
    const unconditionalRoot = css.slice(rootIndex, darkMediaIndex)
    expect(unconditionalRoot).toContain('#FBFBFA')
  })
})

describe('motion tokens — the duration namespace trap', () => {
  // Verified empirically 2026-07-31 by building a probe component and
  // grepping the emitted CSS: `ease-standard` is generated (--ease-* IS a
  // Tailwind v4 theme namespace) but `duration-standard` is NOT (there is no
  // --duration-* namespace; the utility takes a bare number). An element
  // written `duration-standard` gets no transition duration and no error,
  // which is the silent kind of wrong. This guards story 1.6 and after.
  // Comments stripped for the same reason cssDeclarations exists above: the
  // index.css comment documenting this trap names `duration-standard` in
  // prose, and a check that reads prose instead of code flags the very
  // warning that prevents the bug.
  const sourceFiles = globSync('**/*.{ts,tsx,css}', { cwd: here })
    .filter((f) => !f.endsWith('index.css.test.ts'))
    .map((f) => ({
      file: f,
      text: readFileSync(path.join(here, f), 'utf-8')
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/^\s*\/\/.*$/gm, ''),
    }))

  it('never uses the bare duration-<token> utility, which emits nothing', () => {
    const offenders = sourceFiles
      // (?<!-) excludes the token declarations themselves (`--duration-fast:`)
      // and the correct arbitrary form (`duration-(--duration-standard)`),
      // both of which carry a hyphen immediately before `duration`. Only a
      // bare utility class matches.
      .filter(({ text }) => /(?<!-)\bduration-(fast|standard|slow)\b/.test(text))
      .map(({ file }) => file)
    expect(
      offenders,
      'use duration-(--duration-standard), not duration-standard',
    ).toEqual([])
  })
})

describe('package.json — icon library guard', () => {
  it('never depends on lucide-react, directly or otherwise', () => {
    expect(packageJson).not.toMatch(/lucide-react/)
  })

  it('depends on @phosphor-icons/react', () => {
    expect(packageJson).toMatch(/@phosphor-icons\/react/)
  })
})

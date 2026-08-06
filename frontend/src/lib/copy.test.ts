import { describe, expect, it } from 'vitest'
import { stripDashes } from './copy'

describe('stripDashes', () => {
  it('passes text with no dashes through byte-identical', () => {
    const text = 'The candidate owned the payouts reconciliation surface end to end.'
    expect(stripDashes(text)).toBe(text)
  })

  it('turns an en-dash between two digits into "to", not a comma', () => {
    expect(stripDashes('Grew the team from 2016–2019.')).toBe('Grew the team from 2016 to 2019.')
  })

  it('handles a digit range with whitespace around the en-dash', () => {
    expect(stripDashes('Ship in 5 – 7 days.')).toBe('Ship in 5 to 7 days.')
  })

  it('turns any other em-dash, with its surrounding whitespace, into a comma', () => {
    expect(stripDashes('The team pivoted — quickly.')).toBe('The team pivoted, quickly.')
  })

  it('turns any other en-dash, with its surrounding whitespace, into a comma', () => {
    expect(stripDashes('Good – but risky.')).toBe('Good, but risky.')
  })

  // --- the other five dash-family characters (U+2010, U+2011, U+2012,
  // U+2015, U+2212) -- the defect this suite exists to close. Fixed
  // 2026-08-06 after a U+2011 non-breaking hyphen reached a live,
  // candidate-facing probe and crashed a console print with
  // UnicodeEncodeError.

  it('normalises a hyphen (U+2010) to an ASCII hyphen, not a comma', () => {
    expect(stripDashes('co‐founder')).toBe('co-founder')
  })

  it('normalises a non-breaking hyphen (U+2011) to an ASCII hyphen, not a comma', () => {
    expect(stripDashes('well‑known')).toBe('well-known')
  })

  it('normalises a minus sign (U+2212) to an ASCII hyphen, not a comma', () => {
    expect(stripDashes('the delta was −5 points')).toBe('the delta was -5 points')
  })

  it('turns a figure dash (U+2012) between two digits into "to"', () => {
    expect(stripDashes('Grew the team from 2016‒2019.')).toBe(
      'Grew the team from 2016 to 2019.',
    )
  })

  it('turns any other figure dash (U+2012), with its surrounding whitespace, into a comma', () => {
    expect(stripDashes('The team pivoted‒quickly.')).toBe('The team pivoted, quickly.')
  })

  it('turns a horizontal bar (U+2015) between two digits into "to"', () => {
    expect(stripDashes('Ship in 5―7 days.')).toBe('Ship in 5 to 7 days.')
  })

  it('turns any other horizontal bar (U+2015), with its surrounding whitespace, into a comma', () => {
    expect(stripDashes('Good―but risky.')).toBe('Good, but risky.')
  })

  // This is the case that makes the two-class split necessary: a naive fix
  // that widened the comma rule to all seven characters (rather than
  // splitting hyphen-like from aside/range) would turn this into
  // "state, of, the, art" or similar -- clearly worse than leaving it
  // alone. The non-breaking hyphen must survive as an ASCII hyphen and the
  // result must gain zero commas.
  it('normalises "state-of-the-art" written with non-breaking hyphens to ASCII hyphens, never a comma', () => {
    const result = stripDashes('state‑of‑the‑art')
    expect(result).toBe('state-of-the-art')
    expect(result).not.toContain(',')
  })

  it('collapses an inserted comma that lands right before other punctuation', () => {
    expect(stripDashes('It worked—.')).toBe('It worked.')
    expect(stripDashes('It worked—,')).toBe('It worked,')
    expect(stripDashes('It worked—;')).toBe('It worked;')
  })

  it('collapses whitespace runs left over after substitution', () => {
    expect(stripDashes('Good  work — really')).toBe('Good work, really')
  })

  it('trims the result', () => {
    expect(stripDashes('  padded on both sides  ')).toBe('padded on both sides')
  })
})

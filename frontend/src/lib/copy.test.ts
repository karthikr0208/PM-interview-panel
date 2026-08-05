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

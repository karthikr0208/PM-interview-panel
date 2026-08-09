import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { EvaluationColumn } from './EvaluationColumn'
import type { AnswerEvaluation } from '../lib/types'

afterEach(cleanup)

// Same mocking style as OrchestrationColumn.test.tsx: the hook is stubbed so
// this file is about what the column RENDERS, and lib/evaluations.test.ts
// owns the fetch/subscribe/reduce behaviour.
const { useEvaluations, retry } = vi.hoisted(() => ({
  useEvaluations: vi.fn(),
  retry: vi.fn(),
}))
vi.mock('../lib/evaluations', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/evaluations')>()
  return { ...actual, useEvaluations }
})

function evaluation(overrides: Partial<AnswerEvaluation> = {}): AnswerEvaluation {
  return {
    id: 'eval-1',
    session_id: 'sess-1',
    turn_idx: 0,
    dimension: 'market_accuracy',
    score: 3,
    evidence_quote: 'Their churn sits in the self serve tier, not in enterprise.',
    reasoning: null,
    ...overrides,
  }
}

function ready(rows: AnswerEvaluation[]) {
  useEvaluations.mockReturnValue({ state: { kind: 'ready', rows }, retry })
}

// Every assertion is scoped to ONE row by its accessible name -- five rows
// always render, so an unscoped query could pass against the wrong dimension.
function row(name: string) {
  return screen.getByRole('listitem', { name })
}

const ALL_FIVE: AnswerEvaluation[] = [
  evaluation({ id: 'a', dimension: 'business_model_fluency', score: 3 }),
  evaluation({ id: 'b', dimension: 'market_accuracy', score: 2 }),
  evaluation({ id: 'c', dimension: 'decision_quality', score: 4 }),
  evaluation({ id: 'd', dimension: 'structural_clarity', score: 3 }),
  evaluation({ id: 'e', dimension: 'point_of_view', score: 2 }),
]

describe('EvaluationColumn', () => {
  beforeEach(() => {
    useEvaluations.mockReset()
    retry.mockReset()
  })

  it('renders all five dimensions in PRD order even when only two have data', () => {
    ready([
      evaluation({ id: 'a', dimension: 'point_of_view', score: 2 }),
      evaluation({ id: 'b', dimension: 'market_accuracy', score: 3 }),
    ])
    render(<EvaluationColumn sessionId="sess-1" />)

    const names = screen.getAllByRole('listitem').map((el) => el.getAttribute('aria-label'))
    expect(names).toEqual([
      'Business model fluency',
      'Market accuracy',
      'Decision quality',
      'Structural clarity',
      'Point of view',
    ])
  })

  it('shows the number for a scored dimension, always visible and in mono', () => {
    ready([evaluation({ dimension: 'market_accuracy', score: 3 })])
    render(<EvaluationColumn sessionId="sess-1" />)

    const scored = within(row('Market accuracy')).getByText('3 / 4')
    // PRD §8: mono for every number, and the value is never hover-only.
    expect(scored.className).toContain('font-mono')
  })

  it('fills the bar up to the score, and no further', () => {
    ready([
      evaluation({ id: 'a', dimension: 'market_accuracy', score: 3 }),
      evaluation({ id: 'b', dimension: 'decision_quality', score: 1 }),
    ])
    render(<EvaluationColumn sessionId="sess-1" />)

    expect(row('Market accuracy').querySelectorAll('[data-filled="true"]')).toHaveLength(3)
    expect(row('Market accuracy').querySelectorAll('[data-filled="false"]')).toHaveLength(1)
    expect(row('Decision quality').querySelectorAll('[data-filled="true"]')).toHaveLength(1)
  })

  it('expands a row to its verbatim evidence quote', () => {
    const quote = 'Their churn sits in the self serve tier, not in enterprise.'
    ready([evaluation({ dimension: 'market_accuracy', evidence_quote: quote })])
    render(<EvaluationColumn sessionId="sess-1" />)

    const details = row('Market accuracy').querySelector('details') as HTMLDetailsElement
    // Starts collapsed, and the quote lives INSIDE the disclosure rather than
    // beside it -- a component that printed the quote unconditionally would
    // pass a text-only assertion.
    expect(details.open).toBe(false)
    expect(within(details).getByText(quote)).toBeTruthy()

    fireEvent.click(details.querySelector('summary') as HTMLElement)
    expect(details.open).toBe(true)
  })

  it('shows the reasoning when there is one, and nothing in its place when there is not', () => {
    ready([evaluation({ dimension: 'market_accuracy', reasoning: 'Named the segment and the driver.' })])
    const { unmount } = render(<EvaluationColumn sessionId="sess-1" />)
    expect(within(row('Market accuracy')).getByText('Named the segment and the driver.')).toBeTruthy()
    expect(within(row('Market accuracy')).getByText('Why this score')).toBeTruthy()
    unmount()

    ready([evaluation({ dimension: 'market_accuracy', reasoning: null })])
    render(<EvaluationColumn sessionId="sess-1" />)
    expect(within(row('Market accuracy')).queryByText('Why this score')).toBeNull()
  })

  it('renders a NOT ASSESSED dimension with no numeral at all, and not expandable', () => {
    ready([evaluation({ dimension: 'market_accuracy', score: 3 })])
    render(<EvaluationColumn sessionId="sess-1" />)

    const unassessed = row('Point of view')
    // Positive: it says so in words.
    expect(within(unassessed).getByText('Not assessed')).toBeTruthy()
    // Negative: no digit anywhere in the row, so it can never read as a zero
    // or as a score of 1.
    expect(unassessed.textContent ?? '').not.toMatch(/\d/)
    // Distinguishable from a score of 1 by SHAPE, not only by colour: the
    // unassessed track is dashed and has no filled segment.
    expect(unassessed.querySelectorAll('[data-track="dashed"]')).toHaveLength(4)
    expect(unassessed.querySelectorAll('[data-filled="true"]')).toHaveLength(0)
    // There is no quote behind it, so there is no disclosure to open.
    expect(unassessed.querySelector('details')).toBeNull()

    // Control: the scored row in the same render IS expandable and IS solid.
    expect(row('Market accuracy').querySelector('details')).not.toBeNull()
    expect(row('Market accuracy').querySelectorAll('[data-track="solid"]')).toHaveLength(4)
  })

  it('SUPPRESSES the overall score while any dimension is unassessed, and shows coverage instead', () => {
    ready([
      evaluation({ id: 'a', dimension: 'business_model_fluency', score: 3 }),
      evaluation({ id: 'b', dimension: 'market_accuracy', score: 2 }),
      evaluation({ id: 'c', dimension: 'decision_quality', score: 4 }),
    ])
    render(<EvaluationColumn sessionId="sess-1" />)

    const text = document.body.textContent ?? ''
    // POSITIVE first, so the absence assertion below cannot pass vacuously
    // against a blank component.
    expect(text).toContain('3 of 5 dimensions assessed')
    expect(text).not.toContain('Overall')
  })

  it('shows an overall only once all five dimensions are scored', () => {
    ready(ALL_FIVE)
    render(<EvaluationColumn sessionId="sess-1" />)

    // 3 + 2 + 4 + 3 + 2 = 14, over five dimensions.
    expect(document.body.textContent ?? '').toContain('Overall 2.8 / 4')
  })

  it('blind mode hides the numbers and the fills, and leaves coverage', () => {
    ready(ALL_FIVE)
    render(<EvaluationColumn sessionId="sess-1" />)

    const toggle = screen.getByRole('button', { name: /blind mode/i })
    expect(toggle.getAttribute('aria-pressed')).toBe('false')
    expect(document.body.textContent ?? '').toContain('Overall 2.8 / 4')

    fireEvent.click(toggle)

    expect(toggle.getAttribute('aria-pressed')).toBe('true')
    const text = document.body.textContent ?? ''
    expect(text).not.toContain('Overall')
    expect(text).not.toContain('3 / 4')
    // Coverage and progress are what blind mode is allowed to show.
    expect(text).toContain('5 of 5 dimensions assessed')
    expect(within(row('Market accuracy')).getByText('Assessed')).toBeTruthy()
    expect(document.querySelectorAll('[data-filled="true"]')).toHaveLength(0)
  })

  it('`revealed` forces the numbers back regardless of the toggle', () => {
    ready(ALL_FIVE)
    const { rerender } = render(<EvaluationColumn sessionId="sess-1" />)
    fireEvent.click(screen.getByRole('button', { name: /blind mode/i }))
    expect(document.body.textContent ?? '').not.toContain('Overall')

    rerender(<EvaluationColumn sessionId="sess-1" revealed />)

    const text = document.body.textContent ?? ''
    expect(text).toContain('Overall 2.8 / 4')
    expect(within(row('Market accuracy')).getByText('2 / 4')).toBeTruthy()
  })

  it('strips a raw U+2011 out of an evidence quote before it reaches the DOM', () => {
    // Rows written before 2026-08-07 carry the non-breaking hyphen raw, and
    // this column renders historical transcripts.
    ready([
      evaluation({
        dimension: 'market_accuracy',
        evidence_quote: 'The self‑serve tier churns hardest.',
        reasoning: 'A go‑to‑market answer, not a pricing one.',
      }),
    ])
    render(<EvaluationColumn sessionId="sess-1" />)

    const text = document.body.textContent ?? ''
    expect(text).not.toContain('‑')
    // Positive control: the sentence is still there, normalised, rather than
    // dropped outright.
    expect(text).toContain('The self-serve tier churns hardest.')
    expect(text).toContain('A go-to-market answer, not a pricing one.')
  })

  it('has no em-dash or en-dash in any candidate-facing copy', () => {
    ready(ALL_FIVE)
    render(<EvaluationColumn sessionId="sess-1" />)
    expect(document.body.textContent ?? '').not.toMatch(/[—–]/)
  })

  it('renders a loading state', () => {
    useEvaluations.mockReturnValue({ state: { kind: 'loading' }, retry })
    render(<EvaluationColumn sessionId="sess-1" />)
    expect(screen.getByRole('status')).toBeTruthy()
    expect(screen.getByText(/loading your scorecard/i)).toBeTruthy()
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
  })

  it('renders an empty state that is not an error', () => {
    useEvaluations.mockReturnValue({ state: { kind: 'empty' }, retry })
    render(<EvaluationColumn sessionId="sess-1" />)
    expect(screen.getByText(/nothing scored yet/i)).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('renders an error state and wires the retry the hook returns', () => {
    useEvaluations.mockReturnValue({
      state: { kind: 'error', message: 'Could not load your scorecard.' },
      retry,
    })
    render(<EvaluationColumn sessionId="sess-1" />)

    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText('Could not load your scorecard.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(retry).toHaveBeenCalledTimes(1)
  })
})

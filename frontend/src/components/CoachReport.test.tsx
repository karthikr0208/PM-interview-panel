import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { CoachReport } from './CoachReport'
import type { CoachImprovement } from '../lib/types'

afterEach(cleanup)

// Same mocking style as EvaluationColumn.test.tsx: the hook is stubbed so
// this file is about what the component RENDERS, and lib/coachReport.test.ts
// owns the fetch/subscribe/reduce behaviour.
const { useCoachReport, retry } = vi.hoisted(() => ({
  useCoachReport: vi.fn(),
  retry: vi.fn(),
}))
vi.mock('../lib/coachReport', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/coachReport')>()
  return { ...actual, useCoachReport }
})

function moment(overrides: Partial<CoachImprovement> = {}): CoachImprovement {
  return {
    id: 'imp-moment',
    session_id: 'sess-1',
    idx: 0,
    kind: 'moment',
    anchor_quote: 'We should exit the SMB tier because the CAC never pays back.',
    dimension: null,
    stronger_version: 'Name the payback period, not just the direction of the call.',
    drill: 'Practice stating the number before the recommendation.',
    created_at: '2026-08-11T00:00:00Z',
    ...overrides,
  }
}

function gap(overrides: Partial<CoachImprovement> = {}): CoachImprovement {
  return {
    id: 'imp-gap',
    session_id: 'sess-1',
    idx: 1,
    kind: 'gap',
    anchor_quote: null,
    dimension: 'market_accuracy',
    stronger_version: 'Size the market before proposing where to play in it.',
    drill: 'Practice a thirty second market sizing before every recommendation.',
    created_at: '2026-08-11T00:00:00Z',
    ...overrides,
  }
}

function ready(improvements: CoachImprovement[]) {
  useCoachReport.mockReturnValue({ state: { kind: 'ready', improvements }, retry })
}

describe('CoachReport', () => {
  beforeEach(() => {
    useCoachReport.mockReset()
    retry.mockReset()
  })

  it('renders three improvements in idx order', () => {
    ready([
      moment({ id: 'a', idx: 2, stronger_version: 'Third item.' }),
      moment({ id: 'b', idx: 0, stronger_version: 'First item.' }),
      gap({ id: 'c', idx: 1, stronger_version: 'Second item.' }),
    ])
    render(<CoachReport sessionId="sess-1" />)

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(within(items[0]).getByText('First item.')).toBeTruthy()
    expect(within(items[1]).getByText('Second item.')).toBeTruthy()
    expect(within(items[2]).getByText('Third item.')).toBeTruthy()
  })

  it('numbers the items in mono', () => {
    ready([moment({ idx: 0 }), gap({ idx: 1 }), moment({ id: 'c', idx: 2 })])
    render(<CoachReport sessionId="sess-1" />)

    const items = screen.getAllByRole('listitem')
    const first = items[0].querySelector('span')
    expect(first?.textContent).toBe('1')
    expect(first?.className).toContain('font-mono')
  })

  it('a MOMENT renders the candidate\'s own words', () => {
    const quote = 'We should exit the SMB tier because the CAC never pays back.'
    ready([moment({ anchor_quote: quote })])
    render(<CoachReport sessionId="sess-1" />)

    expect(screen.getByText(quote)).toBeTruthy()
    expect(screen.getByText('What you said')).toBeTruthy()
  })

  it('a GAP renders its dimension\'s human label and renders NO quote element', () => {
    ready([gap({ dimension: 'market_accuracy' })])
    render(<CoachReport sessionId="sess-1" />)

    // Positive: the human label, matching EvaluationColumn's own label for
    // the same dimension string.
    expect(screen.getByText('Market accuracy')).toBeTruthy()
    expect(screen.getByText('Never came up')).toBeTruthy()
    // Negative: no "What you said" heading and no <blockquote> anywhere --
    // there is no quote of a thing the candidate never said.
    expect(screen.queryByText('What you said')).toBeNull()
    expect(document.querySelector('blockquote')).toBeNull()
  })

  it('both kinds still show the stronger version and the drill', () => {
    ready([moment(), gap()])
    render(<CoachReport sessionId="sess-1" />)

    const items = screen.getAllByRole('listitem')
    expect(within(items[0]).getByText('A stronger version')).toBeTruthy()
    expect(within(items[0]).getByText('Try this')).toBeTruthy()
    expect(within(items[1]).getByText('A stronger version')).toBeTruthy()
    expect(within(items[1]).getByText('Try this')).toBeTruthy()
  })

  it('renders a loading state', () => {
    useCoachReport.mockReturnValue({ state: { kind: 'loading' }, retry })
    render(<CoachReport sessionId="sess-1" />)
    expect(screen.getByRole('status')).toBeTruthy()
    expect(screen.getByText(/loading your coaching notes/i)).toBeTruthy()
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
  })

  it('renders an empty state that is not an error, with honest specific copy', () => {
    useCoachReport.mockReturnValue({ state: { kind: 'empty' }, retry })
    render(<CoachReport sessionId="sess-1" />)
    expect(screen.getByText('Your coaching notes appear when the interview ends.')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('renders an error state and wires the retry the hook returns', () => {
    useCoachReport.mockReturnValue({
      state: { kind: 'error', message: 'Could not load your coaching notes.' },
      retry,
    })
    render(<CoachReport sessionId="sess-1" />)

    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText('Could not load your coaching notes.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(retry).toHaveBeenCalledTimes(1)
  })

  it('strips a raw dash out of stored prose before it reaches the DOM', () => {
    // Rows written before the normalisation shipped can carry raw dash-family
    // characters, same trap EvaluationColumn.test.tsx guards against.
    ready([
      moment({
        stronger_version: 'Name the payback period — not just the direction of the call.',
        drill: 'Practice the number — then the recommendation.',
      }),
    ])
    render(<CoachReport sessionId="sess-1" />)

    const text = document.body.textContent ?? ''
    expect(text).not.toContain('—')
    // Positive control: the sentence is still there, normalised, rather than
    // dropped outright.
    expect(text).toContain('Name the payback period, not just the direction of the call.')
    expect(text).toContain('Practice the number, then the recommendation.')
  })

  it('has no em-dash or en-dash in any candidate-facing copy', () => {
    ready([moment(), gap()])
    render(<CoachReport sessionId="sess-1" />)
    expect(document.body.textContent ?? '').not.toMatch(/[—–]/)
  })
})

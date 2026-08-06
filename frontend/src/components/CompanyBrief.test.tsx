import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { CompanyBrief } from './CompanyBrief'
import type { CaseWorldState } from '../lib/caseWorld'
import type { CaseWorld } from '../lib/types'

afterEach(cleanup)

function noop() {}

function makeWorld(overrides: Partial<CaseWorld> = {}): CaseWorld {
  return {
    company: {
      name: 'Reddit',
      one_line: 'Reddit runs a network of community-run discussion forums, monetized through ads and content licensing.',
      stage: 'public',
      employees: 2000,
      founded_year: 2005,
    },
    market: {
      description: 'Online social and community platforms.',
      size_usd: '$740.3B',
      growth_rate_pct: 10.7,
      competitors: [],
    },
    metrics: {
      arr_usd: '$1.3B',
      yoy_growth_pct: 62.0,
      gross_margin_pct: 88.4,
      monthly_churn_pct: 4.1,
      customer_count: 110000000,
    },
    situation: {
      prompt: 'How should Reddit balance licensing against direct traffic?',
      tension: 'The two revenue lines may work against each other.',
      options: ['Lean into licensing', 'Restrict and gate', 'Build the answer layer'],
      constraints: ['Public-company reporting'],
      leadership_belief: 'Leadership frames the two as complementary.',
    },
    supporting_facts: ['Reddit went public on the NYSE in March 2024.'],
    as_of: 'August 2025',
    suits_categories: ['strategy', 'gtm', 'growth'],
    ...overrides,
  }
}

describe('CompanyBrief', () => {
  it('shows a skeletal loading state, never a spinner', () => {
    const state: CaseWorldState = { kind: 'loading' }
    render(<CompanyBrief state={state} onRetry={noop} />)
    expect(screen.getByRole('status')).toBeTruthy()
    expect(screen.queryByRole('progressbar')).toBeNull()
  })

  it('shows an explicit empty state when no brief exists for the session', () => {
    const state: CaseWorldState = { kind: 'empty' }
    render(<CompanyBrief state={state} onRetry={noop} />)
    expect(screen.getByText(/no company brief is available/i)).toBeTruthy()
  })

  it('shows the server error message and lets the candidate retry', () => {
    const state: CaseWorldState = { kind: 'error', message: 'Could not load the company brief.' }
    const onRetry = vi.fn()
    render(<CompanyBrief state={state} onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText('Could not load the company brief.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('shows the company name, what it sells, and the as_of line', () => {
    const state: CaseWorldState = { kind: 'ready', world: makeWorld() }
    render(<CompanyBrief state={state} onRetry={noop} />)
    expect(screen.getByText('Reddit')).toBeTruthy()
    expect(screen.getByText(/community-run discussion forums/i)).toBeTruthy()
    expect(screen.getByText(/as of august 2025/i)).toBeTruthy()
  })

  // The acceptance box: "the candidate can re-read it without losing their
  // place" -- collapsing must not unmount the brief's own data. One click
  // hides the detail, a second click brings back the SAME text, not a
  // re-fetch.
  it('collapses and re-expands without losing the brief text', () => {
    const state: CaseWorldState = { kind: 'ready', world: makeWorld() }
    render(<CompanyBrief state={state} onRetry={noop} />)

    const toggle = screen.getByRole('button', { name: /reddit/i })
    fireEvent.click(toggle)
    expect(screen.queryByText(/community-run discussion forums/i)).toBeNull()

    fireEvent.click(toggle)
    expect(screen.getByText(/community-run discussion forums/i)).toBeTruthy()
  })
})

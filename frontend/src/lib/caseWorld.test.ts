import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { CaseWorld } from './types'

// Mocked so this never touches real Supabase (same pattern as
// lib/agentEvents.test.ts). vi.mock factories are hoisted above imports, so
// the state they close over is created via vi.hoisted.
const { state, fromMock, maybeSingle } = vi.hoisted(() => {
  return {
    state: {
      data: null as { world: CaseWorld } | null,
      error: null as { message: string } | null,
    },
    fromMock: vi.fn(),
    maybeSingle: vi.fn(),
  }
})

vi.mock('./supabase', () => {
  const queryBuilder = {
    eq: vi.fn(() => queryBuilder),
    maybeSingle: (...args: unknown[]) => {
      maybeSingle(...args)
      return Promise.resolve({ data: state.data, error: state.error })
    },
  }
  fromMock.mockImplementation(() => ({ select: vi.fn(() => queryBuilder) }))
  return { supabase: { from: fromMock } }
})

const { useCaseWorld } = await import('./caseWorld')

function makeWorld(overrides: Partial<CaseWorld> = {}): CaseWorld {
  return {
    company: {
      name: 'Reddit',
      one_line: 'Reddit runs a network of community-run discussion forums.',
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

describe('useCaseWorld', () => {
  beforeEach(() => {
    state.data = null
    state.error = null
    fromMock.mockClear()
    maybeSingle.mockClear()
  })

  it('starts in "empty" and queries nothing when there is no session yet', () => {
    const { result } = renderHook(() => useCaseWorld(null))
    expect(result.current.state).toEqual({ kind: 'empty' })
    expect(fromMock).not.toHaveBeenCalled()
  })

  it('starts "loading" then resolves to "ready" with the fetched world', async () => {
    state.data = { world: makeWorld() }
    const { result } = renderHook(() => useCaseWorld('sess-1'))

    expect(result.current.state).toEqual({ kind: 'loading' })
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    expect(result.current.state).toEqual({ kind: 'ready', world: makeWorld() })
    expect(fromMock).toHaveBeenCalledWith('case_worlds')
  })

  it('resolves to "empty" when no row exists for the session', async () => {
    state.data = null
    const { result } = renderHook(() => useCaseWorld('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('empty'))
  })

  it('resolves to "error" with a candidate-readable message when the query fails', async () => {
    state.error = { message: 'permission denied' }
    const { result } = renderHook(() => useCaseWorld('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('error'))
    expect(result.current.state).toEqual({
      kind: 'error',
      message: 'Could not load the company brief.',
    })
  })

  it('retry() re-queries after a failure', async () => {
    state.error = { message: 'network down' }
    const { result } = renderHook(() => useCaseWorld('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('error'))

    state.error = null
    state.data = { world: makeWorld() }
    act(() => {
      result.current.retry()
    })

    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
  })
})

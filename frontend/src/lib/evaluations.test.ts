import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { AnswerEvaluation } from './types'

// Mocked so this never touches real Supabase (same pattern as
// lib/agentEvents.test.ts). vi.mock factories are hoisted above imports, so
// the state they close over is created via vi.hoisted.
const { state, channelOn, channelSubscribe, removeChannel, fromMock } = vi.hoisted(() => {
  return {
    state: {
      selectData: [] as AnswerEvaluation[],
      selectError: null as { message: string } | null,
      handlers: [] as Array<(payload: { new: AnswerEvaluation }) => void>,
    },
    channelOn: vi.fn(),
    channelSubscribe: vi.fn(),
    removeChannel: vi.fn(),
    fromMock: vi.fn(),
  }
})

vi.mock('./supabase', () => {
  const queryBuilder = {
    eq: vi.fn(() => queryBuilder),
    order: vi.fn(() => queryBuilder),
    then: (
      resolve: (v: { data: AnswerEvaluation[] | null; error: { message: string } | null }) => void,
    ) => Promise.resolve({ data: state.selectData, error: state.selectError }).then(resolve),
  }
  const channel = {
    on: (...args: unknown[]) => {
      channelOn(...args)
      state.handlers.push(args[2] as (payload: { new: AnswerEvaluation }) => void)
      return channel
    },
    subscribe: (...args: unknown[]) => {
      channelSubscribe(...args)
      return channel
    },
  }
  fromMock.mockImplementation(() => ({ select: vi.fn(() => queryBuilder) }))
  return {
    supabase: {
      from: fromMock,
      channel: vi.fn(() => channel),
      removeChannel,
    },
  }
})

const { DIMENSIONS, highestPerDimension, useEvaluations } = await import('./evaluations')

function makeRow(overrides: Partial<AnswerEvaluation> = {}): AnswerEvaluation {
  return {
    id: 'eval-1',
    session_id: 'sess-1',
    turn_idx: 0,
    dimension: 'market_accuracy',
    score: 3,
    evidence_quote: 'Their churn is driven by the self serve tier, not enterprise.',
    reasoning: null,
    ...overrides,
  }
}

// ============================================================================
// The pure reduction. No React, no Supabase -- plain arrays in, standings out.
// ============================================================================
describe('highestPerDimension', () => {
  it('returns all five dimensions in PRD order, whatever order the rows arrive in', () => {
    const standings = highestPerDimension([
      makeRow({ id: 'a', dimension: 'point_of_view', score: 2 }),
      makeRow({ id: 'b', dimension: 'business_model_fluency', score: 4 }),
    ])
    expect(standings.map((s) => s.dimension)).toEqual([
      'business_model_fluency',
      'market_accuracy',
      'decision_quality',
      'structural_clarity',
      'point_of_view',
    ])
    expect(standings).toHaveLength(DIMENSIONS.length)
  })

  it('marks a dimension with NO ROW as not_assessed, never as a zero', () => {
    const standings = highestPerDimension([makeRow({ dimension: 'decision_quality', score: 1 })])
    const missing = standings.filter((s) => s.kind === 'not_assessed')
    expect(missing.map((s) => s.dimension)).toEqual([
      'business_model_fluency',
      'market_accuracy',
      'structural_clarity',
      'point_of_view',
    ])
    // The shape itself carries no score field. A regression that filled one
    // in with 0 would fail here rather than quietly rendering an empty bar.
    for (const standing of missing) {
      expect('evaluation' in standing).toBe(false)
    }
  })

  it('LETS THE HIGHEST SCORE WIN for a dimension scored more than once, even when it came earlier', () => {
    // A probe that goes worse than the opening answer must not erase the
    // stronger showing already on the record. If this reduced by latest
    // turn_idx instead, the later (weaker) row would win here.
    const standings = highestPerDimension([
      makeRow({ id: 'first', dimension: 'market_accuracy', turn_idx: 0, score: 4 }),
      makeRow({ id: 'later', dimension: 'market_accuracy', turn_idx: 4, score: 2 }),
    ])
    const market = standings.find((s) => s.dimension === 'market_accuracy')
    expect(market?.kind).toBe('scored')
    expect(market?.kind === 'scored' && market.evaluation.score).toBe(4)
    expect(market?.kind === 'scored' && market.evaluation.id).toBe('first')
  })

  it('sorts by turn_idx rather than trusting arrival order when comparing scores', () => {
    // Realtime delivers in insertion order, the fetch in query order, and the
    // two are merged. A reducer that just scanned the array in whatever order
    // it arrived could pick the wrong row on a tie (see the test below).
    const standings = highestPerDimension([
      makeRow({ id: 'later', dimension: 'decision_quality', turn_idx: 6, score: 1 }),
      makeRow({ id: 'earlier', dimension: 'decision_quality', turn_idx: 2, score: 4 }),
    ])
    const decision = standings.find((s) => s.dimension === 'decision_quality')
    expect(decision?.kind === 'scored' && decision.evaluation.id).toBe('earlier')
    expect(decision?.kind === 'scored' && decision.evaluation.score).toBe(4)
  })

  it('TIE-BREAKS TO THE EARLIER ROW when two rows score the same dimension identically', () => {
    const standings = highestPerDimension([
      makeRow({ id: 'earlier', dimension: 'structural_clarity', turn_idx: 1, score: 3 }),
      makeRow({ id: 'later', dimension: 'structural_clarity', turn_idx: 5, score: 3 }),
    ])
    const clarity = standings.find((s) => s.dimension === 'structural_clarity')
    expect(clarity?.kind === 'scored' && clarity.evaluation.id).toBe('earlier')
    // Same result regardless of the array's arrival order.
    const reversed = highestPerDimension([
      makeRow({ id: 'later', dimension: 'structural_clarity', turn_idx: 5, score: 3 }),
      makeRow({ id: 'earlier', dimension: 'structural_clarity', turn_idx: 1, score: 3 }),
    ])
    const clarityReversed = reversed.find((s) => s.dimension === 'structural_clarity')
    expect(clarityReversed?.kind === 'scored' && clarityReversed.evaluation.id).toBe('earlier')
  })

  it('the evidence_quote and reasoning on the winning standing come from the WINNING ROW, never a different one', () => {
    // The named trap: a score traced to a sentence that did not earn it would
    // break the product's central promise. Two rows for the same dimension,
    // each with its own quote -- the higher-scoring row's own quote must be
    // the one that surfaces, not the other row's, and not some third value.
    const standings = highestPerDimension([
      makeRow({
        id: 'weak',
        dimension: 'point_of_view',
        turn_idx: 0,
        score: 1,
        evidence_quote: 'It depends on a lot of factors.',
        reasoning: 'Restates the prompt, no thesis.',
      }),
      makeRow({
        id: 'strong',
        dimension: 'point_of_view',
        turn_idx: 3,
        score: 4,
        evidence_quote: 'We should exit the SMB tier because the CAC never pays back.',
        reasoning: 'Defensible thesis, sharpened under pushback.',
      }),
    ])
    const pov = standings.find((s) => s.dimension === 'point_of_view')
    expect(pov?.kind === 'scored' && pov.evaluation.id).toBe('strong')
    expect(pov?.kind === 'scored' && pov.evaluation.score).toBe(4)
    expect(pov?.kind === 'scored' && pov.evaluation.evidence_quote).toBe(
      'We should exit the SMB tier because the CAC never pays back.',
    )
    expect(pov?.kind === 'scored' && pov.evaluation.reasoning).toBe(
      'Defensible thesis, sharpened under pushback.',
    )
  })

  it('ignores a dimension name the rubric does not contain', () => {
    const standings = highestPerDimension([makeRow({ dimension: 'vibes', score: 4 })])
    expect(standings.every((s) => s.kind === 'not_assessed')).toBe(true)
  })
})

// ============================================================================
// The hook.
// ============================================================================
describe('useEvaluations', () => {
  beforeEach(() => {
    state.selectData = []
    state.selectError = null
    state.handlers = []
    channelOn.mockClear()
    channelSubscribe.mockClear()
    removeChannel.mockClear()
    fromMock.mockClear()
  })

  it('starts in "empty" and queries nothing when there is no session yet', () => {
    const { result } = renderHook(() => useEvaluations(null))
    expect(result.current.state).toEqual({ kind: 'empty' })
    expect(fromMock).not.toHaveBeenCalled()
  })

  it('starts "loading" then resolves to "ready" with the fetched rows', async () => {
    state.selectData = [makeRow({ id: 'eval-1' })]
    const { result } = renderHook(() => useEvaluations('sess-1'))

    expect(result.current.state).toEqual({ kind: 'loading' })
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    expect(result.current.state.kind === 'ready' && result.current.state.rows).toHaveLength(1)
    expect(fromMock).toHaveBeenCalledWith('answer_evaluations')
  })

  it('resolves to "empty", NOT "error", when the session has no scores yet', async () => {
    // The distinction lib/caseWorld.ts spells out. Collapsing the two would
    // show a candidate an error banner for the whole first question.
    state.selectData = []
    const { result } = renderHook(() => useEvaluations('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('empty'))
  })

  it('resolves to "error" with a candidate-readable message when the query fails', async () => {
    state.selectError = { message: 'permission denied' }
    const { result } = renderHook(() => useEvaluations('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('error'))
    expect(result.current.state).toEqual({
      kind: 'error',
      message: 'Could not load your scorecard.',
    })
  })

  it('subscribes via postgres_changes INSERT filtered to the session, not a poll', async () => {
    renderHook(() => useEvaluations('sess-1'))
    await waitFor(() => expect(channelSubscribe).toHaveBeenCalled())

    expect(channelOn).toHaveBeenCalledWith(
      'postgres_changes',
      expect.objectContaining({
        event: 'INSERT',
        schema: 'public',
        table: 'answer_evaluations',
        filter: 'session_id=eq.sess-1',
      }),
      expect.any(Function),
    )
  })

  it('promotes "empty" to "ready" when a score arrives over realtime', async () => {
    const { result } = renderHook(() => useEvaluations('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('empty'))

    act(() => {
      state.handlers.forEach((handler) => handler({ new: makeRow({ id: 'live-1' }) }))
    })

    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    expect(result.current.state.kind === 'ready' && result.current.state.rows[0].id).toBe('live-1')
  })

  it('does not duplicate a row the realtime channel redelivers', async () => {
    state.selectData = [makeRow({ id: 'eval-1' })]
    const { result } = renderHook(() => useEvaluations('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))

    act(() => {
      state.handlers.forEach((handler) => handler({ new: makeRow({ id: 'eval-1' }) }))
    })

    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(result.current.state.kind === 'ready' && result.current.state.rows).toHaveLength(1)
  })

  it('retry() re-queries after a failure', async () => {
    state.selectError = { message: 'network down' }
    const { result } = renderHook(() => useEvaluations('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('error'))

    state.selectError = null
    state.selectData = [makeRow()]
    act(() => {
      result.current.retry()
    })

    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
  })

  it('unsubscribes on unmount', async () => {
    const { unmount } = renderHook(() => useEvaluations('sess-1'))
    await waitFor(() => expect(channelSubscribe).toHaveBeenCalled())

    unmount()
    expect(removeChannel).toHaveBeenCalledTimes(1)
  })
})

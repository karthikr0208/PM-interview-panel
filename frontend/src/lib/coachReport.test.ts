import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { CoachImprovement } from './types'

// Mocked so this never touches real Supabase, same pattern as
// lib/evaluations.test.ts. vi.mock factories are hoisted above imports, so
// the state they close over is created via vi.hoisted.
const { state, channelOn, channelSubscribe, removeChannel, fromMock } = vi.hoisted(() => {
  return {
    state: {
      selectData: [] as CoachImprovement[],
      selectError: null as { message: string } | null,
      handlers: [] as Array<(payload: { new: CoachImprovement }) => void>,
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
      resolve: (v: { data: CoachImprovement[] | null; error: { message: string } | null }) => void,
    ) => Promise.resolve({ data: state.selectData, error: state.selectError }).then(resolve),
  }
  const channel = {
    on: (...args: unknown[]) => {
      channelOn(...args)
      state.handlers.push(args[2] as (payload: { new: CoachImprovement }) => void)
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

const { useCoachReport } = await import('./coachReport')

function makeRow(overrides: Partial<CoachImprovement> = {}): CoachImprovement {
  return {
    id: 'imp-1',
    session_id: 'sess-1',
    idx: 0,
    kind: 'moment',
    anchor_quote: 'We should exit the SMB tier because the CAC never pays back.',
    dimension: null,
    stronger_version: 'Name the metric that made the call, not just the call.',
    drill: 'Practice stating the number before the recommendation.',
    created_at: '2026-08-11T00:00:00Z',
    ...overrides,
  }
}

describe('useCoachReport', () => {
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
    const { result } = renderHook(() => useCoachReport(null))
    expect(result.current.state).toEqual({ kind: 'empty' })
    expect(fromMock).not.toHaveBeenCalled()
  })

  it('starts "loading" then resolves to "ready" with the fetched rows, ordered by idx', async () => {
    state.selectData = [makeRow({ id: 'imp-1', idx: 0 })]
    const { result } = renderHook(() => useCoachReport('sess-1'))

    expect(result.current.state).toEqual({ kind: 'loading' })
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    expect(result.current.state.kind === 'ready' && result.current.state.improvements).toHaveLength(1)
    expect(fromMock).toHaveBeenCalledWith('coach_reports')
  })

  it('resolves to "empty", NOT "error", when the Coach has not run yet', async () => {
    // The distinction lib/caseWorld.ts and lib/evaluations.ts both spell out:
    // an interview that has not finished is a real, expected absence, and a
    // failed query is a network or permission failure worth a retry.
    // Collapsing the two would show a candidate an error for the whole
    // interview, not just the sessions whose fetch actually broke.
    state.selectData = []
    const { result } = renderHook(() => useCoachReport('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('empty'))
  })

  it('resolves to "error" with a candidate-readable message when the query fails', async () => {
    state.selectError = { message: 'permission denied' }
    const { result } = renderHook(() => useCoachReport('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('error'))
    expect(result.current.state).toEqual({
      kind: 'error',
      message: 'Could not load your coaching notes.',
    })
  })

  it('subscribes via postgres_changes INSERT filtered to the session, not a poll', async () => {
    renderHook(() => useCoachReport('sess-1'))
    await waitFor(() => expect(channelSubscribe).toHaveBeenCalled())

    expect(channelOn).toHaveBeenCalledWith(
      'postgres_changes',
      expect.objectContaining({
        event: 'INSERT',
        schema: 'public',
        table: 'coach_reports',
        filter: 'session_id=eq.sess-1',
      }),
      expect.any(Function),
    )
  })

  it('promotes "empty" to "ready" when an improvement arrives over realtime', async () => {
    const { result } = renderHook(() => useCoachReport('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('empty'))

    act(() => {
      state.handlers.forEach((handler) => handler({ new: makeRow({ id: 'live-1' }) }))
    })

    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
    expect(result.current.state.kind === 'ready' && result.current.state.improvements[0].id).toBe(
      'live-1',
    )
  })

  it('does not duplicate a row the realtime channel redelivers', async () => {
    state.selectData = [makeRow({ id: 'imp-1' })]
    const { result } = renderHook(() => useCoachReport('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('ready'))

    act(() => {
      state.handlers.forEach((handler) => handler({ new: makeRow({ id: 'imp-1' }) }))
    })

    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(result.current.state.kind === 'ready' && result.current.state.improvements).toHaveLength(1)
  })

  it('retry() re-queries after a failure', async () => {
    state.selectError = { message: 'network down' }
    const { result } = renderHook(() => useCoachReport('sess-1'))
    await waitFor(() => expect(result.current.state.kind).toBe('error'))

    state.selectError = null
    state.selectData = [makeRow()]
    act(() => {
      result.current.retry()
    })

    await waitFor(() => expect(result.current.state.kind).toBe('ready'))
  })

  it('unsubscribes on unmount', async () => {
    const { unmount } = renderHook(() => useCoachReport('sess-1'))
    await waitFor(() => expect(channelSubscribe).toHaveBeenCalled())

    unmount()
    expect(removeChannel).toHaveBeenCalledTimes(1)
  })
})

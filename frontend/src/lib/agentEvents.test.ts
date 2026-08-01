import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import type { AgentEvent } from './types'

// Mocked so this never touches real Supabase (same pattern as
// lib/supabase.test.ts). vi.mock factories are hoisted above imports, so
// the state they close over is created via vi.hoisted.
const { state, channelOn, channelSubscribe, removeChannel, fromMock } = vi.hoisted(() => {
  return {
    state: {
      selectData: [] as AgentEvent[],
      selectError: null as { message: string } | null,
      handlers: [] as Array<(payload: { new: AgentEvent }) => void>,
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
    then: (resolve: (v: { data: AgentEvent[] | null; error: { message: string } | null }) => void) =>
      Promise.resolve({ data: state.selectData, error: state.selectError }).then(resolve),
  }
  const channel = {
    on: (...args: unknown[]) => {
      channelOn(...args)
      state.handlers.push(args[2] as (payload: { new: AgentEvent }) => void)
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

const { useAgentEvents } = await import('./agentEvents')

function makeEvent(overrides: Partial<AgentEvent>): AgentEvent {
  return {
    id: 'evt-1',
    session_id: 'sess-1',
    agent: 'resume_analyst',
    status: 'started',
    summary: null,
    duration_ms: null,
    tokens: null,
    created_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

describe('useAgentEvents', () => {
  beforeEach(() => {
    state.selectData = []
    state.selectError = null
    state.handlers = []
    channelOn.mockClear()
    channelSubscribe.mockClear()
    removeChannel.mockClear()
    fromMock.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('returns an empty array and does not query when there is no session yet', () => {
    const { result } = renderHook(() => useAgentEvents(null))
    expect(result.current).toEqual([])
    expect(fromMock).not.toHaveBeenCalled()
  })

  it('fetches existing rows for the session before any realtime event arrives', async () => {
    state.selectData = [makeEvent({ id: 'evt-1', status: 'started' })]
    const { result } = renderHook(() => useAgentEvents('sess-1'))

    await waitFor(() => expect(result.current).toHaveLength(1))
    expect(result.current[0].id).toBe('evt-1')
  })

  it('subscribes via postgres_changes INSERT filtered to the session, not a poll', async () => {
    renderHook(() => useAgentEvents('sess-1'))
    await waitFor(() => expect(channelSubscribe).toHaveBeenCalled())

    expect(channelOn).toHaveBeenCalledWith(
      'postgres_changes',
      expect.objectContaining({
        event: 'INSERT',
        schema: 'public',
        table: 'agent_events',
        filter: 'session_id=eq.sess-1',
      }),
      expect.any(Function),
    )
  })

  it('appends a row delivered over realtime after the initial fetch', async () => {
    const { result } = renderHook(() => useAgentEvents('sess-1'))
    await waitFor(() => expect(channelSubscribe).toHaveBeenCalled())

    const newRow = makeEvent({ id: 'evt-2', status: 'done', summary: 'Read your resume' })
    state.handlers.forEach((handler) => handler({ new: newRow }))

    await waitFor(() => expect(result.current.some((e) => e.id === 'evt-2')).toBe(true))
  })

  it('does not duplicate a row the realtime channel redelivers', async () => {
    state.selectData = [makeEvent({ id: 'evt-1' })]
    const { result } = renderHook(() => useAgentEvents('sess-1'))
    await waitFor(() => expect(result.current).toHaveLength(1))

    state.handlers.forEach((handler) => handler({ new: makeEvent({ id: 'evt-1' }) }))

    // Give any (incorrect) duplicate-append a chance to land before asserting.
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(result.current).toHaveLength(1)
  })

  it('unsubscribes on unmount and on session change', async () => {
    const { unmount } = renderHook(() => useAgentEvents('sess-1'))
    await waitFor(() => expect(channelSubscribe).toHaveBeenCalled())

    unmount()
    expect(removeChannel).toHaveBeenCalledTimes(1)
  })
})

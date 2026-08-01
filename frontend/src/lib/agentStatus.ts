import type { AgentEvent } from './types'

export type AgentState = 'waiting' | 'active' | 'done' | 'error'

export interface AgentStatus {
  state: AgentState
  summary: string | null
  event: AgentEvent | null
}

/**
 * Pure derivation, no I/O -- kept separate from `useAgentEvents` so it can
 * be unit tested against fixture event lists without touching Supabase.
 * `events` is expected in arrival order (ascending `created_at`); the LAST
 * event for `agentName` decides the state: `started` with no later terminal
 * event is "active", `done` and `error` are terminal.
 */
export function deriveAgentStatus(events: AgentEvent[], agentName: string): AgentStatus {
  const own = events.filter((e) => e.agent === agentName)
  if (own.length === 0) {
    return { state: 'waiting', summary: null, event: null }
  }
  const latest = own[own.length - 1]
  const state: AgentState =
    latest.status === 'done' ? 'done' : latest.status === 'error' ? 'error' : 'active'
  return { state, summary: latest.summary, event: latest }
}

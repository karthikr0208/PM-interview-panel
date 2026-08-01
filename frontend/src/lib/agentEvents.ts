import { useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { AgentEvent } from './types'

/**
 * Live-subscribes to `agent_events` for one session via Supabase Realtime
 * (PHASE-1-SPEC.md 1.6b: "Live updates arrive via Supabase Realtime on
 * agent_events, not by polling"). RLS scopes what a subscriber can receive
 * to their own session -- proven with a real second identity in
 * `frontend/scripts/probe_realtime.mjs` before this hook was written.
 *
 * No manual `realtime.setAuth()` call here: `lib/supabase.ts`'s shared
 * client already listens for its own auth state changes and forwards the
 * token to `realtime` automatically (`SupabaseClient._listenForAuthEvents`),
 * and `ensureAnonymousSession()` has always run by the time a `sessionId`
 * exists to subscribe to (it is a precondition of `createSession()`).
 *
 * Fetches whatever rows already exist for the session and subscribes in the
 * same tick, merging both into one set de-duplicated by id.
 *
 * KNOWN RESIDUAL RISK, measured 2026-08-01, do not assume this is airtight.
 * A row inserted in the window between `subscribe()` reporting SUBSCRIBED and
 * the socket's RLS authorization settling server-side can be dropped silently:
 * the probe saw the positive control fail 2 of 8 runs at zero settle time, and
 * 3 of 3 pass with a 2s delay. A service-role control subscriber received every
 * row in the same runs, which isolates it to the RLS-scoped subscription rather
 * than the publication or the pipeline. Neither fetch order closes it -- the
 * fetch's snapshot is taken before the row exists and the subscription is not
 * yet delivering, so the row falls between them.
 *
 * It is unlikely to bite in practice today, and that is timing luck rather than
 * design: the Resume Analyst takes seconds to answer, so its `agent_events`
 * land long after the settle window. **Story 1.4 writes the first real events
 * and should re-check this** -- if any agent ever writes an event immediately
 * on session start, add a delayed re-fetch after SUBSCRIBED rather than
 * trusting the subscription alone.
 */
export function useAgentEvents(sessionId: string | null): AgentEvent[] {
  const [events, setEvents] = useState<AgentEvent[]>([])

  useEffect(() => {
    setEvents([])
    if (!sessionId) {
      return
    }

    let cancelled = false

    function mergeOne(row: AgentEvent) {
      setEvents((prev) => (prev.some((e) => e.id === row.id) ? prev : [...prev, row]))
    }

    supabase
      .from('agent_events')
      .select('*')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: true })
      .then(({ data, error }) => {
        if (cancelled || error || !data) return
        setEvents((prev) => {
          const merged = [...prev]
          for (const row of data as AgentEvent[]) {
            if (!merged.some((e) => e.id === row.id)) merged.push(row)
          }
          return merged
        })
      })

    const channel = supabase
      .channel(`agent-events-${sessionId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'agent_events',
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => mergeOne(payload.new as AgentEvent),
      )
      .subscribe()

    return () => {
      cancelled = true
      supabase.removeChannel(channel)
    }
  }, [sessionId])

  return events
}

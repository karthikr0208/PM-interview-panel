import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { CaseWorld } from './types'

export type CaseWorldState =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'ready'; world: CaseWorld }
  | { kind: 'error'; message: string }

/**
 * Reads the company brief for one session, once. `case_worlds` is written
 * exactly once by `generate_case_world` (story 1.1's DDL, story 3.5.2's
 * curated fixtures) and that write happens synchronously, inside the same
 * `ainvoke` call `/session/{id}/level/confirm` awaits, BEFORE that route
 * returns `first_question` -- so by the time `InterviewContainer` mounts
 * (App.tsx, gated on `levelState.kind === 'confirmed'`), the row already
 * exists. No realtime subscription, unlike `useAgentEvents`: this is a
 * write-once row read after its write has already settled, not a stream of
 * inserts arriving over the session's lifetime.
 *
 * Read directly from Supabase rather than added to an HTTP response body --
 * `case_worlds` has carried a `select`-only, own-session RLS policy since
 * story 1.1 (`migrations/0002_rls_policies.sql`), the same policy
 * `useAgentEvents` already relies on for `agent_events`. This is a read
 * against existing, checked-in infrastructure, not a new backend surface.
 *
 * `'empty'` (no row found) is kept distinct from `'error'` (the query
 * itself failed) -- the first is a real, if unexpected, absence; the second
 * is a network/permission failure worth a retry.
 *
 * Returns `{ state, retry }` -- matching `useLevelAssessment` and
 * `useInterview`'s own shape -- rather than spreading `retry` onto the
 * `CaseWorldState` union, which would let TypeScript decorrelate `kind` from
 * `world`/`message` on the merged object.
 */
export function useCaseWorld(sessionId: string | null): { state: CaseWorldState; retry: () => void } {
  const [state, setState] = useState<CaseWorldState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!sessionId) {
      setState({ kind: 'empty' })
      return
    }

    let cancelled = false
    setState({ kind: 'loading' })

    supabase
      .from('case_worlds')
      .select('world')
      .eq('session_id', sessionId)
      .maybeSingle()
      .then(({ data, error }: { data: { world: CaseWorld } | null; error: { message: string } | null }) => {
        if (cancelled) return
        if (error) {
          setState({ kind: 'error', message: 'Could not load the company brief.' })
          return
        }
        if (!data) {
          setState({ kind: 'empty' })
          return
        }
        setState({ kind: 'ready', world: data.world })
      })

    return () => {
      cancelled = true
    }
  }, [sessionId, attempt])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])

  return { state, retry }
}

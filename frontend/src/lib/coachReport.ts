import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { CoachImprovement } from './types'

export type CoachReportState =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'ready'; improvements: CoachImprovement[] }
  | { kind: 'error'; message: string }

/**
 * Live coaching notes for one session: an initial fetch plus a Realtime
 * subscription on `coach_reports`, modelled directly on `useEvaluations` in
 * `lib/evaluations.ts`. The Coach writes its three rows late -- after the
 * interview ends -- so unlike `case_worlds` (write-once, read-once) this
 * needs the same merge-on-arrival treatment `answer_evaluations` gets: a
 * fetch that overwrote state on resolution could drop a row that arrived
 * over realtime in the same tick.
 *
 * `'empty'` (no rows yet) is kept distinct from `'error'` (the query itself
 * failed), same reasoning as every other hook in this file's family: an
 * interview that has not finished yet is a real, expected absence -- the
 * Coach has not run -- and a failed query is a network or permission failure
 * worth a retry. Collapsing the two would show every candidate an error for
 * the entire interview, not just the ones whose fetch actually broke.
 *
 * Returns `{ state, retry }`, matching `useEvaluations` / `useCaseWorld`.
 *
 * 🔴 REALTIME PUBLICATION GAP: `coach_reports` is created by
 * `backend/migrations/0005_coach_reports.sql`, which adds RLS but does NOT
 * add the table to `supabase_realtime` -- only `0001_initial_schema.sql`
 * touches the publication, and its guarded loop lists exactly
 * `['transcript_turns', 'answer_evaluations', 'agent_events']`. `coach_reports`
 * is not in that array and no later migration adds it. The subscription
 * below is wired anyway, mirroring `useEvaluations` exactly, because the
 * initial `.select()` fetch does not depend on the publication and still
 * works correctly -- but until a migration adds `coach_reports` to
 * `supabase_realtime`, the INSERT handler here will never fire, and a
 * candidate who has this column mounted before the Coach writes will not see
 * the three cards appear live; only a subsequent fetch (e.g. a fresh page
 * load) would show them. Flagged for backend/DB attention, not fixed here --
 * CLAUDE.md reserves migrations for the orchestrator.
 */
export function useCoachReport(sessionId: string | null): {
  state: CoachReportState
  retry: () => void
} {
  const [state, setState] = useState<CoachReportState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!sessionId) {
      setState({ kind: 'empty' })
      return
    }

    let cancelled = false
    setState({ kind: 'loading' })

    // Merges into whatever rows are already held rather than replacing them,
    // for the same reason `useEvaluations` does: the fetch and the
    // subscription start in the same tick, so a row delivered over realtime
    // can land before the fetch resolves.
    function mergeRows(incoming: readonly CoachImprovement[]) {
      setState((prev) => {
        const merged = prev.kind === 'ready' ? [...prev.improvements] : []
        for (const row of incoming) {
          if (!merged.some((r) => r.id === row.id)) merged.push(row)
        }
        return merged.length > 0 ? { kind: 'ready', improvements: merged } : { kind: 'empty' }
      })
    }

    supabase
      .from('coach_reports')
      .select('*')
      .eq('session_id', sessionId)
      .order('idx', { ascending: true })
      .then(({ data, error }: { data: CoachImprovement[] | null; error: { message: string } | null }) => {
        if (cancelled) return
        if (error) {
          // A row already delivered over realtime outranks a failed fetch:
          // showing an error over notes the candidate can already see would
          // be a lie about what is known.
          setState((prev) =>
            prev.kind === 'ready' ? prev : { kind: 'error', message: 'Could not load your coaching notes.' },
          )
          return
        }
        mergeRows(data ?? [])
      })

    const channel = supabase
      .channel(`coach-reports-${sessionId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'coach_reports',
          filter: `session_id=eq.${sessionId}`,
        },
        (payload: { new: CoachImprovement }) => {
          if (cancelled) return
          mergeRows([payload.new])
        },
      )
      .subscribe()

    return () => {
      cancelled = true
      supabase.removeChannel(channel)
    }
  }, [sessionId, attempt])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])

  return { state, retry }
}

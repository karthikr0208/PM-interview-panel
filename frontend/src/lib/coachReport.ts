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
 * The publication gap this docstring used to describe is CLOSED.
 * `0005_coach_reports.sql` created the table with RLS but left it out of
 * `supabase_realtime` -- only `0001_initial_schema.sql` touched the
 * publication, listing exactly
 * `['transcript_turns', 'answer_evaluations', 'agent_events']` -- so the
 * INSERT handler below could never fire and the cards only appeared on a
 * fresh page load. `0006` adds the table to the publication, and the fix is
 * confirmed by the product rather than by a probe: in the live sit of
 * 2026-08-12 the coaching panel filled in with no refresh. Note that
 * `probe_realtime.mjs` cannot show this -- it exercises `agent_events`.
 *
 * It mattered more here than for the other three tables. Those are written
 * repeatedly, so a missed broadcast fills in on the next write.
 * `coach_reports` is written ONCE, in the last node, after the candidate has
 * stopped interacting.
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

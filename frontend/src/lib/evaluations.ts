import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { AnswerEvaluation } from './types'

/**
 * The five rubric dimensions, in PRD §7's order. Declaration order is render
 * order in `EvaluationColumn.tsx`, exactly as `AGENTS` is in
 * `OrchestrationColumn.tsx`. These strings are the JOIN KEY to
 * `answer_evaluations.dimension`, not a display concern -- the human labels
 * live in the component.
 */
export const DIMENSIONS = [
  'business_model_fluency',
  'market_accuracy',
  'decision_quality',
  'structural_clarity',
  'point_of_view',
] as const

export type Dimension = (typeof DIMENSIONS)[number]

/**
 * What one dimension currently stands at. `not_assessed` carries no score
 * field at all rather than a nullable one, so there is no shape in which a
 * missing row can be read as a number by a careless caller.
 */
export type DimensionStanding =
  | { dimension: Dimension; kind: 'scored'; evaluation: AnswerEvaluation }
  | { dimension: Dimension; kind: 'not_assessed' }

/**
 * HIGHEST SCORE PER DIMENSION WINS, TIE-BROKEN TO THE EARLIER ROW.
 *
 * The Evaluator scores once per ANSWER, so a dimension revisited by a later
 * probe has several rows in `answer_evaluations`. The scorecard shows the
 * candidate's BEST demonstrated standing on each dimension, not the most
 * recent attempt -- a probe answered worse than the opening answer (nerves, a
 * rushed follow-up) must not erase evidence of the stronger showing the
 * candidate already put on the record.
 *
 * Rows are read in `turn_idx` order and the HIGHEST score for a dimension
 * wins. On a tie, the EARLIER row wins (first time they demonstrated it):
 * iterating ascending and only replacing the held row on a STRICTLY greater
 * score means a later row scoring the same never displaces it.
 *
 * 🔴 THE WINNING ROW IS RETURNED, never a score computed apart from where it
 * came from. `evidence_quote` and `reasoning` on the returned standing always
 * belong to the SAME row as the score -- a scorecard whose quote traces back
 * to a different row than the number it sits beside would break this
 * product's central promise, that every score can be traced to the sentence
 * that earned it.
 *
 * `_prior_scores` in `backend/app/graph/build.py` still lets the LATEST
 * evaluation win, deliberately: it feeds the Evaluator the ARC of the
 * interview, where "what changed most recently" is exactly what belongs in
 * context. This function answers a different question -- what earns the
 * candidate the most credit on the scorecard -- so the two are allowed to
 * disagree, and they do on purpose.
 *
 * A dimension with NO ROW comes back `not_assessed`. `score` is
 * `not null check (score between 1 and 4)` in the schema, so absence is the
 * only way an unassessed dimension can exist, and it is never a zero.
 *
 * Pure, and separate from the hook on purpose: it is the part with real logic
 * in it, and it is tested against plain arrays with no React and no Supabase.
 */
export function highestPerDimension(rows: readonly AnswerEvaluation[]): DimensionStanding[] {
  const best = new Map<string, AnswerEvaluation>()

  // Sorted rather than assuming the query's ordering: rows also arrive over
  // realtime, in delivery order, and a re-scored dimension must not depend on
  // which path its row took to get here. Ascending order is also what makes
  // the tie-break work for free -- see the STRICTLY-greater check below.
  const ordered = [...rows].sort((a, b) => a.turn_idx - b.turn_idx)
  for (const row of ordered) {
    const current = best.get(row.dimension)
    // Strictly greater, not >=: on a tie, `current` is already the earlier
    // row (we are walking ascending), and leaving it in place IS the
    // tie-break to the earlier row.
    if (!current || row.score > current.score) {
      best.set(row.dimension, row)
    }
  }

  return DIMENSIONS.map((dimension) => {
    const evaluation = best.get(dimension)
    return evaluation ? { dimension, kind: 'scored', evaluation } : { dimension, kind: 'not_assessed' }
  })
}

export type EvaluationsState =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'ready'; rows: AnswerEvaluation[] }
  | { kind: 'error'; message: string }

/**
 * Live scores for one session: an initial fetch plus a Realtime subscription
 * on `answer_evaluations`, modelled on `lib/agentEvents.ts`. Unlike
 * `case_worlds`, this table is written repeatedly over the interview's
 * lifetime -- once per answer -- so a one-shot read would show a scorecard
 * frozen at whatever existed when the column mounted.
 *
 * `answer_evaluations` is in the realtime publication (migration 0001) and
 * carries a `select`-only, own-session RLS policy (migration 0002), the same
 * already-shipped infrastructure `useAgentEvents` and `useCaseWorld` read
 * against. No backend change is involved in this hook.
 *
 * `'empty'` (no rows yet) is kept distinct from `'error'` (the query itself
 * failed), the same distinction `lib/caseWorld.ts` spells out: an interview
 * that has not been scored yet is a real and expected absence, a failed query
 * is a network or permission failure worth a retry. Collapsing the two would
 * show a candidate an error for the entire first question.
 *
 * Returns `{ state, retry }` rather than spreading `retry` onto the union,
 * matching `useCaseWorld` / `useLevelAssessment` / `useInterview`.
 *
 * The realtime startup race documented at length in `lib/agentEvents.ts`
 * applies here too and is even less likely to bite: this column is mounted in
 * `AppShell`'s `evaluation` slot in `App.tsx`, outside the conversation
 * switch, so it subscribes the moment a `sessionId` exists -- before the
 * resume is even uploaded, and many minutes before the first answer is
 * scored.
 */
export function useEvaluations(sessionId: string | null): {
  state: EvaluationsState
  retry: () => void
} {
  const [state, setState] = useState<EvaluationsState>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!sessionId) {
      setState({ kind: 'empty' })
      return
    }

    let cancelled = false
    setState({ kind: 'loading' })

    // Every transition below MERGES into whatever rows are already held
    // rather than replacing them. The fetch and the subscription start in the
    // same tick, so a row delivered over realtime can land before the fetch
    // resolves; a fetch that overwrote state would drop it.
    function mergeRows(incoming: readonly AnswerEvaluation[]) {
      setState((prev) => {
        const merged = prev.kind === 'ready' ? [...prev.rows] : []
        for (const row of incoming) {
          if (!merged.some((r) => r.id === row.id)) merged.push(row)
        }
        return merged.length > 0 ? { kind: 'ready', rows: merged } : { kind: 'empty' }
      })
    }

    supabase
      .from('answer_evaluations')
      .select('*')
      .eq('session_id', sessionId)
      .order('turn_idx', { ascending: true })
      .then(({ data, error }: { data: AnswerEvaluation[] | null; error: { message: string } | null }) => {
        if (cancelled) return
        if (error) {
          // A row already delivered over realtime outranks a failed fetch:
          // showing an error over scores the candidate can see would be a
          // lie about what is known.
          setState((prev) =>
            prev.kind === 'ready' ? prev : { kind: 'error', message: 'Could not load your scorecard.' },
          )
          return
        }
        mergeRows(data ?? [])
      })

    const channel = supabase
      .channel(`answer-evaluations-${sessionId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'answer_evaluations',
          filter: `session_id=eq.${sessionId}`,
        },
        (payload: { new: AnswerEvaluation }) => {
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

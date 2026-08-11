import { Quotes, Target, WarningCircle } from '@phosphor-icons/react'
import { stripDashes } from '../lib/copy'
import { useCoachReport, type CoachReportState } from '../lib/coachReport'
import { DIMENSION_LABEL, type Dimension } from '../lib/evaluations'
import type { CoachImprovement } from '../lib/types'

/**
 * One improvement, rendered according to its `kind` -- the whole point of
 * this surface (CLAUDE.md story 5.4). A `moment` shows the candidate's own
 * words before the stronger version; a `gap` has no quote to show because
 * nothing was said, so it names the rubric dimension instead. Rendering a
 * `gap` with an empty quote block, or a `moment` without its quote, is
 * exactly the defect this split guards against.
 */
function ImprovementCard({ improvement, number }: { improvement: CoachImprovement; number: number }) {
  const { kind, anchor_quote, dimension, stronger_version, drill } = improvement

  return (
    <li className="border-t border-border py-4 first:border-t-0 first:pt-0">
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="mt-0.5 font-mono text-xs tabular-nums text-text-secondary"
        >
          {number}
        </span>
        <div className="min-w-0 flex-1 space-y-3">
          {kind === 'moment' ? (
            <div>
              <p className="flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                <Quotes size={14} className="shrink-0" />
                What you said
              </p>
              {/* NON-NULL for a `moment`, enforced in Postgres
                  (coach_reports_moment_needs_a_quote) -- there is always a
                  quote here to render. */}
              <blockquote className="mt-1 border-l-2 border-border pl-3 text-sm text-text-secondary">
                {stripDashes(anchor_quote as string)}
              </blockquote>
            </div>
          ) : (
            <div>
              <p className="flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                <Target size={14} className="shrink-0" />
                Never came up
              </p>
              {/* No quote block here, deliberately -- there is no sentence of
                  a thing the candidate never said. Names the dimension
                  instead, using the SAME human labels the scorecard uses
                  (`DIMENSION_LABEL`, shared from `lib/evaluations.ts`), so
                  the two surfaces cannot describe the same dimension two
                  different ways. */}
              <p className="mt-1 text-sm text-text-secondary">
                {DIMENSION_LABEL[dimension as Dimension] ?? dimension}
              </p>
            </div>
          )}

          <div>
            <p className="text-xs font-medium text-text-secondary">A stronger version</p>
            <p className="mt-1 text-sm text-text-primary">{stripDashes(stronger_version)}</p>
          </div>

          <div>
            <p className="text-xs font-medium text-text-secondary">Try this</p>
            <p className="mt-1 text-sm text-text-secondary">{stripDashes(drill)}</p>
          </div>
        </div>
      </div>
    </li>
  )
}

// Skeletal, never a circular spinner (v1 §3 Rule 5) -- same treatment as
// EvaluationColumn's LoadingState.
function LoadingState() {
  return (
    <div role="status" aria-live="polite">
      <p className="text-sm text-text-secondary">Loading your coaching notes.</p>
      <div className="mt-3 space-y-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="space-y-2">
            <div className="h-2 w-1/3 animate-pulse rounded-full bg-border" />
            <div className="h-2 w-full animate-pulse rounded-full bg-border" />
            <div className="h-2 w-2/3 animate-pulse rounded-full bg-border" />
          </div>
        ))}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="rounded-card border border-dashed border-border bg-surface p-4">
      {/* Honest and specific, never encouraging filler: the Coach runs once,
          at the end of the interview, and nothing here is a promise about
          what it will say. */}
      <p className="text-sm text-text-secondary">Your coaching notes appear when the interview ends.</p>
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-card border border-border bg-surface p-4" role="alert">
      <div className="flex items-start gap-3">
        <WarningCircle size={20} className="mt-0.5 shrink-0 text-error" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">We could not load your coaching notes</p>
          <p className="mt-1 text-sm text-text-secondary">{message}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 rounded-control border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98]"
      >
        Try again
      </button>
    </div>
  )
}

function ReportBody({ state, onRetry }: { state: CoachReportState; onRetry: () => void }) {
  if (state.kind === 'loading') return <LoadingState />
  if (state.kind === 'empty') return <EmptyState />
  if (state.kind === 'error') return <ErrorState message={state.message} onRetry={onRetry} />

  // Already ordered by `idx` ascending from the query and from realtime
  // merge, but sorted again here rather than trusted blindly -- the same
  // defensive stance `highestPerDimension` takes on `turn_idx`, and cheap
  // insurance against a row arriving out of order over realtime.
  const ordered = [...state.improvements].sort((a, b) => a.idx - b.idx)

  return (
    <ul className="flex flex-col">
      {ordered.map((improvement, i) => (
        <ImprovementCard key={improvement.id} improvement={improvement} number={i + 1} />
      ))}
    </ul>
  )
}

interface CoachReportProps {
  // null before the candidate's first upload attempt, matching
  // EvaluationColumn / OrchestrationColumn's prop.
  sessionId: string | null
}

/**
 * The coaching report (story 5.4): three improvements, each either a
 * `moment` (the candidate's own words, then a stronger version) or a `gap`
 * (a rubric dimension that never came up). Mounted below `EvaluationColumn`
 * in `App.tsx`'s evaluation slot -- this is end-of-interview output and
 * belongs under the scorecard it elaborates on, not beside it.
 */
export function CoachReport({ sessionId }: CoachReportProps) {
  const { state, retry } = useCoachReport(sessionId)

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-medium text-text-primary">What to work on</h2>
      <ReportBody state={state} onRetry={retry} />
    </div>
  )
}

import { useState } from 'react'
import { Eye, EyeSlash, Quotes, WarningCircle } from '@phosphor-icons/react'
import { stripDashes } from '../lib/copy'
import {
  DIMENSIONS,
  DIMENSION_LABEL,
  highestPerDimension,
  useEvaluations,
  type DimensionStanding,
  type EvaluationsState,
} from '../lib/evaluations'

const MAX_SCORE = 4
const SEGMENTS = [1, 2, 3, 4] as const

/**
 * Four segments, filled up to `score`. Horizontal bars, never a radar chart
 * (PRD §8) -- a radar makes five dimensions look like one shape and hides the
 * individual number, which is the opposite of what this surface is for.
 *
 * `aria-hidden`: the bar is a redundant view of the number rendered beside it,
 * and an unhidden run of four empty spans announces nothing useful.
 *
 * `score === null` is the unassessed track: DASHED and never filled, so it is
 * distinguishable from a score of 1 (one solid segment) at a glance and
 * without relying on colour.
 */
function ScoreBar({ score }: { score: number | null }) {
  return (
    <span aria-hidden="true" className="mt-2 flex gap-1">
      {SEGMENTS.map((segment) => {
        const filled = score !== null && segment <= score
        return (
          <span
            key={segment}
            data-filled={filled ? 'true' : 'false'}
            data-track={score === null ? 'dashed' : 'solid'}
            className={`h-1.5 flex-1 rounded-full ${
              filled
                ? 'bg-accent'
                : score === null
                  ? 'border border-dashed border-border bg-transparent'
                  : 'bg-border'
            }`}
          />
        )
      })}
    </span>
  )
}

function DimensionRow({ standing, blind }: { standing: DimensionStanding; blind: boolean }) {
  const label = DIMENSION_LABEL[standing.dimension]

  // Not expandable, deliberately: there is no row behind an unassessed
  // dimension, so there is no quote to reveal and a `<details>` here would
  // offer the candidate a control that opens onto nothing.
  if (standing.kind === 'not_assessed') {
    return (
      <li aria-label={label} className="border-t border-border py-3 first:border-t-0 first:pt-0">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-text-secondary">{label}</span>
          {/* No numeral at all. A zero here would be a score the Evaluator
              never gave, and the schema cannot even store one. */}
          <span className="text-xs text-text-secondary">Not assessed</span>
        </div>
        <ScoreBar score={null} />
      </li>
    )
  }

  const { score, evidence_quote, reasoning } = standing.evaluation

  return (
    <li aria-label={label} className="border-t border-border py-3 first:border-t-0 first:pt-0">
      {/* `<details>` rather than custom open state, the same choice
          OrchestrationColumn.tsx makes for its error detail: keyboard
          operable and screen-reader announced without a single line of
          interaction code. */}
      <details>
        <summary className="cursor-pointer list-none">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-text-primary">{label}</span>
            {blind ? (
              <span className="text-xs text-text-secondary">Assessed</span>
            ) : (
              // Always visible, never on hover (PRD §8), and mono so the
              // column does not jitter as scores land.
              <span className="font-mono text-xs tabular-nums text-text-primary">
                {score} / {MAX_SCORE}
              </span>
            )}
          </div>
          <ScoreBar score={blind ? null : score} />
        </summary>

        <div className="mt-3 space-y-3">
          <div>
            <p className="flex items-center gap-1.5 text-xs font-medium text-text-secondary">
              <Quotes size={14} className="shrink-0" />
              What you said
            </p>
            {/* `stripDashes` on every model-written string. Rows written
                before 2026-08-07 carry raw U+2011 and this column renders
                historical transcripts, so prompt-side cleaning does not
                cover them. */}
            <blockquote className="mt-1 border-l-2 border-border pl-3 text-sm text-text-secondary">
              {stripDashes(evidence_quote)}
            </blockquote>
          </div>
          {reasoning && (
            <div>
              <p className="text-xs font-medium text-text-secondary">Why this score</p>
              <p className="mt-1 text-sm text-text-secondary">{stripDashes(reasoning)}</p>
            </div>
          )}
        </div>
      </details>
    </li>
  )
}

// Skeletal, never a circular spinner (v1 §3 Rule 5) -- same treatment as
// CompanyBrief's LoadingCard and App's AssessingLevelCard.
function LoadingState() {
  return (
    <div role="status" aria-live="polite">
      <p className="text-sm text-text-secondary">Loading your scorecard.</p>
      <div className="mt-3 space-y-3">
        {DIMENSIONS.map((dimension) => (
          <div key={dimension} className="space-y-2">
            <div className="h-2 w-2/5 animate-pulse rounded-full bg-border" />
            <div className="h-1.5 w-full animate-pulse rounded-full bg-border" />
          </div>
        ))}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="rounded-card border border-dashed border-border bg-surface p-4">
      <p className="text-sm text-text-secondary">
        Nothing scored yet. Your scores appear here once you answer the first question.
      </p>
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-card border border-border bg-surface p-4" role="alert">
      <div className="flex items-start gap-3">
        <WarningCircle size={20} className="mt-0.5 shrink-0 text-error" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">We could not load your scorecard</p>
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

/**
 * 🔴 THE OVERALL IS SUPPRESSED WHENEVER ANY DIMENSION IS UNASSESSED.
 *
 * An average over five dimensions where two carry no evidence is a number
 * with no meaning, and no label ("partial", "so far") makes it honest --
 * candidates read the big number and ignore the qualifier. Coverage is the
 * true statement available at that moment, so coverage is what renders
 * (PRD §8, PHASE-4-SPEC 4.4).
 *
 * Blind mode falls through to the same coverage line: coverage and progress
 * are exactly what blind mode is allowed to show.
 */
function OverallLine({ standings, blind }: { standings: DimensionStanding[]; blind: boolean }) {
  const scored = standings.filter((s) => s.kind === 'scored')
  const assessed = scored.length
  const complete = assessed === DIMENSIONS.length

  if (complete && !blind) {
    const total = scored.reduce((sum, s) => sum + (s.kind === 'scored' ? s.evaluation.score : 0), 0)
    const average = (total / DIMENSIONS.length).toFixed(1)
    return (
      <p className="text-sm text-text-primary">
        Overall <span className="font-mono tabular-nums">{average}</span> /{' '}
        <span className="font-mono tabular-nums">{MAX_SCORE}</span>
      </p>
    )
  }

  return (
    <p className="text-sm text-text-secondary">
      <span className="font-mono tabular-nums">{assessed}</span> of{' '}
      <span className="font-mono tabular-nums">{DIMENSIONS.length}</span> dimensions assessed
    </p>
  )
}

interface EvaluationColumnProps {
  // null before the candidate's first upload attempt, exactly as
  // OrchestrationColumn takes it -- session creation is hoisted to the App
  // shell so both columns read the SAME session.
  sessionId: string | null
  // Forces blind mode OFF, whatever the toggle says: the full reveal at the
  // end of the interview (PRD §8). A prop rather than a hook so the moment of
  // reveal is owned by whoever knows the interview is over, not by this
  // column.
  revealed?: boolean
}

/**
 * The scorecard (story 4.4). Five rubric dimensions, always all five, each a
 * horizontal bar with its number always visible and its evidence one
 * disclosure away.
 *
 * The single design constraint everything here serves: a score the candidate
 * cannot trace back to a sentence they actually said is the failure this
 * surface exists to prevent. That is why every scored row expands to its
 * verbatim `evidence_quote`, and why an unassessed dimension says so in words
 * instead of rendering an empty bar that reads as a zero.
 */
export function EvaluationColumn({ sessionId, revealed = false }: EvaluationColumnProps) {
  const { state, retry } = useEvaluations(sessionId)
  // Defaults to scores VISIBLE (PRD §8). Blind mode is the deliberate
  // exercise, not the default posture.
  const [blindRequested, setBlindRequested] = useState(false)
  const blind = revealed ? false : blindRequested

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-text-primary">Evaluation</h2>
        {state.kind === 'ready' && !revealed && (
          <button
            type="button"
            aria-pressed={blindRequested}
            onClick={() => setBlindRequested((b) => !b)}
            className="flex items-center gap-1.5 rounded-control border border-border bg-surface px-2 py-1 text-xs font-medium text-text-secondary transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98]"
          >
            {blindRequested ? <EyeSlash size={14} /> : <Eye size={14} />}
            Blind mode
          </button>
        )}
      </div>
      <ScorecardBody state={state} blind={blind} onRetry={retry} />
    </div>
  )
}

function ScorecardBody({
  state,
  blind,
  onRetry,
}: {
  state: EvaluationsState
  blind: boolean
  onRetry: () => void
}) {
  if (state.kind === 'loading') return <LoadingState />
  if (state.kind === 'empty') return <EmptyState />
  if (state.kind === 'error') return <ErrorState message={state.message} onRetry={onRetry} />

  const standings = highestPerDimension(state.rows)

  return (
    <>
      <ul className="flex flex-col">
        {standings.map((standing) => (
          <DimensionRow key={standing.dimension} standing={standing} blind={blind} />
        ))}
      </ul>
      <div className="border-t border-border pt-3">
        <OverallLine standings={standings} blind={blind} />
      </div>
    </>
  )
}

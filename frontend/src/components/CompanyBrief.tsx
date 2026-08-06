import { useState } from 'react'
import { Buildings, CaretDown, CaretUp, WarningCircle } from '@phosphor-icons/react'
import type { CaseWorldState } from '../lib/caseWorld'

interface CompanyBriefProps {
  state: CaseWorldState
  onRetry: () => void
}

// Skeletal, never a circular spinner (v1 §3 Rule 5) -- same treatment as
// every other loading state in this app.
function LoadingCard() {
  return (
    <div className="rounded-card border border-border bg-surface p-4" role="status" aria-live="polite">
      <div className="h-3 w-1/3 animate-pulse rounded-full bg-border" />
      <div className="mt-3 space-y-2">
        <div className="h-2 w-full animate-pulse rounded-full bg-border" />
        <div className="h-2 w-4/5 animate-pulse rounded-full bg-border" />
      </div>
    </div>
  )
}

function EmptyCard() {
  return (
    <div className="rounded-card border border-dashed border-border bg-surface p-4">
      <p className="text-sm text-text-secondary">No company brief is available for this interview.</p>
    </div>
  )
}

function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-card border border-border bg-surface p-4" role="alert">
      <div className="flex items-start gap-3">
        <WarningCircle size={20} className="mt-0.5 shrink-0 text-error" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">We could not load the brief</p>
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
 * The company brief (story 3.5.5). Mounted once, as a sibling of
 * `InterviewSurface` rather than folded into its state machine -- the
 * acceptance box is "the candidate can re-read it without losing their
 * place", the same failure `useInterview` already guards against for the
 * main question (never overwritten by a clarification or a probe). Keeping
 * the brief in its OWN always-mounted component, driven by its own hook
 * (`lib/caseWorld.ts`), gets that property for free: nothing about the
 * interview's `asking` / `sending` / `error` transitions can make it
 * disappear, because it does not live in that state at all.
 *
 * Collapsible rather than fixed-open: the candidate reads it once at the
 * start, then wants the vertical space back for 45 minutes of probing --
 * collapsing does not unmount it, so "re-read without losing your place"
 * means one click away, not gone.
 *
 * Deliberately NOT run through `stripDashes`: unlike a probe or a question,
 * this text comes from the CURATED fixtures (`backend/app/cases/*.json`,
 * story 3.5.2), hand-written and already verified dash-free (PHASE-3.5-SPEC
 * §3.5.2's observed output), not live model output. `stripDashes` is for
 * the model-output surfaces; applying it here would be defending against a
 * failure mode this data cannot have.
 */
export function CompanyBrief({ state, onRetry }: CompanyBriefProps) {
  const [collapsed, setCollapsed] = useState(false)

  if (state.kind === 'loading') return <LoadingCard />
  if (state.kind === 'empty') return <EmptyCard />
  if (state.kind === 'error') return <ErrorCard message={state.message} onRetry={onRetry} />

  const { company, as_of } = state.world

  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        aria-expanded={!collapsed}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <Buildings size={18} className="shrink-0 text-text-secondary" />
          {company.name}
        </span>
        {collapsed ? <CaretDown size={16} className="text-text-secondary" /> : <CaretUp size={16} className="text-text-secondary" />}
      </button>

      {!collapsed && (
        <div className="mt-3 space-y-2">
          <p className="text-sm text-text-secondary">{company.one_line}</p>
          {as_of && (
            <p className="text-xs text-text-secondary">
              This brief reflects public information as of {as_of}. Treat it as ground truth for
              this interview.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

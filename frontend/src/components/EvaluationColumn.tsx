/**
 * Story 1.6a: a static placeholder. Live rubric-dimension scoring does not
 * exist until Phase 4 -- this phase never populates this column, it only
 * lays out the space for it.
 */
export function EvaluationColumn() {
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-medium text-text-primary">Evaluation</h2>
      <p className="text-sm text-text-secondary">
        Nothing scored yet. This column fills in once the interview begins.
      </p>
    </div>
  )
}

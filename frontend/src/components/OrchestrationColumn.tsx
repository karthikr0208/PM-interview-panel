/**
 * Story 1.6a: a static placeholder region with the correct layout and
 * nothing live in it. The four agent-status states (waiting/active/done/
 * error), plain-language activity descriptions, and the Supabase Realtime
 * subscription on `agent_events` all depend on story 1.4 (which does not
 * exist yet) and land in 1.6b.
 */
export function OrchestrationColumn() {
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-medium text-text-primary">Agents</h2>
      <p className="text-sm text-text-secondary">
        Agent activity will appear here once your resume is uploaded.
      </p>
    </div>
  )
}

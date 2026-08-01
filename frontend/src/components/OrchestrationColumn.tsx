import { useAgentEvents } from '../lib/agentEvents'
import { deriveAgentStatus, type AgentState, type AgentStatus } from '../lib/agentStatus'

// Distinguishable by SHAPE, not only colour (DESIGN.md §4, colour-blind
// candidates must still be able to tell states apart). Literal glyphs, not
// an icon component -- these four characters are the design system's own
// spec for this row, not a Phosphor icon substitution.
const GLYPH: Record<AgentState, string> = {
  waiting: '○',
  active: '◉',
  done: '●',
  error: '⚠',
}

const STATE_COLOR: Record<AgentState, string> = {
  waiting: 'text-text-secondary',
  active: 'text-accent',
  done: 'text-success',
  error: 'text-error',
}

const STATE_LABEL: Record<AgentState, string> = {
  waiting: 'Waiting',
  active: 'Working',
  done: 'Done',
  error: 'Error',
}

// Fallback copy for when no `agent_events.summary` has arrived yet (true
// today -- story 1.4 is what starts writing real events). Backend summaries
// are already plain language (schema comment on agent_events: "never raw
// JSON") and are rendered verbatim in preference to these when present.
const DEFAULT_COPY: Record<AgentState, string> = {
  waiting: 'Waiting to start.',
  active: 'Reading your resume and assessing a level.',
  done: 'Read your resume and assessed a level.',
  error: 'Ran into a problem understanding your resume.',
}

function AgentStatusRow({ name, status }: { name: string; status: AgentStatus }) {
  // Plain language only, never the raw event -- rendering `status.event`
  // itself (or JSON.stringify of it) here would be exactly the raw-JSON
  // regression PHASE-1-SPEC.md 1.6b bans.
  const copy = status.summary ?? DEFAULT_COPY[status.state]

  return (
    <div className="border-t border-border py-3 first:border-t-0 first:pt-0" role="status" aria-live="polite">
      <div className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className={`text-base leading-none ${STATE_COLOR[status.state]} ${
            // The one legitimate perpetual pulse in the system -- it
            // encodes real state (an agent is thinking right now), not
            // decoration. Reduced to near-zero automatically under
            // prefers-reduced-motion (frontend/src/index.css, global rule).
            status.state === 'active' ? 'animate-pulse' : ''
          }`}
        >
          {GLYPH[status.state]}
        </span>
        <span className="text-sm font-medium text-text-primary">{name}</span>
        <span className={`text-xs ${STATE_COLOR[status.state]}`}>{STATE_LABEL[status.state]}</span>
      </div>
      <p className="mt-1 pl-6 text-sm text-text-secondary">{copy}</p>
      {status.state === 'error' && status.event && (
        <details className="mt-1 pl-6">
          <summary className="cursor-pointer text-sm text-text-secondary">Show details</summary>
          <p className="mt-1 font-mono text-xs text-text-secondary">
            {status.event.agent} · {new Date(status.event.created_at).toLocaleTimeString()}
          </p>
        </details>
      )}
    </div>
  )
}

interface OrchestrationColumnProps {
  // null before the candidate's first upload attempt -- session creation is
  // hoisted to the App shell (lib/session.ts) and shared across siblings,
  // so this column subscribes to the SAME session the upload and
  // confirmation flow use, not a placeholder id of its own.
  sessionId: string | null
}

/**
 * Story 1.6b: the Resume Analyst's live status, driven by Supabase Realtime
 * on `agent_events` (lib/agentEvents.ts), not polling. Only one agent exists
 * in the panel this phase; later phases add rows here rather than replacing
 * this one.
 */
export function OrchestrationColumn({ sessionId }: OrchestrationColumnProps) {
  const events = useAgentEvents(sessionId)
  const resumeAnalyst = deriveAgentStatus(events, 'resume_analyst')

  return (
    <div className="flex flex-col gap-1">
      <h2 className="mb-2 text-sm font-medium text-text-primary">Agents</h2>
      <AgentStatusRow name="Resume Analyst" status={resumeAnalyst} />
    </div>
  )
}

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

// Fallback copy for when no `agent_events.summary` has arrived yet. Backend
// summaries are already plain language (schema comment on agent_events:
// "never raw JSON") and are rendered verbatim in preference to these when
// present.
//
// Every non-waiting string below is BYTE-IDENTICAL to the corresponding
// `_*_SUMMARY` constant in `app/graph/build.py`, which carries the matching
// comment. That is the point: a candidate sees the same sentence whether the
// row is showing the real event or its own fallback while the event is in
// flight, so the panel never visibly rewrites itself.
//
// No em-dashes anywhere in this file (CLAUDE.md, design v2 §9). Every string
// here is candidate-facing.
type AgentCopy = Record<AgentState, string>

interface PanelAgent {
  // Matches `agent_events.agent` exactly -- this is the join key to the
  // backend, not a display concern. `deriveAgentStatus` filters on it.
  key: string
  name: string
  copy: AgentCopy
}

const WAITING_COPY = 'Waiting to start.'

// Declaration order is render order, and it deliberately mirrors the graph:
// level_candidate -> generate_case_world -> plan_interview -> ask_question.
// A candidate watching the column sees work move down it in the order it
// actually happens, so later phases append here rather than inserting.
const AGENTS: readonly PanelAgent[] = [
  {
    key: 'resume_analyst',
    name: 'Resume Analyst',
    copy: {
      waiting: WAITING_COPY,
      active: 'Reading your resume and assessing a level.',
      done: 'Read your resume and assessed a level.',
      error: 'Ran into a problem understanding your resume.',
    },
  },
  {
    key: 'case_architect',
    name: 'Case Architect',
    copy: {
      waiting: WAITING_COPY,
      // Must stay byte-identical to build.py's _CASE_WORLD_*_SUMMARY, so a
      // candidate sees the same sentence whether this fallback or the real
      // summary renders. "Choosing" since 2026-08-07: the node selects one of
      // eight curated real companies and makes no LLM call, so "Building"
      // described work that no longer happens.
      active: 'Choosing the company for your interview.',
      done: 'Chose the company for your interview.',
      error: 'Ran into a problem choosing the company.',
    },
  },
  {
    key: 'planner',
    name: 'Interview Planner',
    copy: {
      waiting: WAITING_COPY,
      active: 'Planning interview questions.',
      done: 'Planned interview questions.',
      error: 'Ran into a problem planning the interview.',
    },
  },
  {
    key: 'interviewer',
    name: 'Interviewer',
    copy: {
      waiting: WAITING_COPY,
      active: 'Asking the next interview question.',
      done: 'Asked the next interview question.',
      // `ask_question` is fully deterministic and has no error branch --
      // `answer_clarification_node` is the only thing under this agent key
      // that can fail, so this is its error string, not ask_question's.
      error: 'Ran into a problem answering your clarifying question.',
    },
  },
  {
    // Added 2026-08-09, story 4.3. Its absence was a real defect, not an
    // omission of polish: `evaluate_answer_node` had been writing
    // `agent_events` rows under this key since the node was built, and
    // `deriveAgentStatus` filters on `AGENTS`, so every one of them was
    // silently dropped. The backend looked correct and the column simply
    // never showed the Evaluator working. `test_every_backend_agent_key_has
    // _a_row_in_the_orchestration_column` (backend/tests/test_user_facing_
    // copy.py) now fails when a new agent key reaches `agent_events` without
    // a row here, which is what makes this unrepeatable for Phase 5's Coach.
    key: 'evaluator',
    name: 'Evaluator',
    copy: {
      waiting: WAITING_COPY,
      // Byte-identical to build.py's _EVALUATE_*_SUMMARY, same rule as every
      // entry above. The Evaluator runs once per ANSWER rather than once per
      // phase, so this row re-enters `active` several times in one interview
      // -- the only row in this column that does.
      active: 'Scoring your answer against the rubric.',
      done: 'Scored your answer against the rubric.',
      error: 'Ran into a problem scoring your answer.',
    },
  },
]

function AgentStatusRow({
  name,
  status,
  copy: defaultCopy,
}: {
  name: string
  status: AgentStatus
  copy: AgentCopy
}) {
  // Plain language only, never the raw event -- rendering `status.event`
  // itself (or JSON.stringify of it) here would be exactly the raw-JSON
  // regression PHASE-1-SPEC.md 1.6b bans.
  const copy = status.summary ?? defaultCopy[status.state]

  return (
    // `aria-label` names the live region, so a screen reader announcing an
    // update says which agent changed. With three rows an unnamed "status"
    // region would announce a sentence with no subject.
    <div
      className="border-t border-border py-3 first:border-t-0 first:pt-0"
      role="status"
      aria-live="polite"
      aria-label={name}
    >
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
 * Live agent status, driven by Supabase Realtime on `agent_events`
 * (lib/agentEvents.ts), not polling.
 *
 * Story 1.6b built this for the Resume Analyst alone; story 2.7 added the
 * Case Architect and the Interview Planner, which needed a row each in
 * `AGENTS` and nothing else -- one subscription already carries every agent's
 * events for the session, since it filters on `session_id`, not on agent.
 *
 * THE REALTIME STARTUP RACE WAS RE-CHECKED HERE, not assumed (PHASE-2-SPEC
 * §2.7). `lib/agentEvents.ts` documents a window in which a row inserted
 * between `subscribe()` returning SUBSCRIBED and RLS authorization settling
 * can be dropped. The 2.7 acceptance box flags these two agents as the
 * condition that reopens it, because they write their first event sooner
 * after the candidate confirms than the Resume Analyst does after upload.
 *
 * It does NOT reopen, and the reason is structural rather than a timing
 * argument. **The settle window is measured from `subscribe()`, not from the
 * user action that triggers the event.** This component is mounted in
 * `AppShell`'s `orchestration` slot in `App.tsx`, OUTSIDE the
 * `renderConversation()` switch, so it is never unmounted by a state change
 * and `useAgentEvents` resubscribes only when `sessionId` itself changes.
 * `sessionId` is created once per candidate (story 1.6b fixed the
 * session-per-upload defect), so by the time the Case Architect writes
 * anything the subscription has been open for the entire upload, assessment
 * and confirmation cycle -- far longer than the 2s settle the probe measured
 * as sufficient, and longer than the Resume Analyst's own margin.
 *
 * What WOULD reopen it: rendering this column conditionally, remounting it on
 * the confirmation step, or keying the subscription to anything that changes
 * mid-journey.
 */
export function OrchestrationColumn({ sessionId }: OrchestrationColumnProps) {
  const events = useAgentEvents(sessionId)

  return (
    <div className="flex flex-col gap-1">
      <h2 className="mb-2 text-sm font-medium text-text-primary">Agents</h2>
      {AGENTS.map((agent) => (
        <AgentStatusRow
          key={agent.key}
          name={agent.name}
          copy={agent.copy}
          status={deriveAgentStatus(events, agent.key)}
        />
      ))}
    </div>
  )
}

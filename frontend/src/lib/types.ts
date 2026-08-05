/**
 * Mirrors `backend/app/agents/resume_analyst.py`'s `CandidateProfile` /
 * `ResumeAnalysis` Pydantic models field-for-field. Story 1.4 owns wiring a
 * real `ResumeAnalysis` from `level_candidate` into the UI built against
 * this interface -- see PHASE-1-SPEC.md 1.6b's scope boundary. Keep this in
 * sync with the backend models by hand; there is no shared schema generator
 * in this project.
 */

export const LEVELS = ['APM', 'PM', 'Senior PM', 'GPM'] as const

export type Level = (typeof LEVELS)[number]

export interface CandidateProfile {
  years_pm_experience: number | null
  domains: string[]
  product_types: string[]
  company_contexts: string[]
  scope_evidence: string[]
  notable_outcomes: string[]
  people_leadership: string | null
}

export interface ResumeAnalysis {
  candidate_profile: CandidateProfile
  assessed_level: Level
  level_rationale: string
  low_confidence_fields: string[]
}

/**
 * Mirrors the `agent_events` table (`backend/migrations/0001_initial_schema.sql`).
 * `summary` is written by the backend as plain language, never raw JSON --
 * the frontend renders it verbatim rather than composing new copy on top.
 */
export type AgentEventStatus = 'started' | 'done' | 'error'

export interface AgentEvent {
  id: string
  session_id: string
  agent: string
  status: AgentEventStatus
  summary: string | null
  duration_ms: number | null
  tokens: number | null
  created_at: string
}

/**
 * Mirrors `await_candidate`'s `interrupt()` payload in
 * `backend/app/graph/build.py` field-for-field. `kind` and `text` are
 * nullable because that node reads `messages[-1]` and yields `null` for
 * both when `messages` is empty -- defensive, not decorative.
 */
export type InterviewTurnKind = 'question' | 'clarification'

export interface InterviewTurn {
  kind: InterviewTurnKind | null
  text: string | null
  current_q_idx: number
}

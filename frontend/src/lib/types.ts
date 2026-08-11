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
 * Mirrors the `answer_evaluations` table
 * (`backend/migrations/0001_initial_schema.sql`, plus `reasoning` added by
 * `0004_evaluation_reasoning.sql`). ONE ROW PER (turn, dimension): the
 * Evaluator scores once per answer, so a dimension accumulates several rows
 * across an interview.
 *
 * `score` is `not null check (score between 1 and 4)` at the database, so an
 * unassessed dimension CANNOT be stored as a row. Absence is the
 * representation of "not assessed", deliberately -- never a zero, never a
 * sentinel. `lib/evaluations.ts` is the only place that turns absence into
 * the rendered state.
 *
 * `reasoning` is nullable: rows written before `0004` do not have it.
 */
export interface AnswerEvaluation {
  id: string
  session_id: string
  turn_idx: number
  dimension: string
  score: number
  evidence_quote: string
  reasoning: string | null
}

/**
 * Mirrors `await_candidate`'s `interrupt()` payload in
 * `backend/app/graph/build.py` field-for-field. `kind` and `text` are
 * nullable because that node reads `messages[-1]` and yields `null` for
 * both when `messages` is empty -- defensive, not decorative.
 *
 * `'probe'` added in story 3.5.5, mirroring `ask_probe`'s
 * `additional_kwargs={"kind": "probe"}` (`app/graph/build.py`) -- a probe is
 * a follow-up on the SAME main question, never a replacement for it. See
 * `lib/interview.ts`'s `useInterview` for how that distinction is kept.
 */
export type InterviewTurnKind = 'question' | 'clarification' | 'probe'

export interface InterviewTurn {
  kind: InterviewTurnKind | null
  text: string | null
  current_q_idx: number
}

/**
 * Mirrors `backend/app/agents/case_architect.py`'s Pydantic models
 * field-for-field, and the eight curated fixtures at `backend/app/cases/*.json`
 * (story 3.5.2). Read by the frontend from the `case_worlds` table directly
 * (`lib/caseWorld.ts`) via Supabase, the same RLS-scoped-select pattern
 * `lib/agentEvents.ts` already uses for `agent_events` -- `case_worlds` has
 * had a `select`-only, own-session RLS policy since story 1.1
 * (`migrations/0002_rls_policies.sql`), so this is a read against
 * already-shipped infrastructure, not a new backend surface.
 */
export interface CaseWorldCompetitor {
  name: string
  positioning: string
  relative_strength: string
}

export interface CaseWorldCompany {
  name: string
  one_line: string
  stage: 'seed' | 'series_a' | 'series_b' | 'series_c' | 'growth' | 'public'
  employees: number
  founded_year: number
}

export interface CaseWorldMarket {
  description: string
  size_usd: string
  growth_rate_pct: number
  competitors: CaseWorldCompetitor[]
}

export interface CaseWorldMetrics {
  arr_usd: string
  yoy_growth_pct: number
  gross_margin_pct: number
  monthly_churn_pct: number
  customer_count: number
}

export interface CaseWorldSituation {
  prompt: string
  tension: string
  options: string[]
  constraints: string[]
  leadership_belief: string
}

export interface CaseWorld {
  company: CaseWorldCompany
  market: CaseWorldMarket
  metrics: CaseWorldMetrics
  situation: CaseWorldSituation
  supporting_facts: string[]
  as_of: string
  suits_categories: string[]
}

/**
 * Mirrors the `coach_reports` table (`backend/migrations/0005_coach_reports.sql`).
 * ONE ROW PER IMPROVEMENT, three rows per session, ordered for display by
 * `idx` -- not a JSON blob, for the same reason `answer_evaluations` is one
 * row per (turn, dimension).
 *
 * `kind` decides which of `anchor_quote` / `dimension` is populated, enforced
 * in Postgres by two scoped check constraints rather than by convention:
 *   'moment' -- the candidate said something. `anchor_quote` is non-null,
 *               `dimension` is null.
 *   'gap'    -- a rubric dimension never came up. `dimension` is non-null,
 *               `anchor_quote` is null -- there is no quote of a thing the
 *               candidate never said.
 *
 * `anchor_quote` is never normalised on the way in (matches
 * `answer_evaluations.evidence_quote`): it is compared to the transcript
 * byte for byte. `stronger_version` and `drill` ARE normalised for em-dashes
 * at the graph boundary, same as `reasoning`.
 */
export type CoachImprovementKind = 'moment' | 'gap'

export interface CoachImprovement {
  id: string
  session_id: string
  idx: number
  kind: CoachImprovementKind
  anchor_quote: string | null
  dimension: string | null
  stronger_version: string
  drill: string
  created_at: string
}

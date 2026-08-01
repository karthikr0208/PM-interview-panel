import { useState, type ReactNode } from 'react'
import { CheckCircle, WarningCircle } from '@phosphor-icons/react'
import { LEVELS, type Level, type ResumeAnalysis } from '../lib/types'

interface ConfirmationScreenProps {
  analysis: ResumeAnalysis
  /**
   * Transport-agnostic on purpose -- story 1.4 owns the backend route (see
   * `lib/api.ts`'s `submitLevelCorrection` seam). This component only
   * reports what the candidate chose; it does not know how that reaches
   * the graph.
   */
  onConfirm: (level: Level, meta: { corrected: boolean }) => void
}

function isUncertain(analysis: ResumeAnalysis, field: string): boolean {
  return analysis.low_confidence_fields.includes(field)
}

function UncertainBadge() {
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-warning">
      <WarningCircle size={14} />
      Worth double-checking
    </span>
  )
}

function FieldBlock({
  label,
  uncertain,
  children,
}: {
  label: string
  uncertain: boolean
  children: ReactNode
}) {
  return (
    <div
      className={`rounded-control border p-3 ${
        uncertain ? 'border-warning bg-warning/10' : 'border-border'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium text-text-primary">{label}</p>
        {uncertain && <UncertainBadge />}
      </div>
      <div className="mt-1 text-sm text-text-secondary">{children}</div>
    </div>
  )
}

function QuoteList({ items, emptyText }: { items: string[]; emptyText: string }) {
  if (items.length === 0) {
    return <p>{emptyText}</p>
  }
  return (
    <ul className="list-disc space-y-1 pl-4">
      {items.map((item) => (
        <li key={item}>&ldquo;{item}&rdquo;</li>
      ))}
    </ul>
  )
}

/**
 * Story 1.6b. Shows the Resume Analyst's output (`ResumeAnalysis`, mirrored
 * in `lib/types.ts`) and lets the candidate accept or correct the level.
 * Fields named in `low_confidence_fields` are marked so the candidate knows
 * what to check rather than reviewing everything with equal weight
 * (PHASE-1-SPEC.md 1.6b).
 */
export function ConfirmationScreen({ analysis, onConfirm }: ConfirmationScreenProps) {
  const { candidate_profile: profile } = analysis
  const [selectedLevel, setSelectedLevel] = useState<Level>(analysis.assessed_level)
  const [submitted, setSubmitted] = useState(false)

  const corrected = selectedLevel !== analysis.assessed_level

  function handleSubmit() {
    onConfirm(selectedLevel, { corrected })
    setSubmitted(true)
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <div>
        <h2 className="text-sm font-medium text-text-primary">Your assessed level</h2>
        <p className="mt-1 text-sm text-text-secondary">
          Based on your resume, here is the level we would interview you at. Correct it if it does
          not look right.
        </p>
      </div>

      <div className={`rounded-card border p-4 ${
        isUncertain(analysis, 'assessed_level') ? 'border-warning bg-warning/10' : 'border-border bg-surface'
      }`}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-text-primary">Level</span>
          {isUncertain(analysis, 'assessed_level') && <UncertainBadge />}
        </div>
        <div className="mt-3 flex flex-wrap gap-2" role="radiogroup" aria-label="Assessed level">
          {LEVELS.map((level) => (
            <button
              key={level}
              type="button"
              role="radio"
              aria-checked={selectedLevel === level}
              disabled={submitted}
              onClick={() => setSelectedLevel(level)}
              className={`rounded-control border px-3 py-2 text-sm font-medium transition-colors duration-(--duration-standard) ease-standard disabled:cursor-not-allowed disabled:opacity-60 ${
                selectedLevel === level
                  ? 'border-accent bg-accent text-white'
                  : 'border-border bg-surface text-text-primary hover:border-accent'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
        <p className="mt-3 text-sm text-text-secondary">{analysis.level_rationale}</p>
      </div>

      <FieldBlock label="Years of PM experience" uncertain={isUncertain(analysis, 'years_pm_experience')}>
        {profile.years_pm_experience === null ? (
          <p>Not clearly stated on the resume.</p>
        ) : (
          <p className="mono-num">{profile.years_pm_experience}</p>
        )}
      </FieldBlock>

      <FieldBlock label="Domains" uncertain={isUncertain(analysis, 'domains')}>
        {profile.domains.length === 0 ? <p>None listed.</p> : <p>{profile.domains.join(', ')}</p>}
      </FieldBlock>

      <FieldBlock label="Product types" uncertain={isUncertain(analysis, 'product_types')}>
        {profile.product_types.length === 0 ? (
          <p>None listed.</p>
        ) : (
          <p>{profile.product_types.join(', ')}</p>
        )}
      </FieldBlock>

      <FieldBlock label="Company contexts" uncertain={isUncertain(analysis, 'company_contexts')}>
        {profile.company_contexts.length === 0 ? (
          <p>None listed.</p>
        ) : (
          <p>{profile.company_contexts.join(', ')}</p>
        )}
      </FieldBlock>

      <FieldBlock label="What you owned" uncertain={isUncertain(analysis, 'scope_evidence')}>
        <QuoteList items={profile.scope_evidence} emptyText="Nothing found on the resume." />
      </FieldBlock>

      <FieldBlock label="Outcomes" uncertain={isUncertain(analysis, 'notable_outcomes')}>
        <QuoteList items={profile.notable_outcomes} emptyText="No measurable outcomes listed." />
      </FieldBlock>

      <FieldBlock label="People led" uncertain={isUncertain(analysis, 'people_leadership')}>
        <p>{profile.people_leadership ?? 'None mentioned.'}</p>
      </FieldBlock>

      {submitted ? (
        <div className="flex items-center gap-2 rounded-card border border-border bg-surface p-4">
          <CheckCircle size={20} className="shrink-0 text-success" />
          <p className="text-sm text-text-primary">
            {corrected ? 'Your corrected level was sent.' : 'Level confirmed.'}
          </p>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleSubmit}
          className="self-start rounded-control bg-accent px-4 py-2 text-sm font-medium text-white transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98]"
        >
          {corrected ? 'Confirm corrected level' : 'Confirm level'}
        </button>
      )}
    </div>
  )
}

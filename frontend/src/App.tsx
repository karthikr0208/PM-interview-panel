import { WarningCircle } from '@phosphor-icons/react'
import HealthCheck from './HealthCheck'
import { IconStandard } from './lib/icons'
import { useCandidateSession } from './lib/session'
import { useLevelAssessment } from './lib/levelAssessment'
import { AppShell } from './components/AppShell'
import { OrchestrationColumn } from './components/OrchestrationColumn'
import { EvaluationColumn } from './components/EvaluationColumn'
import { UploadSurface } from './components/UploadSurface'
import { ConfirmationScreen } from './components/ConfirmationScreen'

// Skeletal, never a circular spinner (v1 §3 Rule 5) -- same treatment as
// UploadSurface's ParsingState, reused here rather than imported since that
// component's states are upload-specific and this one is not.
function AssessingLevelCard() {
  return (
    <div className="rounded-card border border-border bg-surface p-6" role="status" aria-live="polite">
      <p className="text-sm font-medium text-text-primary">Reading your resume</p>
      <p className="mt-1 text-sm text-text-secondary">Assessing what level to interview you at.</p>
      <div className="mt-4 space-y-2">
        <div className="h-2 w-full animate-pulse rounded-full bg-border" />
        <div className="h-2 w-5/6 animate-pulse rounded-full bg-border" />
        <div className="h-2 w-2/3 animate-pulse rounded-full bg-border" />
      </div>
    </div>
  )
}

function LevelAssessmentErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-card border border-border bg-surface p-6" role="alert">
      <div className="flex items-start gap-3">
        <WarningCircle size={24} className="mt-0.5 shrink-0 text-error" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">We could not assess your level</p>
          <p className="mt-1 text-sm text-text-secondary">{message}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-control border border-border bg-surface px-4 py-2 text-sm font-medium text-text-primary transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98]"
      >
        Try again
      </button>
    </div>
  )
}

function App() {
  // Hoisted here, not inside UploadSurface, so a rejected file plus a retry
  // reuses the SAME session and so OrchestrationColumn can subscribe to the
  // same session's agent_events (PHASE-1-SPEC.md 1.6b).
  const { sessionId, getOrCreateSessionId } = useCandidateSession()
  // Owns level_candidate -> confirm_level from the candidate's side (story
  // 1.4): starts the Resume Analyst once the resume is uploaded, holds its
  // result for ConfirmationScreen, and carries a confirmation or correction
  // back to the backend.
  const { state: levelState, beginAssessment, confirmLevel } = useLevelAssessment(sessionId)

  function renderConversation() {
    switch (levelState.kind) {
      case 'ready':
      case 'confirmed':
        return (
          <ConfirmationScreen
            analysis={levelState.analysis}
            onConfirm={(level) => {
              void confirmLevel(level)
            }}
          />
        )
      case 'assessing':
        return <AssessingLevelCard />
      case 'error':
        return (
          <LevelAssessmentErrorCard message={levelState.message} onRetry={() => void beginAssessment()} />
        )
      case 'idle':
      default:
        return (
          <UploadSurface
            getOrCreateSessionId={getOrCreateSessionId}
            onUploadComplete={() => void beginAssessment()}
          />
        )
    }
  }

  return (
    <IconStandard>
      <AppShell
        orchestration={<OrchestrationColumn sessionId={sessionId} />}
        conversation={renderConversation()}
        evaluation={<EvaluationColumn />}
      />
      {/* Phase 0 scaffolding. Not deleted here -- story 1.7 removes it, only
          after 1.4 is verified against the real level_candidate/confirm_level
          nodes above. Kept rendered, out of the primary flow, per that
          story's own constraint. */}
      <div className="border-t border-border p-4">
        <HealthCheck />
      </div>
    </IconStandard>
  )
}

export default App

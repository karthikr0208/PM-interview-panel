import { WarningCircle } from '@phosphor-icons/react'
import { IconStandard } from './lib/icons'
import { useCandidateSession } from './lib/session'
import { useLevelAssessment } from './lib/levelAssessment'
import { useInterview } from './lib/interview'
import { useCaseWorld } from './lib/caseWorld'
import { AppShell } from './components/AppShell'
import { OrchestrationColumn } from './components/OrchestrationColumn'
import { EvaluationColumn } from './components/EvaluationColumn'
import { CoachReport } from './components/CoachReport'
import { UploadSurface } from './components/UploadSurface'
import { ConfirmationScreen } from './components/ConfirmationScreen'
import { InterviewSurface } from './components/InterviewSurface'
import { CompanyBrief } from './components/CompanyBrief'
import type { InterviewTurn } from './lib/types'

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

// Its own component, not inlined into `renderConversation`, so `useInterview`
// mounts fresh exactly once the candidate's level is confirmed -- the hook's
// initial state closes over `firstQuestion` on mount, and this component
// mounting is what makes that mount happen at the right moment rather than
// needing a placeholder question before one exists.
function InterviewContainer({
  sessionId,
  firstQuestion,
}: {
  sessionId: string | null
  firstQuestion: InterviewTurn
}) {
  const { state, submitAnswer, askClarification } = useInterview(sessionId, firstQuestion)
  // Own hook, own always-mounted component -- see CompanyBrief.tsx's
  // docstring for why the brief lives outside `useInterview`'s state
  // machine rather than as one more field threaded through it.
  const { state: briefState, retry: retryBrief } = useCaseWorld(sessionId)
  return (
    <div className="flex flex-col gap-4">
      <CompanyBrief state={briefState} onRetry={retryBrief} />
      <InterviewSurface
        state={state}
        onSubmitAnswer={submitAnswer}
        onAskClarification={askClarification}
        coachReport={<CoachReport sessionId={sessionId} />}
      />
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
        return (
          <ConfirmationScreen
            analysis={levelState.analysis}
            onConfirm={(level) => {
              void confirmLevel(level)
            }}
          />
        )
      case 'confirmed':
        // ConfirmationScreen's own "Level confirmed." acknowledgment
        // (`submitted` state) already showed while `confirmLevel`'s request
        // was in flight -- this replaces it with the interview once the
        // first question has actually arrived, rather than deleting that
        // acknowledgment outright.
        return <InterviewContainer sessionId={sessionId} firstQuestion={levelState.firstQuestion} />
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
            // Takes the id from the upload rather than from `sessionId`
            // above: on the FIRST upload this closure is created while
            // `sessionId` is still null, and passing nothing left the
            // Resume Analyst on "Waiting to start" forever. See
            // lib/levelAssessment.ts.
            onUploadComplete={(uploadedSessionId) => void beginAssessment(uploadedSessionId)}
          />
        )
    }
  }

  return (
    <IconStandard>
      <AppShell
        orchestration={<OrchestrationColumn sessionId={sessionId} />}
        conversation={renderConversation()}
        // Same session as the orchestration column, for the same reason: both
        // read the candidate's own rows over Realtime and neither may mint an
        // id of its own. `revealed` stays unset until Phase 5 owns the end of
        // the interview -- until then the candidate controls blind mode.
        // `CoachReport` used to render here, below the scorecard, but this
        // rail is too narrow to read three paragraphs of coaching prose. It
        // now renders in `InterviewContainer`'s middle column instead, below
        // the end-of-interview card, where there is room for prose. This
        // rail stays numbers-only.
        evaluation={<EvaluationColumn sessionId={sessionId} />}
      />
    </IconStandard>
  )
}

export default App

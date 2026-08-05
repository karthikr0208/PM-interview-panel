import { useEffect, useState } from 'react'
import { WarningCircle } from '@phosphor-icons/react'
import { stripDashes } from '../lib/copy'
import type { InterviewState } from '../lib/interview'

interface InterviewSurfaceProps {
  state: InterviewState
  onSubmitAnswer: (text: string) => void
  onAskClarification: (text: string) => void
}

// Skeletal, never a circular spinner (v1 §3 Rule 5) -- same treatment as
// App.tsx's AssessingLevelCard, copied rather than imported since App.tsx
// does not export it. Copy differs by what is actually in flight.
function SendingSkeleton({ pending }: { pending: 'answer' | 'clarify' }) {
  return (
    <div className="rounded-card border border-border bg-surface p-6" role="status" aria-live="polite">
      <p className="text-sm font-medium text-text-primary">
        {pending === 'answer' ? 'Sending your answer' : 'Sending your question'}
      </p>
      <p className="mt-1 text-sm text-text-secondary">
        {pending === 'answer'
          ? 'The interviewer is reading it.'
          : 'Waiting for a reply to your clarifying question.'}
      </p>
      <div className="mt-4 space-y-2">
        <div className="h-2 w-full animate-pulse rounded-full bg-border" />
        <div className="h-2 w-5/6 animate-pulse rounded-full bg-border" />
        <div className="h-2 w-2/3 animate-pulse rounded-full bg-border" />
      </div>
    </div>
  )
}

// Mirrors App.tsx's LevelAssessmentErrorCard -- same shape, different copy
// and a retry that resends the candidate's own last action instead of
// restarting the whole assessment.
function ErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-card border border-border bg-surface p-4" role="alert">
      <div className="flex items-start gap-3">
        <WarningCircle size={24} className="mt-0.5 shrink-0 text-error" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">We could not send that</p>
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

/**
 * The candidate-facing side of the conduct loop (story 3.3). Presentational
 * -- `useInterview` (lib/interview.ts) owns the state; this component only
 * renders it and reports the candidate's two actions upward.
 *
 * Answer and clarify are two SEPARATE controls, not one textarea with a
 * mode toggle -- the acceptance box requires the two actions be visibly
 * distinct, not merely functionally distinct.
 *
 * NO persona header, no interviewer name, no avatar (banned 2026-07-31).
 * The question is rendered whole in a single node -- no typewriter, no
 * per-character reveal (design v1).
 */
export function InterviewSurface({ state, onSubmitAnswer, onAskClarification }: InterviewSurfaceProps) {
  const [answerText, setAnswerText] = useState('')
  const [clarifyText, setClarifyText] = useState('')
  // Which control was submitted last, so "Try again" resends the SAME
  // action rather than guessing -- the hook's own error state does not
  // carry this, since it is an input-echo concern, not interview state.
  const [lastAction, setLastAction] = useState<'answer' | 'clarify' | null>(null)

  const question = state.kind === 'done' ? null : state.question
  const clarification = state.kind === 'done' ? null : state.clarification
  const questionIdx = question?.current_q_idx ?? null

  // A new question arriving means the previous answer was accepted --
  // clear the stale text rather than leave it sitting in the box.
  useEffect(() => {
    setAnswerText('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionIdx])

  // A clarification answer landing means the candidate's question was
  // already sent -- clear the input so a follow-up starts blank.
  useEffect(() => {
    if (clarification) setClarifyText('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clarification])

  if (state.kind === 'done') {
    return (
      <div className="mx-auto flex max-w-xl flex-col gap-4">
        <div className="rounded-card border border-border bg-surface p-6">
          <p className="text-sm font-medium text-text-primary">That is the end of the interview.</p>
          <p className="mt-1 text-sm text-text-secondary">
            Feedback and scoring are not part of this build yet.
          </p>
        </div>
      </div>
    )
  }

  const sending = state.kind === 'sending'
  const answerEmpty = answerText.trim().length === 0
  const clarifyEmpty = clarifyText.trim().length === 0

  function handleSubmitAnswer() {
    if (answerEmpty || sending) return
    setLastAction('answer')
    onSubmitAnswer(answerText)
  }

  function handleAskClarification() {
    if (clarifyEmpty || sending) return
    setLastAction('clarify')
    onAskClarification(clarifyText)
  }

  function handleRetry() {
    if (lastAction === 'clarify') {
      onAskClarification(clarifyText)
    } else {
      onSubmitAnswer(answerText)
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <div className="rounded-card border border-border bg-surface p-4">
        <p className="text-xs font-medium text-text-secondary">
          Question <span className="mono-num">{question?.current_q_idx ?? ''}</span>
        </p>
        <p className="mt-2 text-sm text-text-primary">{stripDashes(question?.text ?? '')}</p>
      </div>

      {clarification && (
        <div className="rounded-control border border-border bg-background p-3">
          <p className="text-xs font-medium text-text-secondary">
            Answer to your clarifying question
          </p>
          <p className="mt-1 text-sm text-text-secondary">{stripDashes(clarification)}</p>
          <p className="mt-2 text-xs text-text-secondary">The question above is still yours to answer.</p>
        </div>
      )}

      {state.kind === 'error' && <ErrorBanner message={state.message} onRetry={handleRetry} />}

      {sending && <SendingSkeleton pending={state.pending} />}

      <div className="rounded-card border border-border bg-surface p-4">
        <label htmlFor="interview-answer" className="text-sm font-medium text-text-primary">
          Your answer
        </label>
        <textarea
          id="interview-answer"
          value={answerText}
          onChange={(e) => setAnswerText(e.target.value)}
          disabled={sending}
          rows={5}
          className="mt-1 w-full rounded-control border border-border bg-surface p-3 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-60"
        />
        {answerEmpty && (
          <p className="mt-1 text-xs text-text-secondary">Write an answer before submitting.</p>
        )}
        <button
          type="button"
          onClick={handleSubmitAnswer}
          disabled={sending || answerEmpty}
          className="mt-3 rounded-control bg-accent px-4 py-2 text-sm font-medium text-white transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Submit answer
        </button>
      </div>

      <div className="rounded-control border border-border bg-surface p-3">
        <label htmlFor="interview-clarify" className="text-xs font-medium text-text-secondary">
          Or ask a clarifying question instead
        </label>
        <textarea
          id="interview-clarify"
          value={clarifyText}
          onChange={(e) => setClarifyText(e.target.value)}
          disabled={sending}
          rows={2}
          className="mt-1 w-full rounded-control border border-border bg-surface p-2 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-60"
        />
        {clarifyEmpty && <p className="mt-1 text-xs text-text-secondary">Type a question first.</p>}
        <button
          type="button"
          onClick={handleAskClarification}
          disabled={sending || clarifyEmpty}
          className="mt-2 rounded-control border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-primary transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Ask a clarifying question
        </button>
      </div>
    </div>
  )
}

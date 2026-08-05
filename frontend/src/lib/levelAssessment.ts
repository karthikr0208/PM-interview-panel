import { useCallback, useState } from 'react'
import { ApiError, startLevelAssessment, submitLevelCorrection } from './api'
import type { InterviewTurn, Level, ResumeAnalysis } from './types'

export type LevelAssessmentState =
  | { kind: 'idle' }
  | { kind: 'assessing' }
  | { kind: 'ready'; analysis: ResumeAnalysis }
  // Keeps `analysis` (rather than dropping it) so the caller can keep
  // rendering the SAME `ConfirmationScreen` after a successful confirm --
  // that component already shows its own "confirmed" acknowledgement
  // locally (ConfirmationScreen.tsx's `submitted` state); swapping it out
  // for different UI here would replace that acknowledgement instead of
  // letting it stand.
  //
  // `firstQuestion` (story 3.3) is the same resume's second pause,
  // `await_candidate`'s interrupt payload -- it lets `App.tsx` hand the
  // interview off without a second round trip.
  | { kind: 'confirmed'; analysis: ResumeAnalysis; level: Level; firstQuestion: InterviewTurn }
  | { kind: 'error'; message: string }

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback
}

/**
 * Owns the `level_candidate` -> `confirm_level` cycle from the candidate's
 * side: kicks off the Resume Analyst once a resume is uploaded, holds the
 * result long enough for `ConfirmationScreen` to render it, and carries the
 * candidate's confirmation or correction back to the backend
 * (PHASE-1-SPEC.md 1.4).
 *
 * Deliberately separate from `UploadSurface` (which only knows upload
 * progress, not what happens after) and from `useCandidateSession` (which
 * only knows the session id) -- this hook is what `App.tsx` composes them
 * through.
 */
export function useLevelAssessment(sessionId: string | null) {
  const [state, setState] = useState<LevelAssessmentState>({ kind: 'idle' })

  /**
   * `uploadedSessionId` is the id the resume was ACTUALLY uploaded against,
   * handed over by `UploadSurface`. It is not a convenience parameter.
   *
   * 🔴 Without it this function silently did nothing on the real candidate
   * journey, and the bug shipped to production (observed 2026-08-04). The
   * first file is chosen while `sessionId` is still null, so the
   * `onUploadComplete` callback captured by `UploadSurface`'s async handler
   * closes over the render where this `useCallback` also saw null. The upload
   * then creates the session and succeeds, calls that captured callback, and
   * the old `if (!sessionId) return` guard returned silently -- leaving the
   * state machine on `idle`, which re-renders the upload surface in its
   * success state. To the candidate the resume uploads fine and the Resume
   * Analyst sits on "Waiting to start" forever.
   *
   * Passing the id through removes the race rather than narrowing it: the
   * upload already knows which session it used, so nothing has to wait for a
   * React state update to propagate.
   */
  const beginAssessment = useCallback(
    async (uploadedSessionId?: string) => {
      const id = uploadedSessionId ?? sessionId
      if (!id) {
        // Never silent. A no-op here is indistinguishable from a hang to the
        // candidate, which is exactly how the defect above survived review.
        setState({
          kind: 'error',
          message: 'Your session was lost before we could read your resume. Please try again.',
        })
        return
      }
      setState({ kind: 'assessing' })
      try {
        const analysis = await startLevelAssessment(id)
        setState({ kind: 'ready', analysis })
      } catch (err) {
        setState({
          kind: 'error',
          message: errorMessage(err, 'Could not assess your level. Please try again.'),
        })
      }
    },
    [sessionId],
  )

  const confirmLevel = useCallback(
    async (level: Level) => {
      if (!sessionId) return
      try {
        const result = await submitLevelCorrection(sessionId, level)
        setState((prev) =>
          prev.kind === 'ready' || prev.kind === 'confirmed'
            ? { kind: 'confirmed', analysis: prev.analysis, level, firstQuestion: result.first_question }
            : prev,
        )
      } catch (err) {
        setState({
          kind: 'error',
          message: errorMessage(err, 'Could not send your confirmed level. Please try again.'),
        })
      }
    },
    [sessionId],
  )

  return { state, beginAssessment, confirmLevel }
}

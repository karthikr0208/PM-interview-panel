import { useCallback, useState } from 'react'
import { ApiError, startLevelAssessment, submitLevelCorrection } from './api'
import type { Level, ResumeAnalysis } from './types'

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
  | { kind: 'confirmed'; analysis: ResumeAnalysis; level: Level }
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

  const beginAssessment = useCallback(async () => {
    if (!sessionId) return
    setState({ kind: 'assessing' })
    try {
      const analysis = await startLevelAssessment(sessionId)
      setState({ kind: 'ready', analysis })
    } catch (err) {
      setState({
        kind: 'error',
        message: errorMessage(err, 'Could not assess your level. Please try again.'),
      })
    }
  }, [sessionId])

  const confirmLevel = useCallback(
    async (level: Level) => {
      if (!sessionId) return
      try {
        await submitLevelCorrection(sessionId, level)
        setState((prev) =>
          prev.kind === 'ready' || prev.kind === 'confirmed'
            ? { kind: 'confirmed', analysis: prev.analysis, level }
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

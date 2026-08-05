import { useCallback, useState } from 'react'
import { ApiError, sendInterviewReply } from './api'
import type { InterviewTurn } from './types'

export type InterviewState =
  | { kind: 'asking'; question: InterviewTurn; clarification: string | null }
  | { kind: 'sending'; question: InterviewTurn; clarification: string | null; pending: 'answer' | 'clarify' }
  | { kind: 'done' }
  | { kind: 'error'; question: InterviewTurn; clarification: string | null; message: string }

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback
}

/**
 * Owns the conduct loop from the candidate's side (story 3.3, backend
 * `/session/{id}/interview/reply` from story 3.2): posts an answer or a
 * clarifying question, and interprets whatever the graph paused at (or
 * finished with) next.
 *
 * 🔴 TRAP 2: `next.kind === 'clarification'` does NOT replace the question
 * and does NOT advance `current_q_idx` -- only `ask_question` does that
 * (`answer_clarification_node`'s docstring in `app/graph/build.py`). The
 * candidate still owes the original question, so `question` is carried
 * forward unchanged and only `clarification` is set. A `question` response
 * is the opposite: it replaces `question` and clears `clarification`, which
 * belonged to the question just left behind.
 */
export function useInterview(sessionId: string | null, firstQuestion: InterviewTurn) {
  const [state, setState] = useState<InterviewState>({
    kind: 'asking',
    question: firstQuestion,
    clarification: null,
  })

  const send = useCallback(
    async (type: 'answer' | 'clarify', text: string) => {
      // Guard against double submit (already sending) and against calling
      // after the interview is over (no question left to attach a reply
      // to) -- the surface hides its controls in both cases, but the guard
      // holds even if a stale callback fires anyway. Narrows `state` to
      // 'asking' | 'error', the only two variants carrying a question.
      if (!sessionId || state.kind === 'sending' || state.kind === 'done') return

      const { question, clarification } = state

      setState({ kind: 'sending', question, clarification, pending: type })
      try {
        const result = await sendInterviewReply(sessionId, type, text)
        if (result.done) {
          setState({ kind: 'done' })
          return
        }
        const { next } = result
        if (next.kind === 'clarification') {
          // Original question stands; the clarification is an aside to it.
          setState({ kind: 'asking', question, clarification: next.text })
        } else {
          // A new question replaces the old one, and any clarification tied
          // to the PREVIOUS question no longer applies.
          setState({ kind: 'asking', question: next, clarification: null })
        }
      } catch (err) {
        setState({
          kind: 'error',
          question,
          clarification,
          message: errorMessage(err, 'Could not send your reply. Please try again.'),
        })
      }
    },
    [sessionId, state],
  )

  const submitAnswer = useCallback((text: string) => send('answer', text), [send])
  const askClarification = useCallback((text: string) => send('clarify', text), [send])

  return { state, submitAnswer, askClarification }
}

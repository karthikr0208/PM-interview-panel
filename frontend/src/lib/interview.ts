import { useCallback, useState } from 'react'
import { ApiError, sendInterviewReply } from './api'
import type { InterviewTurn } from './types'

export type InterviewState =
  | { kind: 'asking'; question: InterviewTurn; probe: InterviewTurn | null; clarification: string | null }
  | {
      kind: 'sending'
      question: InterviewTurn
      probe: InterviewTurn | null
      clarification: string | null
      pending: 'answer' | 'clarify'
    }
  | { kind: 'done' }
  | {
      kind: 'error'
      question: InterviewTurn
      probe: InterviewTurn | null
      clarification: string | null
      message: string
    }

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
 * candidate still owes the original question, so `question` (and, since
 * 3.5.5, `probe`) is carried forward unchanged and only `clarification` is
 * set.
 *
 * 🔴 PHASE 3.5.5: `next.kind === 'probe'` (`ask_probe`, `app/graph/build.py`)
 * is the SAME trap wearing a new costume. `_QUESTIONS_THIS_PHASE = 1` means
 * every turn after the opening question is a probe, not a new question --
 * `question` must NEVER be overwritten by one, or the candidate loses the
 * main question they are 45 minutes into answering, which is exactly the
 * clarification bug this story exists to not repeat. Only `probe` advances,
 * and it clears `clarification`, which belonged to whatever came before it.
 *
 * A `next.kind === 'question'` response (not reachable within this phase,
 * since there is only ever one question -- kept for a future phase that
 * reopens `_QUESTIONS_THIS_PHASE`) is the one case that legitimately
 * replaces `question`, and resets both `probe` and `clarification`, which
 * belonged to the question just left behind.
 */
export function useInterview(sessionId: string | null, firstQuestion: InterviewTurn) {
  const [state, setState] = useState<InterviewState>({
    kind: 'asking',
    question: firstQuestion,
    probe: null,
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

      const { question, probe, clarification } = state

      setState({ kind: 'sending', question, probe, clarification, pending: type })
      try {
        const result = await sendInterviewReply(sessionId, type, text)
        if (result.done) {
          setState({ kind: 'done' })
          return
        }
        const { next } = result
        if (next.kind === 'clarification') {
          // Original question AND whatever probe is currently on the table
          // both stand; the clarification is an aside to whichever of them
          // the candidate owes an answer to.
          setState({ kind: 'asking', question, probe, clarification: next.text })
        } else if (next.kind === 'probe') {
          // A follow-up on the SAME main question. `question` is untouched.
          setState({ kind: 'asking', question, probe: next, clarification: null })
        } else {
          // A brand new question replaces the old one AND clears any probe
          // tied to it -- both belonged to the question just left behind.
          setState({ kind: 'asking', question: next, probe: null, clarification: null })
        }
      } catch (err) {
        setState({
          kind: 'error',
          question,
          probe,
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

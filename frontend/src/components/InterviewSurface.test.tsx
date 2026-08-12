import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { InterviewSurface } from './InterviewSurface'
import type { InterviewState } from '../lib/interview'
import type { InterviewTurn } from '../lib/types'

afterEach(cleanup)

const Q1: InterviewTurn = { kind: 'question', text: 'Walk me through a product you shipped end to end.', current_q_idx: 1 }
const P1: InterviewTurn = { kind: 'probe', text: 'You said it grew engagement -- by what metric, specifically?', current_q_idx: 1 }

function noop() {}

describe('InterviewSurface', () => {
  it('reveals the full question text whole, in a single element, on first render', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, probe: null, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    // The whole string, not a prefix -- this is what makes "revealed whole"
    // falsifiable rather than assumed.
    expect(screen.getByText(Q1.text as string)).toBeTruthy()
  })

  it('offers answer and clarify as two distinct controls, each posting its own type', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, probe: null, clarification: null }
    const onSubmitAnswer = vi.fn()
    const onAskClarification = vi.fn()
    render(<InterviewSurface state={state} onSubmitAnswer={onSubmitAnswer} onAskClarification={onAskClarification} />)

    fireEvent.change(screen.getByLabelText(/your answer/i), { target: { value: 'My answer.' } })
    fireEvent.click(screen.getByRole('button', { name: /submit answer/i }))
    expect(onSubmitAnswer).toHaveBeenCalledWith('My answer.')
    expect(onAskClarification).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText(/ask a clarifying question/i), { target: { value: 'What do you mean?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask a clarifying question/i }))
    expect(onAskClarification).toHaveBeenCalledWith('What do you mean?')
  })

  it('shows the clarification as a secondary block without displacing the question', () => {
    const state: InterviewState = {
      kind: 'asking',
      question: Q1,
      probe: null,
      clarification: 'It means the surface you personally owned.',
    }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(Q1.text as string)).toBeTruthy()
    expect(screen.getByText('It means the surface you personally owned.')).toBeTruthy()
  })

  // 🔴 THIS PHASE'S CENTRAL ASSERTION. A probe renders BESIDE the main
  // question, never in place of it -- losing the question on a probe turn
  // is the clarification bug in a new costume. See the mutation
  // falsification below, which proves this assertion can fail.
  it('shows a probe as a distinct follow-up block WITHOUT displacing the main question', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, probe: P1, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(Q1.text as string)).toBeTruthy()
    expect(screen.getByText(/you said it grew engagement/i)).toBeTruthy()
    expect(screen.getByText(/follow-up/i)).toBeTruthy()
  })

  it('shows an explicit empty state before the first probe has arrived', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, probe: null, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(/no follow-up yet/i)).toBeTruthy()
  })

  it('shows a loading skeleton on the probe surface while an answer is being sent, not the probe text', () => {
    const state: InterviewState = { kind: 'sending', question: Q1, probe: null, clarification: null, pending: 'answer' }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(/preparing a follow-up/i)).toBeTruthy()
    expect(screen.queryByText(/no follow-up yet/i)).toBeNull()
  })

  it('keeps showing the CURRENT probe while a clarifying question is in flight, not its loading skeleton', () => {
    const state: InterviewState = { kind: 'sending', question: Q1, probe: P1, clarification: null, pending: 'clarify' }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(/you said it grew engagement/i)).toBeTruthy()
    expect(screen.queryByText(/preparing a follow-up/i)).toBeNull()
  })

  it('strips a dash out of probe text -- the probe is a NEW model-output surface with no inherited guard', () => {
    const probe: InterviewTurn = {
      kind: 'probe',
      text: 'You said it grew engagement — by which metric, specifically?',
      current_q_idx: 1,
    }
    const state: InterviewState = { kind: 'asking', question: Q1, probe, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    const text = document.body.textContent ?? ''
    expect(text).not.toMatch(/[—–]/)
    expect(text).toContain('You said it grew engagement, by which metric, specifically?')
  })

  it('renders the closing state and offers no answer control once done', () => {
    render(<InterviewSurface state={{ kind: 'done' }} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(/end of the interview/i)).toBeTruthy()
    expect(screen.getByText(/your scores are in the panel on the right/i)).toBeTruthy()
    expect(screen.queryByLabelText(/your answer/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /submit answer/i })).toBeNull()
  })

  // Scoring and coaching both shipped (Phases 4 and 5); the closing copy
  // must not still claim they are missing.
  it('does not claim feedback and scoring are unbuilt', () => {
    render(<InterviewSurface state={{ kind: 'done' }} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.queryByText(/not part of this build yet/i)).toBeNull()
  })

  it('renders the coachReport slot in the done state, below the closing card', () => {
    render(
      <InterviewSurface
        state={{ kind: 'done' }}
        onSubmitAnswer={noop}
        onAskClarification={noop}
        coachReport={<p>Coaching notes go here.</p>}
      />,
    )
    expect(screen.getByText('Coaching notes go here.')).toBeTruthy()
  })

  it('does not render the coachReport slot before the done state', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, probe: null, clarification: null }
    render(
      <InterviewSurface
        state={state}
        onSubmitAnswer={noop}
        onAskClarification={noop}
        coachReport={<p>Coaching notes go here.</p>}
      />,
    )
    expect(screen.queryByText('Coaching notes go here.')).toBeNull()
  })

  it('disables controls and shows a skeletal state while sending, never a spinner', () => {
    const state: InterviewState = { kind: 'sending', question: Q1, probe: null, clarification: null, pending: 'answer' }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    // Two skeletal "status" regions while pending 'answer': the probe
    // surface's own loading state (a probe is a real LLM call now, story
    // 3.5.5) alongside the general "Sending your answer" skeleton.
    expect(screen.getAllByRole('status').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByLabelText(/your answer/i)).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: /submit answer/i })).toHaveProperty('disabled', true)
    // No circular spinner element -- v1 §3 Rule 5 bans it. This project has
    // no spinner component to import, so absence is checked by role.
    expect(screen.queryByRole('progressbar')).toBeNull()
  })

  it('shows different loading copy for a pending clarification than a pending answer', () => {
    const state: InterviewState = { kind: 'sending', question: Q1, probe: null, clarification: null, pending: 'clarify' }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(/sending your question/i)).toBeTruthy()
  })

  it('renders the server error message verbatim, and Try again re-submits', () => {
    const state: InterviewState = {
      kind: 'error',
      question: Q1,
      probe: null,
      clarification: null,
      message: 'This session does not belong to you.',
    }
    const onSubmitAnswer = vi.fn()
    render(<InterviewSurface state={state} onSubmitAnswer={onSubmitAnswer} onAskClarification={noop} />)

    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText('This session does not belong to you.')).toBeTruthy()

    // The candidate's answer text survives the error (component-local input
    // state is not cleared on failure), so Try again resends it.
    fireEvent.change(screen.getByLabelText(/your answer/i), { target: { value: 'My answer.' } })
    fireEvent.click(screen.getByRole('button', { name: /submit answer/i }))
    onSubmitAnswer.mockClear()

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onSubmitAnswer).toHaveBeenCalledWith('My answer.')
  })

  it('disables submit on empty input, and says why once the field is touched', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, probe: null, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByRole('button', { name: /submit answer/i })).toHaveProperty('disabled', true)

    // The hint is gated on `touched` since 2026-08-07. A freshly served
    // question showed both hints before the candidate had clicked anything,
    // which reads as an error state on arrival.
    expect(screen.queryByText(/write an answer before submitting/i)).toBeNull()

    fireEvent.blur(screen.getByLabelText(/your answer/i))
    expect(screen.getByText(/write an answer before submitting/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: /submit answer/i })).toHaveProperty('disabled', true)
  })

  it('never shows either input hint on a freshly served question', () => {
    // The regression this guards, observed live 2026-08-07: BOTH hints were
    // rendered on arrival, because each was gated only on the field being
    // empty, which it always is before anyone types.
    const state: InterviewState = { kind: 'asking', question: Q1, probe: null, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.queryByText(/write an answer before submitting/i)).toBeNull()
    expect(screen.queryByText(/type a question first/i)).toBeNull()
  })

  it('disables submit on whitespace-only input', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, probe: null, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    fireEvent.change(screen.getByLabelText(/your answer/i), { target: { value: '   ' } })
    expect(screen.getByRole('button', { name: /submit answer/i })).toHaveProperty('disabled', true)
  })

  it('strips an em-dash and an en-dash out of rendered model output', () => {
    const question: InterviewTurn = {
      kind: 'question',
      text: 'Tell me about a hard call you made — one with real tradeoffs.',
      current_q_idx: 1,
    }
    const state: InterviewState = {
      kind: 'asking',
      question,
      probe: null,
      clarification: 'It is the 2016–2019 window specifically.',
    }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    const text = document.body.textContent ?? ''
    expect(text).not.toMatch(/[—–]/)
    expect(text).toContain('Tell me about a hard call you made, one with real tradeoffs.')
    expect(text).toContain('It is the 2016 to 2019 window specifically.')
  })
})

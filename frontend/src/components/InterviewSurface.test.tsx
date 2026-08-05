import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { InterviewSurface } from './InterviewSurface'
import type { InterviewState } from '../lib/interview'
import type { InterviewTurn } from '../lib/types'

afterEach(cleanup)

const Q1: InterviewTurn = { kind: 'question', text: 'Walk me through a product you shipped end to end.', current_q_idx: 1 }

function noop() {}

describe('InterviewSurface', () => {
  it('reveals the full question text whole, in a single element, on first render', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    // The whole string, not a prefix -- this is what makes "revealed whole"
    // falsifiable rather than assumed.
    expect(screen.getByText(Q1.text as string)).toBeTruthy()
  })

  it('offers answer and clarify as two distinct controls, each posting its own type', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, clarification: null }
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
      clarification: 'It means the surface you personally owned.',
    }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(Q1.text as string)).toBeTruthy()
    expect(screen.getByText('It means the surface you personally owned.')).toBeTruthy()
  })

  it('renders the closing state and offers no answer control once done', () => {
    render(<InterviewSurface state={{ kind: 'done' }} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(/end of the interview/i)).toBeTruthy()
    expect(screen.queryByLabelText(/your answer/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /submit answer/i })).toBeNull()
  })

  it('disables controls and shows a skeletal state while sending, never a spinner', () => {
    const state: InterviewState = { kind: 'sending', question: Q1, clarification: null, pending: 'answer' }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByRole('status')).toBeTruthy()
    expect(screen.getByLabelText(/your answer/i)).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: /submit answer/i })).toHaveProperty('disabled', true)
    // No circular spinner element -- v1 §3 Rule 5 bans it. This project has
    // no spinner component to import, so absence is checked by role.
    expect(screen.queryByRole('progressbar')).toBeNull()
  })

  it('shows different loading copy for a pending clarification than a pending answer', () => {
    const state: InterviewState = { kind: 'sending', question: Q1, clarification: null, pending: 'clarify' }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByText(/sending your question/i)).toBeTruthy()
  })

  it('renders the server error message verbatim, and Try again re-submits', () => {
    const state: InterviewState = {
      kind: 'error',
      question: Q1,
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

  it('disables submit on empty input, and says why', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, clarification: null }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    expect(screen.getByRole('button', { name: /submit answer/i })).toHaveProperty('disabled', true)
    expect(screen.getByText(/write an answer before submitting/i)).toBeTruthy()
  })

  it('disables submit on whitespace-only input', () => {
    const state: InterviewState = { kind: 'asking', question: Q1, clarification: null }
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
      clarification: 'It is the 2016–2019 window specifically.',
    }
    render(<InterviewSurface state={state} onSubmitAnswer={noop} onAskClarification={noop} />)
    const text = document.body.textContent ?? ''
    expect(text).not.toMatch(/[—–]/)
    expect(text).toContain('Tell me about a hard call you made, one with real tradeoffs.')
    expect(text).toContain('It is the 2016 to 2019 window specifically.')
  })
})

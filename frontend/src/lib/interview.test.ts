import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import type { InterviewTurn } from './types'

const { sendInterviewReply } = vi.hoisted(() => ({
  sendInterviewReply: vi.fn(),
}))

vi.mock('./api', () => {
  class ApiError extends Error {}
  return { sendInterviewReply, ApiError }
})

const { useInterview } = await import('./interview')
const { ApiError } = await import('./api')

const Q1: InterviewTurn = { kind: 'question', text: 'Walk me through a product you shipped.', current_q_idx: 1 }
const Q2: InterviewTurn = { kind: 'question', text: 'How would you prioritize this backlog?', current_q_idx: 2 }

describe('useInterview', () => {
  beforeEach(() => {
    sendInterviewReply.mockReset()
  })

  it('starts asking the first question handed to it', () => {
    const { result } = renderHook(() => useInterview('sess-1', Q1))
    expect(result.current.state).toEqual({ kind: 'asking', question: Q1, clarification: null })
  })

  it('goes through "sending" before resolving, giving the surface a real loading state', async () => {
    let resolveReply: (value: unknown) => void = () => {}
    sendInterviewReply.mockImplementation(() => new Promise((resolve) => { resolveReply = resolve }))
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    let submitPromise!: Promise<void>
    act(() => {
      submitPromise = result.current.submitAnswer('My answer.')
    })
    expect(result.current.state).toEqual({ kind: 'sending', question: Q1, clarification: null, pending: 'answer' })

    await act(async () => {
      resolveReply({ session_id: 'sess-1', done: false, next: Q2 })
      await submitPromise
    })
  })

  it('posts type "answer" for submitAnswer and type "clarify" for askClarification, separately', async () => {
    sendInterviewReply.mockResolvedValue({ session_id: 'sess-1', done: false, next: Q1 })
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    await act(async () => {
      await result.current.submitAnswer('An answer.')
    })
    expect(sendInterviewReply).toHaveBeenCalledWith('sess-1', 'answer', 'An answer.')

    sendInterviewReply.mockClear()
    await act(async () => {
      await result.current.askClarification('What do you mean by scope?')
    })
    expect(sendInterviewReply).toHaveBeenCalledWith('sess-1', 'clarify', 'What do you mean by scope?')
  })

  // 🔴 TRAP 2, the most important assertion in this story. A clarification
  // response must NOT replace the question and must NOT advance
  // current_q_idx -- only `ask_question` does that.
  it('on a clarification response, leaves the ORIGINAL question on screen and does not advance current_q_idx', async () => {
    sendInterviewReply.mockResolvedValue({
      session_id: 'sess-1',
      done: false,
      next: { kind: 'clarification', text: 'It means the surface you personally owned.', current_q_idx: 1 },
    })
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    await act(async () => {
      await result.current.askClarification('What do you mean by scope?')
    })

    expect(result.current.state).toEqual({
      kind: 'asking',
      question: Q1,
      clarification: 'It means the surface you personally owned.',
    })
  })

  it('on a question response, replaces the question and clears any previous clarification', async () => {
    sendInterviewReply.mockResolvedValueOnce({
      session_id: 'sess-1',
      done: false,
      next: { kind: 'clarification', text: 'Clarified.', current_q_idx: 1 },
    })
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    await act(async () => {
      await result.current.askClarification('question?')
    })
    expect(result.current.state).toEqual({ kind: 'asking', question: Q1, clarification: 'Clarified.' })

    sendInterviewReply.mockResolvedValueOnce({ session_id: 'sess-1', done: false, next: Q2 })
    await act(async () => {
      await result.current.submitAnswer('answer')
    })

    expect(result.current.state).toEqual({ kind: 'asking', question: Q2, clarification: null })
  })

  it('moves to "done" once the graph reports done: true', async () => {
    sendInterviewReply.mockResolvedValue({ session_id: 'sess-1', done: true })
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    await act(async () => {
      await result.current.submitAnswer('final answer')
    })

    expect(result.current.state).toEqual({ kind: 'done' })
  })

  it('on failure, moves to "error" while carrying the question and clarification forward', async () => {
    sendInterviewReply.mockRejectedValue(new ApiError('This session does not belong to you.'))
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    await act(async () => {
      await result.current.submitAnswer('answer')
    })

    expect(result.current.state).toEqual({
      kind: 'error',
      question: Q1,
      clarification: null,
      message: 'This session does not belong to you.',
    })
  })

  it('falls back to generic copy on a non-API error', async () => {
    sendInterviewReply.mockRejectedValue(new Error('network down'))
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    await act(async () => {
      await result.current.submitAnswer('answer')
    })

    expect(result.current.state).toEqual({
      kind: 'error',
      question: Q1,
      clarification: null,
      message: 'Could not send your reply. Please try again.',
    })
  })

  it('ignores a second submit while one is already in flight', async () => {
    let resolveReply: (value: unknown) => void = () => {}
    sendInterviewReply.mockImplementation(() => new Promise((resolve) => { resolveReply = resolve }))
    const { result } = renderHook(() => useInterview('sess-1', Q1))

    act(() => {
      void result.current.submitAnswer('first')
    })
    await act(async () => {
      await result.current.submitAnswer('second')
    })

    expect(sendInterviewReply).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolveReply({ session_id: 'sess-1', done: true })
    })
  })
})

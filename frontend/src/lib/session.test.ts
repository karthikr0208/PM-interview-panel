import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'

const { createSession } = vi.hoisted(() => ({ createSession: vi.fn() }))

vi.mock('./api', () => ({ createSession }))

const { useCandidateSession } = await import('./session')

describe('useCandidateSession', () => {
  beforeEach(() => {
    createSession.mockReset()
  })

  it('creates a session on first use and returns its id', async () => {
    createSession.mockResolvedValue({ session_id: 'sess-1' })
    const { result } = renderHook(() => useCandidateSession())

    expect(result.current.sessionId).toBeNull()

    let id = ''
    await act(async () => {
      id = await result.current.getOrCreateSessionId()
    })

    expect(id).toBe('sess-1')
    expect(createSession).toHaveBeenCalledTimes(1)
  })

  it('reuses the same session across repeated calls -- the 1.6a defect this story fixes', async () => {
    createSession.mockResolvedValue({ session_id: 'sess-1' })
    const { result } = renderHook(() => useCandidateSession())

    let first = ''
    await act(async () => {
      first = await result.current.getOrCreateSessionId()
    })
    let second = ''
    await act(async () => {
      second = await result.current.getOrCreateSessionId()
    })

    expect(first).toBe('sess-1')
    expect(second).toBe('sess-1')
    // The whole point of the fix: a rejected upload plus a retry must not
    // orphan a second `sessions` row.
    expect(createSession).toHaveBeenCalledTimes(1)
  })

  it('collapses two concurrent calls into a single createSession request', async () => {
    let resolveCreate: (value: { session_id: string }) => void = () => {}
    createSession.mockImplementation(
      () => new Promise((resolve) => { resolveCreate = resolve }),
    )
    const { result } = renderHook(() => useCandidateSession())

    let firstPromise!: Promise<string>
    let secondPromise!: Promise<string>
    act(() => {
      firstPromise = result.current.getOrCreateSessionId()
      secondPromise = result.current.getOrCreateSessionId()
    })

    await act(async () => {
      resolveCreate({ session_id: 'sess-1' })
      await Promise.all([firstPromise, secondPromise])
    })

    expect(await firstPromise).toBe('sess-1')
    expect(await secondPromise).toBe('sess-1')
    expect(createSession).toHaveBeenCalledTimes(1)
  })

  it('allows a retry to create a fresh session after a failed attempt', async () => {
    createSession.mockRejectedValueOnce(new Error('network down'))
    createSession.mockResolvedValueOnce({ session_id: 'sess-2' })
    const { result } = renderHook(() => useCandidateSession())

    await act(async () => {
      await expect(result.current.getOrCreateSessionId()).rejects.toThrow('network down')
    })

    let id = ''
    await act(async () => {
      id = await result.current.getOrCreateSessionId()
    })

    expect(id).toBe('sess-2')
    expect(createSession).toHaveBeenCalledTimes(2)
  })
})

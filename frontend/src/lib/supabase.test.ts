import { beforeEach, describe, expect, it, vi } from 'vitest'

// Mocked so this test never touches real Supabase (per the brief: mock the
// network, do not hit the real backend or Supabase from a unit test).
// vi.mock factories are hoisted above imports, so the fns they close over
// must be created via vi.hoisted rather than a plain top-level const.
const { getSession, signInAnonymously } = vi.hoisted(() => ({
  getSession: vi.fn(),
  signInAnonymously: vi.fn(),
}))

vi.mock('@supabase/supabase-js', () => ({
  createClient: () => ({
    auth: { getSession, signInAnonymously },
  }),
}))

const { ensureAnonymousSession } = await import('./supabase')

describe('ensureAnonymousSession', () => {
  beforeEach(() => {
    getSession.mockReset()
    signInAnonymously.mockReset()
  })

  it('reuses an existing session instead of minting a second identity', async () => {
    const existing = { access_token: 'existing-token', user: { id: 'u1' } }
    getSession.mockResolvedValue({ data: { session: existing } })

    const result = await ensureAnonymousSession()

    expect(result).toBe(existing)
    expect(signInAnonymously).not.toHaveBeenCalled()
  })

  it('signs in anonymously only when no session is already persisted', async () => {
    getSession.mockResolvedValue({ data: { session: null } })
    const fresh = { access_token: 'fresh-token', user: { id: 'u2' } }
    signInAnonymously.mockResolvedValue({ data: { session: fresh }, error: null })

    const result = await ensureAnonymousSession()

    expect(result).toBe(fresh)
    expect(signInAnonymously).toHaveBeenCalledTimes(1)
  })

  it('throws rather than returning a session when sign-in fails', async () => {
    getSession.mockResolvedValue({ data: { session: null } })
    signInAnonymously.mockResolvedValue({
      data: { session: null },
      error: { message: 'network down' },
    })

    await expect(ensureAnonymousSession()).rejects.toThrow()
  })
})

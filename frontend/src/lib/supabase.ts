import { createClient, type Session } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Persists to localStorage by default -- do not disable it. Anonymous users
// are never garbage-collected by Supabase, so a reload that mints a fresh
// identity both orphans the candidate's session and bloats the auth table
// (CLAUDE.md § Anonymous sign-in / PHASE-1-SPEC 1.1).
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

/**
 * Silently establishes an identity for the browser. No signup screen, no
 * visible step -- the candidate never sees this happen.
 *
 * Anonymous users carry the `authenticated` role, not `anon` (measured,
 * DEV-STATE 2026-07-31); every RLS policy in this project targets
 * `authenticated`. Reuses whatever session supabase-js already restored from
 * localStorage before minting a new one, which is what makes the session
 * survive a page reload instead of orphaning it.
 */
export async function ensureAnonymousSession(): Promise<Session> {
  const { data: existing } = await supabase.auth.getSession()
  if (existing.session) {
    return existing.session
  }

  const { data: created, error } = await supabase.auth.signInAnonymously()
  if (error || !created.session) {
    throw new Error(error?.message ?? 'Could not start a session. Please try again.')
  }
  return created.session
}

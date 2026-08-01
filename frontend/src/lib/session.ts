import { useCallback, useRef, useState } from 'react'
import { createSession } from './api'

/**
 * Owns session creation for one candidate journey. `getOrCreateSessionId`
 * creates a `sessions` row on its first call and caches the in-flight
 * promise, so choosing a file that gets rejected and retrying reuses the
 * SAME session instead of orphaning a new row per attempt -- the defect
 * 1.6a deliberately left for 1.6b (PHASE-1-SPEC.md 1.6b).
 */
export function useCandidateSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const pending = useRef<Promise<string> | null>(null)

  const getOrCreateSessionId = useCallback((): Promise<string> => {
    if (sessionId) return Promise.resolve(sessionId)
    if (!pending.current) {
      pending.current = createSession()
        .then((session) => {
          setSessionId(session.session_id)
          return session.session_id
        })
        .catch((err) => {
          // A failed attempt must not permanently wedge the journey -- the
          // next retry gets a fresh createSession() call rather than
          // replaying a rejected promise forever.
          pending.current = null
          throw err
        })
    }
    return pending.current
  }, [sessionId])

  return { sessionId, getOrCreateSessionId }
}

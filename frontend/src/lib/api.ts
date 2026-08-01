import { ensureAnonymousSession } from './supabase'
import type { Level, ResumeAnalysis } from './types'

const API_URL = import.meta.env.VITE_API_URL

/**
 * Thrown for any backend response the server rejected. `message` is the
 * server's own `detail` string. Those strings are already written for the
 * candidate to read (see backend/app/resume.py's docstrings) -- callers
 * render `.message` directly rather than composing new copy on top of it.
 */
export class ApiError extends Error {}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body: unknown = await res.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
    }
  } catch {
    // Body was not JSON (e.g. a proxy error page). Fall through.
  }
  return `Request failed with status ${res.status}.`
}

export async function createSession(): Promise<{ session_id: string }> {
  const session = await ensureAnonymousSession()
  const res = await fetch(`${API_URL}/session`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.access_token}` },
  })
  if (!res.ok) {
    throw new ApiError(await parseErrorDetail(res))
  }
  return res.json()
}

export type UploadPhase = 'uploading' | 'parsing'

interface UploadResumeResult {
  resume_id: string
  storage_path: string
}

/**
 * Uploads a resume via XMLHttpRequest rather than fetch. Only XHR's upload
 * progress events distinguish "the bytes are still on the wire" from "the
 * bytes arrived and the server is now extracting text" -- that is the
 * uploading/parsing state boundary PHASE-1-SPEC 1.6 requires, and fetch has
 * no equivalent signal.
 */
export function uploadResumeFile(
  sessionId: string,
  file: File,
  onPhaseChange: (phase: UploadPhase) => void,
): Promise<UploadResumeResult> {
  return ensureAnonymousSession().then(
    (session) =>
      new Promise<UploadResumeResult>((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        const formData = new FormData()
        formData.append('file', file)

        xhr.open('POST', `${API_URL}/session/${sessionId}/resume`)
        xhr.setRequestHeader('Authorization', `Bearer ${session.access_token}`)

        // Fires once every byte has left the browser -- the request is now
        // sitting on the server, which is doing extraction synchronously.
        xhr.upload.addEventListener('load', () => onPhaseChange('parsing'))

        xhr.addEventListener('load', () => {
          let body: unknown = null
          try {
            body = JSON.parse(xhr.responseText)
          } catch {
            // Non-JSON body; handled as a generic failure below if not 2xx.
          }
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(body as UploadResumeResult)
            return
          }
          const detail =
            body &&
            typeof body === 'object' &&
            typeof (body as { detail?: unknown }).detail === 'string'
              ? (body as { detail: string }).detail
              : `Request failed with status ${xhr.status}.`
          reject(new ApiError(detail))
        })

        xhr.addEventListener('error', () => {
          reject(
            new ApiError('Could not reach the server. Please check your connection and try again.'),
          )
        })

        xhr.send(formData)
      }),
  )
}

/**
 * Runs the Resume Analyst (`level_candidate`) and returns the payload the
 * graph paused at `confirm_level` with. Its shape mirrors `ResumeAnalysis`
 * exactly (`lib/types.ts` mirrors `app/agents/resume_analyst.py`'s Pydantic
 * models field for field), so the response can be handed straight to
 * `ConfirmationScreen`.
 *
 * Idempotent from the caller's side: calling this twice for the same
 * session (a retry, a re-render) returns the SAME assessment rather than
 * running the Resume Analyst again -- the backend route checks for an
 * existing paused interrupt before invoking the graph (app/main.py).
 */
export async function startLevelAssessment(sessionId: string): Promise<ResumeAnalysis> {
  const session = await ensureAnonymousSession()
  const res = await fetch(`${API_URL}/session/${sessionId}/level`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.access_token}` },
  })
  if (!res.ok) {
    throw new ApiError(await parseErrorDetail(res))
  }
  return res.json()
}

export interface LevelConfirmationResult {
  session_id: string
  level: Level
  /** True when the candidate's chosen level differs from the level the
   * Resume Analyst originally assessed -- computed by the backend, which
   * has both values, rather than trusted from the caller. */
  corrected: boolean
}

/**
 * Resumes the paused `confirm_level` interrupt with the candidate's chosen
 * level (`ConfirmationScreen`'s `onConfirm` contract), so the backend can
 * carry it into `Command(resume=...)` and persist it to `sessions.level`.
 */
export async function submitLevelCorrection(
  sessionId: string,
  level: Level,
): Promise<LevelConfirmationResult> {
  const session = await ensureAnonymousSession()
  const res = await fetch(`${API_URL}/session/${sessionId}/level/confirm`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ level }),
  })
  if (!res.ok) {
    throw new ApiError(await parseErrorDetail(res))
  }
  return res.json()
}

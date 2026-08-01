import { ensureAnonymousSession } from './supabase'
import type { Level } from './types'

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
 * SEAM FOR STORY 1.4 — not called from anywhere in this codebase yet.
 *
 * `confirm_level`'s HTTP route does not exist until story 1.4 builds the
 * `level_candidate` -> `confirm_level` graph nodes (PHASE-1-SPEC.md 1.4).
 * When it lands, this is where a candidate's chosen level should be POSTed
 * so the backend can carry it into `Command(resume=...)` and resume the
 * paused interrupt. Until then, `ConfirmationScreen` takes an `onConfirm`
 * callback prop instead of importing this function directly, so the
 * component stays fully testable against fixtures and 1.4 can wire this
 * function into that callback without touching `ConfirmationScreen` itself.
 */
export async function submitLevelCorrection(_sessionId: string, _level: Level): Promise<never> {
  throw new Error('submitLevelCorrection is a seam for story 1.4. No backend route exists yet.')
}

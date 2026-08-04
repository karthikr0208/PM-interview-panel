import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

afterEach(cleanup)

/**
 * 🔴 THE REGRESSION THIS FILE EXISTS FOR, observed in production 2026-08-04.
 *
 * Karthik uploaded a real CV. It uploaded cleanly, and the Resume Analyst sat
 * on "Waiting to start" forever. Nothing errored, in the browser or the
 * backend, because nothing failed: the handoff simply never happened.
 *
 * The first file is chosen while `useCandidateSession`'s `sessionId` is still
 * null, so `UploadSurface`'s async handler captures an `onUploadComplete` from
 * that render, and `beginAssessment`'s `useCallback([sessionId])` closed over
 * null too. The upload created the session and succeeded, called the captured
 * callback, and `if (!sessionId) return` swallowed it.
 *
 * The whole defect lives in the SEAM between three components that each had
 * passing tests, which is why it needs an App-level test: `UploadSurface`,
 * `useCandidateSession` and `useLevelAssessment` were all individually
 * correct. Anything that mounts them separately, or seeds a session id, cannot
 * see it. This test therefore starts from a null session, exactly as a real
 * candidate does.
 */

const { createSession, uploadResumeFile, startLevelAssessment } = vi.hoisted(() => ({
  createSession: vi.fn(),
  uploadResumeFile: vi.fn(),
  startLevelAssessment: vi.fn(),
}))

vi.mock('./lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./lib/api')>()
  return { ...actual, createSession, uploadResumeFile, startLevelAssessment }
})

// The orchestration column subscribes to Supabase Realtime; stub it so this
// test is about the upload -> assessment handoff and nothing else.
vi.mock('./lib/agentEvents', () => ({ useAgentEvents: () => [] }))

const SESSION_ID = 'sess-from-upload'

function pdf(): File {
  return new File([new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d])], 'CV_Karthik.pdf', {
    type: 'application/pdf',
  })
}

/** Same mechanism as UploadSurface.test.tsx -- this project has no
 * `@testing-library/user-event`, and adding a dependency for one helper is
 * not worth it. */
function uploadResume(): void {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  fireEvent.change(input, { target: { files: [pdf()] } })
}

describe('App: upload hands off to the Resume Analyst', () => {
  beforeEach(() => {
    createSession.mockReset()
    uploadResumeFile.mockReset()
    startLevelAssessment.mockReset()

    // Session does not exist until the upload asks for it, which is the
    // precondition for the bug.
    createSession.mockResolvedValue({ session_id: SESSION_ID })
    uploadResumeFile.mockResolvedValue({ resume_id: 'r-1', storage_path: 'p/1' })
    startLevelAssessment.mockResolvedValue({
      candidate_profile: {
        years_pm_experience: 8,
        domains: ['insurance'],
        product_types: ['AI solutions'],
        company_contexts: ['large enterprise'],
        scope_evidence: ['owned the thing end to end'],
        notable_outcomes: ['cut it by 65%'],
        people_leadership: null,
      },
      assessed_level: 'Senior PM',
      level_rationale: 'Owned a product line and set its strategy for several quarters.',
      low_confidence_fields: [],
    })
  })

  it('starts the assessment after an upload that created the session', async () => {
    render(<App />)
    uploadResume()

    await waitFor(() => expect(startLevelAssessment).toHaveBeenCalled())
    expect(startLevelAssessment).toHaveBeenCalledWith(SESSION_ID)
  })

  it('leaves the upload surface and shows the confirmation screen', async () => {
    // The user-visible half of the same defect: production stayed on the
    // upload surface's "Resume received" state, so asserting only that the
    // API was called would miss a regression that never renders.
    render(<App />)
    uploadResume()

    await waitFor(() => expect(screen.getByText(/senior pm/i)).toBeTruthy())
    expect(screen.queryByText(/upload a different resume/i)).toBeNull()
  })

  it('surfaces an error rather than hanging when there is no session at all', async () => {
    // The guard that replaced the silent `return`. A no-op is
    // indistinguishable from a hang to the candidate, which is how the
    // original defect survived review.
    createSession.mockRejectedValue(new Error('session service down'))

    render(<App />)
    uploadResume()

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(startLevelAssessment).not.toHaveBeenCalled()
  })
})

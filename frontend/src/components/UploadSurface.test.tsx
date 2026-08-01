import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { UploadSurface } from './UploadSurface'
import { uploadResumeFile } from '../lib/api'

// This project has no global vitest setup file (the story 1.6a brief's
// file list does not include one), so @testing-library/react's DOM does
// not auto-clean between tests the way it would under `globals: true` plus
// a setupFiles entry. Clean up explicitly instead of accumulating renders.
afterEach(cleanup)

// Mocked so this test never hits the real backend, per the brief.
vi.mock('../lib/api', () => {
  class ApiError extends Error {}
  return {
    uploadResumeFile: vi.fn(),
    ApiError,
  }
})

function selectFile(name = 'resume.pdf', type = 'application/pdf') {
  const input = screen.getByLabelText(/resume/i) as HTMLInputElement
  const file = new File(['file contents'], name, { type })
  fireEvent.change(input, { target: { files: [file] } })
  return file
}

describe('UploadSurface', () => {
  let getOrCreateSessionId: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.mocked(uploadResumeFile).mockReset()
    getOrCreateSessionId = vi.fn().mockResolvedValue('sess-1')
  })

  it('renders the idle state by default', () => {
    render(<UploadSurface getOrCreateSessionId={getOrCreateSessionId} />)
    expect(screen.getByText(/upload your resume/i)).toBeTruthy()
  })

  it('walks through uploading, then parsing, then a success state', async () => {
    let capturedPhaseChange: ((phase: 'uploading' | 'parsing') => void) | null = null
    let resolveUpload: (value: { resume_id: string; storage_path: string }) => void = () => {}
    vi.mocked(uploadResumeFile).mockImplementation(
      (_sessionId, _file, onPhaseChange) =>
        new Promise((resolve) => {
          capturedPhaseChange = onPhaseChange
          resolveUpload = resolve
        }),
    )

    render(<UploadSurface getOrCreateSessionId={getOrCreateSessionId} />)
    selectFile()

    // Fires the instant the component starts the request -- before
    // uploadResumeFile's own onPhaseChange callback ever runs.
    await waitFor(() => expect(screen.getByText(/^uploading$/i)).toBeTruthy())

    capturedPhaseChange?.('parsing')
    await waitFor(() => expect(screen.getByText(/reading your resume/i)).toBeTruthy())

    resolveUpload({ resume_id: 'r1', storage_path: 'sess-1/resume.pdf' })
    await waitFor(() => expect(screen.getByText(/resume received/i)).toBeTruthy())
  })

  it('renders the backend detail string verbatim on a rejected upload', async () => {
    const { ApiError } = await import('../lib/api')
    vi.mocked(uploadResumeFile).mockRejectedValue(
      new ApiError(
        'This PDF has no extractable text. It looks like a scanned or image-only document.',
      ),
    )

    render(<UploadSurface getOrCreateSessionId={getOrCreateSessionId} />)
    selectFile()

    await waitFor(() =>
      expect(screen.getByText(/this pdf has no extractable text/i)).toBeTruthy(),
    )
  })

  it('rejects an unsupported file client-side without ever asking for a session', async () => {
    render(<UploadSurface getOrCreateSessionId={getOrCreateSessionId} />)
    selectFile('resume.txt', 'text/plain')

    await waitFor(() => expect(screen.getByText(/please choose a pdf or docx file/i)).toBeTruthy())
    expect(getOrCreateSessionId).not.toHaveBeenCalled()
  })

  it('returns to idle from an error state via Try again', async () => {
    render(<UploadSurface getOrCreateSessionId={getOrCreateSessionId} />)
    selectFile('resume.txt', 'text/plain')
    await waitFor(() => expect(screen.getByText(/please choose a pdf or docx file/i)).toBeTruthy())

    fireEvent.click(screen.getByText(/try again/i))

    expect(screen.getByText(/upload your resume/i)).toBeTruthy()
  })

  it('reuses the SAME session across a rejected upload and a retry (1.6a defect, fixed in 1.6b)', async () => {
    // First attempt: the backend rejects it (e.g. a scanned PDF). Second
    // attempt: it succeeds. getOrCreateSessionId must be called both times
    // (UploadSurface always asks), but it is the CALLER's job (lib/session.ts,
    // tested separately) to return the same id both times -- this test
    // proves UploadSurface asks every time rather than caching its own copy
    // and silently going stale, which would be the opposite bug.
    const { ApiError } = await import('../lib/api')
    vi.mocked(uploadResumeFile)
      .mockRejectedValueOnce(new ApiError('This PDF has no extractable text.'))
      .mockResolvedValueOnce({ resume_id: 'r1', storage_path: 'sess-1/resume.pdf' })

    render(<UploadSurface getOrCreateSessionId={getOrCreateSessionId} />)

    selectFile()
    await waitFor(() => expect(screen.getByText(/this pdf has no extractable text/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/try again/i))

    selectFile()
    await waitFor(() => expect(screen.getByText(/resume received/i)).toBeTruthy())

    expect(getOrCreateSessionId).toHaveBeenCalledTimes(2)
    // Both calls asked the SAME provider with no arguments -- it is
    // getOrCreateSessionId's own memoization (lib/session.test.ts) that
    // turns these two calls into one session, not anything UploadSurface
    // does on its own.
    const sessionIdsUsed = vi.mocked(uploadResumeFile).mock.calls.map((call) => call[0])
    expect(sessionIdsUsed).toEqual(['sess-1', 'sess-1'])
  })
})

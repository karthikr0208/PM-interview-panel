import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { UploadSurface } from './UploadSurface'
import { createSession, uploadResumeFile } from '../lib/api'

// This project has no global vitest setup file (the story 1.6a brief's
// file list does not include one), so @testing-library/react's DOM does
// not auto-clean between tests the way it would under `globals: true` plus
// a setupFiles entry. Clean up explicitly instead of accumulating renders.
afterEach(cleanup)

// Mocked so this test never hits the real backend, per the brief.
vi.mock('../lib/api', () => {
  class ApiError extends Error {}
  return {
    createSession: vi.fn(),
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
  beforeEach(() => {
    vi.mocked(createSession).mockReset()
    vi.mocked(uploadResumeFile).mockReset()
  })

  it('renders the idle state by default', () => {
    render(<UploadSurface />)
    expect(screen.getByText(/upload your resume/i)).toBeTruthy()
  })

  it('walks through uploading, then parsing, then a success state', async () => {
    vi.mocked(createSession).mockResolvedValue({ session_id: 'sess-1' })

    let capturedPhaseChange: ((phase: 'uploading' | 'parsing') => void) | null = null
    let resolveUpload: (value: { resume_id: string; storage_path: string }) => void = () => {}
    vi.mocked(uploadResumeFile).mockImplementation(
      (_sessionId, _file, onPhaseChange) =>
        new Promise((resolve) => {
          capturedPhaseChange = onPhaseChange
          resolveUpload = resolve
        }),
    )

    render(<UploadSurface />)
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
    vi.mocked(createSession).mockResolvedValue({ session_id: 'sess-1' })
    const { ApiError } = await import('../lib/api')
    vi.mocked(uploadResumeFile).mockRejectedValue(
      new ApiError(
        'This PDF has no extractable text. It looks like a scanned or image-only document.',
      ),
    )

    render(<UploadSurface />)
    selectFile()

    await waitFor(() =>
      expect(screen.getByText(/this pdf has no extractable text/i)).toBeTruthy(),
    )
  })

  it('rejects an unsupported file client-side without calling the backend', async () => {
    render(<UploadSurface />)
    selectFile('resume.txt', 'text/plain')

    await waitFor(() => expect(screen.getByText(/please choose a pdf or docx file/i)).toBeTruthy())
    expect(createSession).not.toHaveBeenCalled()
  })

  it('returns to idle from an error state via Try again', async () => {
    render(<UploadSurface />)
    selectFile('resume.txt', 'text/plain')
    await waitFor(() => expect(screen.getByText(/please choose a pdf or docx file/i)).toBeTruthy())

    fireEvent.click(screen.getByText(/try again/i))

    expect(screen.getByText(/upload your resume/i)).toBeTruthy()
  })
})

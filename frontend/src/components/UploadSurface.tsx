import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { CheckCircle, CloudArrowUp, FileText, WarningCircle } from '@phosphor-icons/react'
import { ApiError, uploadResumeFile } from '../lib/api'

type UploadState =
  | { kind: 'idle' }
  | { kind: 'uploading'; fileName: string }
  | { kind: 'parsing'; fileName: string }
  | { kind: 'done'; fileName: string }
  | { kind: 'error'; message: string; technical?: string }

const ACCEPTED_EXTENSIONS = ['.pdf', '.docx']
// A courtesy check for a fast, friendly failure -- NOT the enforcement. The
// backend re-checks type by content inspection (magic bytes, not extension)
// and size (bytes actually received, not a declared Content-Length), and
// its 400 is what a candidate who works around this actually sees.
const CLIENT_SIZE_LIMIT_BYTES = 5 * 1024 * 1024

function clientSideIssue(file: File): string | null {
  const lower = file.name.toLowerCase()
  if (!ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
    return 'Please choose a PDF or DOCX file.'
  }
  if (file.size > CLIENT_SIZE_LIMIT_BYTES) {
    return 'This file is larger than 5MB. Please upload a smaller file.'
  }
  return null
}

function UploadingState({ fileName }: { fileName: string }) {
  return (
    <div className="rounded-card border border-border bg-surface p-6" role="status" aria-live="polite">
      <div className="flex items-center gap-3">
        <FileText size={24} className="shrink-0 text-text-secondary" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">{fileName}</p>
          <p className="mt-1 text-sm text-text-secondary">Uploading</p>
        </div>
      </div>
      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-border">
        <div className="h-full w-2/3 animate-pulse rounded-full bg-accent" />
      </div>
    </div>
  )
}

function ParsingState({ fileName }: { fileName: string }) {
  return (
    <div className="rounded-card border border-border bg-surface p-6" role="status" aria-live="polite">
      <div className="flex items-center gap-3">
        <FileText size={24} className="shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">{fileName}</p>
          <p className="mt-1 text-sm text-text-secondary">Reading your resume</p>
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <div className="h-2 w-full animate-pulse rounded-full bg-border" />
        <div className="h-2 w-5/6 animate-pulse rounded-full bg-border" />
        <div className="h-2 w-2/3 animate-pulse rounded-full bg-border" />
      </div>
    </div>
  )
}

function DoneState({ fileName, onReset }: { fileName: string; onReset: () => void }) {
  return (
    <div className="rounded-card border border-border bg-surface p-6">
      <div className="flex items-center gap-3">
        <CheckCircle size={24} className="shrink-0 text-success" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">{fileName}</p>
          <p className="mt-1 text-sm text-text-secondary">Resume received</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onReset}
        className="mt-4 text-sm font-medium text-accent transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98]"
      >
        Upload a different resume
      </button>
    </div>
  )
}

function ErrorState({
  message,
  technical,
  onRetry,
}: {
  message: string
  technical?: string
  onRetry: () => void
}) {
  return (
    <div className="rounded-card border border-border bg-surface p-6" role="alert">
      <div className="flex items-start gap-3">
        <WarningCircle size={24} className="mt-0.5 shrink-0 text-error" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">We could not process that file</p>
          <p className="mt-1 text-sm text-text-secondary">{message}</p>
          {technical && (
            <details className="mt-2">
              <summary className="cursor-pointer text-sm text-text-secondary">Show details</summary>
              <p className="mt-1 font-mono text-xs text-text-secondary">{technical}</p>
            </details>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-control border border-border bg-surface px-4 py-2 text-sm font-medium text-text-primary transition-transform duration-(--duration-standard) ease-standard active:scale-[0.98]"
      >
        Try again
      </button>
    </div>
  )
}

interface UploadSurfaceProps {
  // Hoisted to the App shell (lib/session.ts) so a rejected file plus a
  // retry reuses the SAME session row instead of orphaning a new one per
  // attempt -- "one candidate journey should be one session"
  // (PHASE-1-SPEC.md 1.6b, a defect 1.6a deliberately left for 1.6b).
  getOrCreateSessionId: () => Promise<string>
  // Optional: fires once the upload reaches `done`. Story 1.4's App.tsx
  // uses this to kick off the Resume Analyst (`level_candidate`) the
  // moment a resume is ready -- UploadSurface itself stays ignorant of what
  // happens after a successful upload, same boundary as `getOrCreateSessionId`.
  //
  // It RECEIVES THE SESSION ID it uploaded against, and that argument is
  // load-bearing: on the first upload the caller's own `sessionId` state is
  // still null when this callback is captured, so a zero-argument version
  // left the caller unable to tell which session to assess. That shipped as
  // a silent hang (see lib/levelAssessment.ts's `beginAssessment`).
  onUploadComplete?: (sessionId: string) => void
}

export function UploadSurface({ getOrCreateSessionId, onUploadComplete }: UploadSurfaceProps) {
  const [state, setState] = useState<UploadState>({ kind: 'idle' })
  const inputRef = useRef<HTMLInputElement>(null)

  const reset = useCallback(() => setState({ kind: 'idle' }), [])

  const handleFile = useCallback(async (file: File) => {
    const issue = clientSideIssue(file)
    if (issue) {
      setState({ kind: 'error', message: issue })
      return
    }

    setState({ kind: 'uploading', fileName: file.name })
    try {
      const sessionId = await getOrCreateSessionId()
      await uploadResumeFile(sessionId, file, (phase) => {
        setState({ kind: phase, fileName: file.name })
      })
      setState({ kind: 'done', fileName: file.name })
      onUploadComplete?.(sessionId)
    } catch (err) {
      if (err instanceof ApiError) {
        // Already written for the candidate to read (backend/app/resume.py) --
        // surfaced directly rather than paraphrased.
        setState({ kind: 'error', message: err.message })
      } else {
        setState({
          kind: 'error',
          message: 'Could not reach the server. Please check your connection and try again.',
          technical: err instanceof Error ? err.message : String(err),
        })
      }
    }
  }, [getOrCreateSessionId, onUploadComplete])

  const handleInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      event.target.value = ''
      if (file) void handleFile(file)
    },
    [handleFile],
  )

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault()
      const file = event.dataTransfer.files?.[0]
      if (file) void handleFile(file)
    },
    [handleFile],
  )

  return (
    <div className="mx-auto max-w-xl">
      {state.kind === 'idle' && (
        <div>
          <label htmlFor="resume-upload" className="mb-2 block text-sm font-medium text-text-primary">
            Resume
          </label>
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                inputRef.current?.click()
              }
            }}
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
            className="cursor-pointer rounded-card border border-dashed border-border bg-surface p-8 text-center transition-colors duration-(--duration-standard) ease-standard hover:border-accent"
          >
            <CloudArrowUp size={32} className="mx-auto mb-3 text-text-secondary" />
            <p className="text-sm font-medium text-text-primary">Upload your resume</p>
            <p className="mt-1 text-sm text-text-secondary">
              PDF or DOCX, up to 5MB. Click to choose a file, or drag one here.
            </p>
            <input
              ref={inputRef}
              id="resume-upload"
              type="file"
              accept=".pdf,.docx"
              className="sr-only"
              onChange={handleInputChange}
            />
          </div>
        </div>
      )}
      {state.kind === 'uploading' && <UploadingState fileName={state.fileName} />}
      {state.kind === 'parsing' && <ParsingState fileName={state.fileName} />}
      {state.kind === 'done' && <DoneState fileName={state.fileName} onReset={reset} />}
      {state.kind === 'error' && (
        <ErrorState message={state.message} technical={state.technical} onRetry={reset} />
      )}
    </div>
  )
}

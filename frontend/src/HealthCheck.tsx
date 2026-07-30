import { useEffect, useState } from 'react'

// Phase 0 story 0.8: proves VITE_API_URL is actually read at build time and that
// CORS is configured for wherever this bundle ends up running. Deleted in Phase 1.

type Status =
  | { kind: 'loading' }
  | { kind: 'connected'; body: string }
  | { kind: 'error'; message: string }

const API_URL = import.meta.env.VITE_API_URL

const STYLES: Record<Status['kind'], string> = {
  loading: 'border-amber-400/50 bg-amber-400/10 text-amber-700',
  connected: 'border-emerald-400/50 bg-emerald-400/10 text-emerald-700',
  error: 'border-red-400/50 bg-red-400/10 text-red-700',
}

export default function HealthCheck() {
  const [status, setStatus] = useState<Status>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false

    fetch(`${API_URL}/health`)
      .then(async (res) => {
        if (cancelled) return
        if (!res.ok) {
          setStatus({ kind: 'error', message: `Backend responded with HTTP ${res.status}` })
          return
        }
        setStatus({ kind: 'connected', body: await res.text() })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setStatus({
          kind: 'error',
          message: err instanceof Error ? err.message : 'Request failed',
        })
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div
      className={`mx-auto mb-6 max-w-md rounded-md border px-4 py-3 text-left text-sm font-mono ${STYLES[status.kind]}`}
    >
      <div className="font-sans font-medium">Backend connectivity check</div>
      <div className="mt-1 break-all opacity-80">{API_URL}/health</div>
      {status.kind === 'loading' && (
        <div className="mt-2">
          Checking. A sleeping free-tier backend can take under a minute to wake on the first
          request, this is not stuck.
        </div>
      )}
      {status.kind === 'connected' && <div className="mt-2">Response: {status.body}</div>}
      {status.kind === 'error' && <div className="mt-2">Failed: {status.message}</div>}
    </div>
  )
}

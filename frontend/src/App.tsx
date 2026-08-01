import HealthCheck from './HealthCheck'
import { IconStandard } from './lib/icons'
import { useCandidateSession } from './lib/session'
import { AppShell } from './components/AppShell'
import { OrchestrationColumn } from './components/OrchestrationColumn'
import { EvaluationColumn } from './components/EvaluationColumn'
import { UploadSurface } from './components/UploadSurface'

// ConfirmationScreen exists and is fully tested (see
// ConfirmationScreen.test.tsx) but is not mounted here yet: it renders a
// ResumeAnalysis, and nothing produces a real one until story 1.4 builds
// `level_candidate`. Wiring it up with fake data would show a candidate a
// lie. 1.4 mounts it once that data exists, via the `onConfirm` callback
// contract already defined on the component.

function App() {
  // Hoisted here, not inside UploadSurface, so a rejected file plus a retry
  // reuses the SAME session and so OrchestrationColumn can subscribe to the
  // same session's agent_events (PHASE-1-SPEC.md 1.6b).
  const { sessionId, getOrCreateSessionId } = useCandidateSession()

  return (
    <IconStandard>
      <AppShell
        orchestration={<OrchestrationColumn sessionId={sessionId} />}
        conversation={<UploadSurface getOrCreateSessionId={getOrCreateSessionId} />}
        evaluation={<EvaluationColumn />}
      />
      {/* Phase 0 scaffolding. Not deleted here -- story 1.7 removes it, only
          after 1.6 is verified against the real shell above. Kept rendered,
          out of the primary flow, per that story's own constraint. */}
      <div className="border-t border-border p-4">
        <HealthCheck />
      </div>
    </IconStandard>
  )
}

export default App

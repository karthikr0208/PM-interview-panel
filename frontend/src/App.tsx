import HealthCheck from './HealthCheck'
import { IconStandard } from './lib/icons'
import { AppShell } from './components/AppShell'
import { OrchestrationColumn } from './components/OrchestrationColumn'
import { EvaluationColumn } from './components/EvaluationColumn'
import { UploadSurface } from './components/UploadSurface'

function App() {
  return (
    <IconStandard>
      <AppShell
        orchestration={<OrchestrationColumn />}
        conversation={<UploadSurface />}
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

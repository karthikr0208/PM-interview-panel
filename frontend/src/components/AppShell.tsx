import type { ReactNode } from 'react'

interface AppShellProps {
  orchestration: ReactNode
  conversation: ReactNode
  evaluation: ReactNode
}

/**
 * The three-column shell from ARCHITECTURE §8 / DESIGN.md §5: orchestration
 * (280px fixed) · conversation (fluid centre) · live evaluation (320px
 * fixed). Design target is >=1280px (Tailwind's `xl` breakpoint); below that
 * it collapses to a single stacked column, conversation first, rather than a
 * tabbed mobile redesign -- out of scope for this phase.
 */
export function AppShell({ orchestration, conversation, evaluation }: AppShellProps) {
  return (
    <div className="flex min-h-[100dvh] flex-col bg-background xl:flex-row">
      <aside
        aria-label="Agent activity"
        className="order-2 border-t border-border bg-surface p-6 xl:order-1 xl:w-[280px] xl:shrink-0 xl:overflow-y-auto xl:border-t-0 xl:border-r"
      >
        {orchestration}
      </aside>
      <main className="order-1 flex-1 p-6 xl:order-2 xl:overflow-y-auto">{conversation}</main>
      <aside
        aria-label="Live evaluation"
        className="order-3 border-t border-border bg-surface p-6 xl:w-[320px] xl:shrink-0 xl:overflow-y-auto xl:border-t-0 xl:border-l"
      >
        {evaluation}
      </aside>
    </div>
  )
}

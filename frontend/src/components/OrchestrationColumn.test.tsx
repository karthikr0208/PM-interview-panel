import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import { OrchestrationColumn } from './OrchestrationColumn'
import type { AgentEvent } from '../lib/types'

afterEach(cleanup)

const { useAgentEvents } = vi.hoisted(() => ({ useAgentEvents: vi.fn() }))
vi.mock('../lib/agentEvents', () => ({ useAgentEvents }))

function event(overrides: Partial<AgentEvent>): AgentEvent {
  return {
    id: 'evt-1',
    session_id: 'sess-1',
    agent: 'resume_analyst',
    status: 'started',
    summary: null,
    duration_ms: null,
    tokens: null,
    created_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

// Story 2.7 put three rows in this column, so every assertion below is scoped
// to ONE row by its accessible name. An unscoped `getByText('○')` would now
// match three elements and throw, and -- worse -- an unscoped assertion could
// pass on the wrong agent's row entirely.
function row(name: string) {
  return within(screen.getByRole('status', { name }))
}

describe('OrchestrationColumn', () => {
  beforeEach(() => {
    useAgentEvents.mockReset()
  })

  it('renders the WAITING glyph when there is no session yet', () => {
    useAgentEvents.mockReturnValue([])
    render(<OrchestrationColumn sessionId={null} />)
    expect(row('Resume Analyst').getByText('○')).toBeTruthy()
    expect(row('Resume Analyst').getByText('Waiting')).toBeTruthy()
  })

  it('renders the ACTIVE glyph on a started event', () => {
    useAgentEvents.mockReturnValue([event({ status: 'started' })])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Resume Analyst').getByText('◉')).toBeTruthy()
    expect(row('Resume Analyst').getByText('Working')).toBeTruthy()
  })

  it('renders the DONE glyph once a done event lands', () => {
    useAgentEvents.mockReturnValue([
      event({ status: 'done', summary: 'Read your resume and assessed a level' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Resume Analyst').getByText('●')).toBeTruthy()
    expect(row('Resume Analyst').getByText('Done')).toBeTruthy()
  })

  it('renders the ERROR glyph once an error event lands', () => {
    useAgentEvents.mockReturnValue([
      event({ status: 'error', summary: 'Could not read the resume text' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Resume Analyst').getByText('⚠')).toBeTruthy()
    expect(row('Resume Analyst').getByText('Error')).toBeTruthy()
  })

  it('renders four states that are ALL DISTINCT glyphs, not just distinct colours', () => {
    const states: Array<AgentEvent['status'] | undefined> = [undefined, 'started', 'done', 'error']
    const glyphs = states.map((status) => {
      useAgentEvents.mockReturnValue(status ? [event({ status })] : [])
      const { unmount } = render(<OrchestrationColumn sessionId="sess-1" />)
      const glyph = screen
        .getByRole('status', { name: 'Resume Analyst' })
        .querySelector('[aria-hidden="true"]')?.textContent
      unmount()
      return glyph
    })
    expect(new Set(glyphs).size).toBe(4)
  })

  it('reads as plain language and never renders raw JSON', () => {
    useAgentEvents.mockReturnValue([
      event({ status: 'done', summary: 'Read your resume and assessed a level' }),
      event({ id: 'evt-2', agent: 'case_architect', status: 'done', summary: 'Built the case for your interview' }),
      event({ id: 'evt-3', agent: 'planner', status: 'done', summary: 'Planned interview questions' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    const text = document.body.textContent ?? ''
    expect(text).toContain('Read your resume and assessed a level')
    expect(text).not.toMatch(/[{}[\]"]/)
  })

  it('falls back to plain-language default copy before any summary has arrived', () => {
    useAgentEvents.mockReturnValue([event({ status: 'started', summary: null })])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(
      row('Resume Analyst').getByText(/reading your resume and assessing a level/i),
    ).toBeTruthy()
  })

  // ==========================================================================
  // Story 2.7: the Case Architect and the Interview Planner.
  // ==========================================================================

  it('renders all four agents, in the order the graph runs them', () => {
    useAgentEvents.mockReturnValue([])
    render(<OrchestrationColumn sessionId="sess-1" />)
    const names = screen.getAllByRole('status').map((el) => el.getAttribute('aria-label'))
    expect(names).toEqual(['Resume Analyst', 'Case Architect', 'Interview Planner', 'Interviewer'])
  })

  it('drives each agent independently off its OWN events', () => {
    // The failure this guards: a column that renders one shared status, or
    // that filters on the wrong key, would show all three rows moving
    // together. Three different states at once can only be right if each row
    // reads its own agent's events.
    useAgentEvents.mockReturnValue([
      event({ id: 'evt-1', agent: 'resume_analyst', status: 'done' }),
      event({ id: 'evt-2', agent: 'case_architect', status: 'started' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Resume Analyst').getByText('Done')).toBeTruthy()
    expect(row('Case Architect').getByText('Working')).toBeTruthy()
    expect(row('Interview Planner').getByText('Waiting')).toBeTruthy()
  })

  it('renders the four states for the Case Architect and the Planner too', () => {
    for (const [agent, name] of [
      ['case_architect', 'Case Architect'],
      ['planner', 'Interview Planner'],
    ] as const) {
      for (const [status, label, glyph] of [
        ['started', 'Working', '◉'],
        ['done', 'Done', '●'],
        ['error', 'Error', '⚠'],
      ] as const) {
        useAgentEvents.mockReturnValue([event({ agent, status })])
        const { unmount } = render(<OrchestrationColumn sessionId="sess-1" />)
        expect(row(name).getByText(label), `${agent} ${status} label`).toBeTruthy()
        expect(row(name).getByText(glyph), `${agent} ${status} glyph`).toBeTruthy()
        unmount()
      }
    }
  })

  it('falls back to copy naming the RIGHT work for each new agent', () => {
    // A generic fallback ("Working...") would pass the state tests above
    // while telling the candidate nothing, and the Resume Analyst's copy
    // leaking onto the Planner's row would be actively wrong.
    useAgentEvents.mockReturnValue([
      event({ id: 'evt-2', agent: 'case_architect', status: 'started', summary: null }),
      event({ id: 'evt-3', agent: 'planner', status: 'started', summary: null }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    // "choosing", not "building", since 2026-08-07: this node selects one of
    // eight curated real companies and makes no LLM call, so the old copy
    // named work that no longer happens.
    expect(row('Case Architect').getByText(/choosing the company for your interview/i)).toBeTruthy()
    expect(row('Interview Planner').getByText(/planning interview questions/i)).toBeTruthy()
  })

  it('prefers a real backend summary over its own fallback copy', () => {
    useAgentEvents.mockReturnValue([
      event({ agent: 'planner', status: 'done', summary: 'Planned interview questions.' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Interview Planner').getByText('Planned interview questions.')).toBeTruthy()
  })

  // ==========================================================================
  // Story 3.3: the Interviewer.
  // ==========================================================================

  it('renders the Interviewer row with all four states, and byte-identical copy to the backend', () => {
    // These strings are asserted byte-identical to `_ASK_STARTED_SUMMARY`,
    // `_ASK_DONE_SUMMARY` and `_CLARIFY_ERROR_SUMMARY` in
    // `backend/app/graph/build.py`, which is why the panel never visibly
    // rewrites itself once a real event's summary arrives.
    useAgentEvents.mockReturnValue([])
    const { unmount: unmountWaiting } = render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Interviewer').getByText('Waiting')).toBeTruthy()
    unmountWaiting()

    useAgentEvents.mockReturnValue([event({ agent: 'interviewer', status: 'started', summary: null })])
    const { unmount: unmountActive } = render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Interviewer').getByText('Asking the next interview question.')).toBeTruthy()
    unmountActive()

    useAgentEvents.mockReturnValue([event({ agent: 'interviewer', status: 'done', summary: null })])
    const { unmount: unmountDone } = render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Interviewer').getByText('Asked the next interview question.')).toBeTruthy()
    unmountDone()

    useAgentEvents.mockReturnValue([event({ agent: 'interviewer', status: 'error', summary: null })])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(
      row('Interviewer').getByText('Ran into a problem answering your clarifying question.'),
    ).toBeTruthy()
  })

  it('drives the Interviewer independently off its own events, alongside the other three', () => {
    useAgentEvents.mockReturnValue([
      event({ id: 'evt-1', agent: 'resume_analyst', status: 'done' }),
      event({ id: 'evt-2', agent: 'case_architect', status: 'done' }),
      event({ id: 'evt-3', agent: 'planner', status: 'done' }),
      event({ id: 'evt-4', agent: 'interviewer', status: 'started' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(row('Interviewer').getByText('Working')).toBeTruthy()
    expect(row('Interview Planner').getByText('Done')).toBeTruthy()
  })

  it('has no em-dash or en-dash in any candidate-facing copy', () => {
    // CLAUDE.md's ban applies to everything a candidate reads. Checked on
    // rendered output rather than the source, so a dash arriving through
    // fallback copy is caught the same way one typed into JSX would be.
    useAgentEvents.mockReturnValue([
      event({ id: 'evt-1', agent: 'resume_analyst', status: 'started' }),
      event({ id: 'evt-2', agent: 'case_architect', status: 'started' }),
      event({ id: 'evt-3', agent: 'planner', status: 'error' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(document.body.textContent ?? '').not.toMatch(/[—–]/)
  })
})

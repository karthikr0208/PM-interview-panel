import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
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

describe('OrchestrationColumn', () => {
  beforeEach(() => {
    useAgentEvents.mockReset()
  })

  it('renders the WAITING glyph when there is no session yet', () => {
    useAgentEvents.mockReturnValue([])
    render(<OrchestrationColumn sessionId={null} />)
    expect(screen.getByText('○')).toBeTruthy()
    expect(screen.getByText('Waiting')).toBeTruthy()
  })

  it('renders the ACTIVE glyph on a started event', () => {
    useAgentEvents.mockReturnValue([event({ status: 'started' })])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(screen.getByText('◉')).toBeTruthy()
    expect(screen.getByText('Working')).toBeTruthy()
  })

  it('renders the DONE glyph once a done event lands', () => {
    useAgentEvents.mockReturnValue([event({ status: 'done', summary: 'Read your resume and assessed a level' })])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(screen.getByText('●')).toBeTruthy()
    expect(screen.getByText('Done')).toBeTruthy()
  })

  it('renders the ERROR glyph once an error event lands', () => {
    useAgentEvents.mockReturnValue([event({ status: 'error', summary: 'Could not read the resume text' })])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(screen.getByText('⚠')).toBeTruthy()
    expect(screen.getByText('Error')).toBeTruthy()
  })

  it('renders four states that are ALL DISTINCT glyphs, not just distinct colours', () => {
    const states: Array<AgentEvent['status'] | undefined> = [undefined, 'started', 'done', 'error']
    const glyphs = states.map((status) => {
      useAgentEvents.mockReturnValue(status ? [event({ status })] : [])
      const { unmount } = render(<OrchestrationColumn sessionId="sess-1" />)
      const glyph = screen.getByRole('status').querySelector('[aria-hidden="true"]')?.textContent
      unmount()
      return glyph
    })
    expect(new Set(glyphs).size).toBe(4)
  })

  it('reads as plain language and never renders raw JSON', () => {
    useAgentEvents.mockReturnValue([
      event({ status: 'done', summary: 'Read your resume and assessed a level' }),
    ])
    render(<OrchestrationColumn sessionId="sess-1" />)
    const text = document.body.textContent ?? ''
    expect(text).toContain('Read your resume and assessed a level')
    expect(text).not.toMatch(/[{}[\]"]/)
  })

  it('falls back to plain-language default copy before any summary has arrived', () => {
    useAgentEvents.mockReturnValue([event({ status: 'started', summary: null })])
    render(<OrchestrationColumn sessionId="sess-1" />)
    expect(screen.getByText(/reading your resume and assessing a level/i)).toBeTruthy()
  })
})

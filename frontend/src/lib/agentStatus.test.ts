import { describe, expect, it } from 'vitest'
import { deriveAgentStatus } from './agentStatus'
import type { AgentEvent } from './types'

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

describe('deriveAgentStatus', () => {
  it('is "waiting" when there are no events yet for this agent', () => {
    expect(deriveAgentStatus([], 'resume_analyst')).toEqual({
      state: 'waiting',
      summary: null,
      event: null,
    })
  })

  it('is "waiting" when events exist only for a DIFFERENT agent', () => {
    const events = [event({ id: 'evt-1', agent: 'interviewer', status: 'started' })]
    expect(deriveAgentStatus(events, 'resume_analyst').state).toBe('waiting')
  })

  it('is "active" on a started event with no terminal event after it', () => {
    const events = [event({ id: 'evt-1', status: 'started', summary: 'Reading your resume' })]
    const status = deriveAgentStatus(events, 'resume_analyst')
    expect(status.state).toBe('active')
    expect(status.summary).toBe('Reading your resume')
  })

  it('is "done" once a done event has landed', () => {
    const events = [
      event({ id: 'evt-1', status: 'started' }),
      event({ id: 'evt-2', status: 'done', summary: 'Read your resume and assessed a level' }),
    ]
    const status = deriveAgentStatus(events, 'resume_analyst')
    expect(status.state).toBe('done')
    expect(status.summary).toBe('Read your resume and assessed a level')
  })

  it('is "error" once an error event has landed', () => {
    const events = [
      event({ id: 'evt-1', status: 'started' }),
      event({ id: 'evt-2', status: 'error', summary: 'Could not read the resume text' }),
    ]
    const status = deriveAgentStatus(events, 'resume_analyst')
    expect(status.state).toBe('error')
    expect(status.event?.id).toBe('evt-2')
  })

  it('only ever looks at the LATEST event for the named agent, ignoring events for others', () => {
    const events = [
      event({ id: 'evt-1', agent: 'resume_analyst', status: 'done' }),
      event({ id: 'evt-2', agent: 'interviewer', status: 'error' }),
    ]
    expect(deriveAgentStatus(events, 'resume_analyst').state).toBe('done')
  })
})

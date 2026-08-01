import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ConfirmationScreen } from './ConfirmationScreen'
import type { ResumeAnalysis } from '../lib/types'

afterEach(cleanup)

// No fake-round numbers, no generic placeholder names (CLAUDE.md § Design) --
// fixtures follow the same rule the agent's own prompt is held to.
const BASE_ANALYSIS: ResumeAnalysis = {
  candidate_profile: {
    years_pm_experience: 3.4,
    domains: ['B2B fintech'],
    product_types: ['platform APIs'],
    company_contexts: ['seed startup'],
    scope_evidence: ['owned the payouts reconciliation surface end to end'],
    notable_outcomes: ['cut reconciliation errors from 4.2% to 0.6% over two quarters'],
    people_leadership: null,
  },
  assessed_level: 'PM',
  level_rationale:
    'Owned the payouts reconciliation surface end to end and set its roadmap for three quarters.',
  low_confidence_fields: [],
}

describe('ConfirmationScreen', () => {
  it('shows the assessed level, the rationale, and the profile', () => {
    render(<ConfirmationScreen analysis={BASE_ANALYSIS} onConfirm={vi.fn()} />)
    expect(screen.getByRole('radio', { name: 'PM' })).toBeTruthy()
    expect(screen.getByText(/owned the payouts reconciliation surface end to end and set/i)).toBeTruthy()
    expect(screen.getByText('B2B fintech')).toBeTruthy()
  })

  it('marks only fields named in low_confidence_fields as uncertain, not everything', () => {
    const analysis: ResumeAnalysis = {
      ...BASE_ANALYSIS,
      low_confidence_fields: ['years_pm_experience'],
    }
    render(<ConfirmationScreen analysis={analysis} onConfirm={vi.fn()} />)
    const badges = screen.getAllByText(/worth double-checking/i)
    expect(badges).toHaveLength(1)
  })

  it('marks the level itself uncertain when assessed_level is flagged', () => {
    const analysis: ResumeAnalysis = { ...BASE_ANALYSIS, low_confidence_fields: ['assessed_level'] }
    render(<ConfirmationScreen analysis={analysis} onConfirm={vi.fn()} />)
    expect(screen.getAllByText(/worth double-checking/i)).toHaveLength(1)
  })

  it('marks nothing uncertain when low_confidence_fields is empty', () => {
    render(<ConfirmationScreen analysis={BASE_ANALYSIS} onConfirm={vi.fn()} />)
    expect(screen.queryByText(/worth double-checking/i)).toBeNull()
  })

  it('lets the candidate change the level and reports it as a correction', () => {
    const onConfirm = vi.fn()
    render(<ConfirmationScreen analysis={BASE_ANALYSIS} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByRole('radio', { name: 'Senior PM' }))
    fireEvent.click(screen.getByRole('button', { name: /confirm corrected level/i }))

    expect(onConfirm).toHaveBeenCalledWith('Senior PM', { corrected: true })
  })

  it('reports acceptance of the unchanged level as NOT a correction', () => {
    const onConfirm = vi.fn()
    render(<ConfirmationScreen analysis={BASE_ANALYSIS} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByRole('button', { name: /^confirm level$/i }))

    expect(onConfirm).toHaveBeenCalledWith('PM', { corrected: false })
  })

  it('shows an acknowledgement after submitting and locks the level control', () => {
    render(<ConfirmationScreen analysis={BASE_ANALYSIS} onConfirm={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /^confirm level$/i }))

    expect(screen.getByText(/level confirmed/i)).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'PM' })).toHaveProperty('disabled', true)
  })

  it('renders verbatim resume quotes, never raw JSON', () => {
    render(<ConfirmationScreen analysis={BASE_ANALYSIS} onConfirm={vi.fn()} />)
    expect(
      screen.getByText(/owned the payouts reconciliation surface end to end/i, {
        selector: 'li',
      }),
    ).toBeTruthy()
    const text = document.body.textContent ?? ''
    expect(text).not.toMatch(/[{}[\]]/)
  })

  it('shows honest empty-state copy when notable_outcomes is legitimately empty', () => {
    const analysis: ResumeAnalysis = {
      ...BASE_ANALYSIS,
      candidate_profile: { ...BASE_ANALYSIS.candidate_profile, notable_outcomes: [] },
    }
    render(<ConfirmationScreen analysis={analysis} onConfirm={vi.fn()} />)
    expect(screen.getByText(/no measurable outcomes listed/i)).toBeTruthy()
  })
})

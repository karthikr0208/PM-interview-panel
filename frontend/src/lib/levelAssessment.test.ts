import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import type { ResumeAnalysis } from './types'

const { startLevelAssessment, submitLevelCorrection } = vi.hoisted(() => ({
  startLevelAssessment: vi.fn(),
  submitLevelCorrection: vi.fn(),
}))

vi.mock('./api', () => {
  class ApiError extends Error {}
  return { startLevelAssessment, submitLevelCorrection, ApiError }
})

const { useLevelAssessment } = await import('./levelAssessment')
const { ApiError } = await import('./api')

const ANALYSIS: ResumeAnalysis = {
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
  level_rationale: 'Owned the payouts reconciliation surface end to end.',
  low_confidence_fields: [],
}

describe('useLevelAssessment', () => {
  beforeEach(() => {
    startLevelAssessment.mockReset()
    submitLevelCorrection.mockReset()
  })

  it('starts idle and does nothing when there is no session yet', async () => {
    const { result } = renderHook(() => useLevelAssessment(null))
    expect(result.current.state).toEqual({ kind: 'idle' })

    await act(async () => {
      await result.current.beginAssessment()
    })

    expect(result.current.state).toEqual({ kind: 'idle' })
    expect(startLevelAssessment).not.toHaveBeenCalled()
  })

  it('moves idle -> assessing -> ready on a successful assessment', async () => {
    let resolveStart: (value: ResumeAnalysis) => void = () => {}
    startLevelAssessment.mockImplementation(
      () => new Promise((resolve) => { resolveStart = resolve }),
    )
    const { result } = renderHook(() => useLevelAssessment('sess-1'))

    let assessPromise!: Promise<void>
    act(() => {
      assessPromise = result.current.beginAssessment()
    })
    expect(result.current.state).toEqual({ kind: 'assessing' })

    await act(async () => {
      resolveStart(ANALYSIS)
      await assessPromise
    })

    expect(result.current.state).toEqual({ kind: 'ready', analysis: ANALYSIS })
    expect(startLevelAssessment).toHaveBeenCalledWith('sess-1')
  })

  it('surfaces the backend detail string verbatim when the assessment fails', async () => {
    startLevelAssessment.mockRejectedValue(
      new ApiError('No resume text found for this session. Upload a resume first.'),
    )
    const { result } = renderHook(() => useLevelAssessment('sess-1'))

    await act(async () => {
      await result.current.beginAssessment()
    })

    expect(result.current.state).toEqual({
      kind: 'error',
      message: 'No resume text found for this session. Upload a resume first.',
    })
  })

  it('falls back to generic copy when the assessment fails with a non-API error', async () => {
    startLevelAssessment.mockRejectedValue(new Error('network down'))
    const { result } = renderHook(() => useLevelAssessment('sess-1'))

    await act(async () => {
      await result.current.beginAssessment()
    })

    expect(result.current.state).toEqual({
      kind: 'error',
      message: 'Could not assess your level. Please try again.',
    })
  })

  it('moves ready -> confirmed on a successful confirmation, keeping the analysis', async () => {
    startLevelAssessment.mockResolvedValue(ANALYSIS)
    submitLevelCorrection.mockResolvedValue({ session_id: 'sess-1', level: 'PM', corrected: false })
    const { result } = renderHook(() => useLevelAssessment('sess-1'))

    await act(async () => {
      await result.current.beginAssessment()
    })
    await act(async () => {
      await result.current.confirmLevel('PM')
    })

    expect(result.current.state).toEqual({ kind: 'confirmed', analysis: ANALYSIS, level: 'PM' })
    expect(submitLevelCorrection).toHaveBeenCalledWith('sess-1', 'PM')
  })

  it('reports an error state when confirming fails, without losing the reason', async () => {
    startLevelAssessment.mockResolvedValue(ANALYSIS)
    submitLevelCorrection.mockRejectedValue(new ApiError('This session does not belong to you.'))
    const { result } = renderHook(() => useLevelAssessment('sess-1'))

    await act(async () => {
      await result.current.beginAssessment()
    })
    await act(async () => {
      await result.current.confirmLevel('Senior PM')
    })

    expect(result.current.state).toEqual({
      kind: 'error',
      message: 'This session does not belong to you.',
    })
  })
})

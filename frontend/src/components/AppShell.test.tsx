import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { AppShell } from './AppShell'

afterEach(cleanup)

describe('AppShell', () => {
  it('names the product in the only h1, above all three columns', () => {
    render(<AppShell orchestration={<p>agents</p>} conversation={<p>centre</p>} evaluation={<p>scores</p>} />)

    // Level matters as much as the text: every column heading is an h2, so
    // this is the document's top-level heading and must stay unique.
    const headings = screen.getAllByRole('heading', { level: 1 })
    expect(headings).toHaveLength(1)
    expect(headings[0].textContent).toBe("PM's AI Interview Panel")
  })

  it('still renders all three columns', () => {
    render(<AppShell orchestration={<p>agents</p>} conversation={<p>centre</p>} evaluation={<p>scores</p>} />)

    expect(screen.getByText('agents')).toBeTruthy()
    expect(screen.getByText('centre')).toBeTruthy()
    expect(screen.getByText('scores')).toBeTruthy()
  })
})

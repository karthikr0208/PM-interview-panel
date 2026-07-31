import type { PropsWithChildren } from 'react'
import { IconContext } from '@phosphor-icons/react'

// @phosphor-icons/react has no numeric `strokeWidth` prop (that is
// lucide-react's API, which this project deliberately does not use — see
// CLAUDE.md § Design). Phosphor exposes a discrete `weight` enum instead,
// and "regular" is Phosphor's own 1.5px-stroke-at-24px-viewBox weight — the
// value ARCHITECTURE §8 specifies. Every icon in the app should render
// through this provider rather than passing `weight` per call site, so the
// standard cannot drift call by call.
export function IconStandard({ children }: PropsWithChildren) {
  return (
    <IconContext.Provider value={{ weight: 'regular', size: 20 }}>
      {children}
    </IconContext.Provider>
  )
}

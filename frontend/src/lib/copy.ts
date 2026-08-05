/**
 * Deterministic em/en-dash stripper for candidate-facing text that came out
 * of a model. Prompting alone has shipped an em-dash into a generated
 * question twice (see DEV-STATE) -- this is the fix that cannot be prompted
 * around, so it runs at the render boundary on every string a model wrote,
 * never on this project's own static source strings (those are covered by
 * review instead).
 *
 * Order matters: a digit range ("2016-2019") is rewritten to "to" BEFORE
 * the generic dash-to-comma rule runs, or the generic rule would consume
 * the en-dash first and leave a comma where a range reads better.
 */
export function stripDashes(text: string): string {
  let result = text
    // En-dash between two digit runs reads as a range, not an aside.
    .replace(/(\d+)\s*–\s*(\d+)/g, '$1 to $2')
    // Any remaining em-dash or en-dash, with its surrounding whitespace,
    // reads as an aside -- a comma is the closest single-character
    // equivalent.
    .replace(/\s*[—–]\s*/g, ', ')

  // A dash that landed right before other punctuation (", ." ", ," ", ;")
  // leaves a redundant comma behind it; collapse down to the punctuation.
  result = result.replace(/,\s*([.,;:!?])/g, '$1')

  // Collapse whitespace runs left behind by the replacements above.
  result = result.replace(/\s+/g, ' ')

  return result.trim()
}

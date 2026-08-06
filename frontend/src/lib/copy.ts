/**
 * Deterministic dash-family stripper for candidate-facing text that came out
 * of a model. Prompting alone has shipped an em-dash into a generated
 * question twice (see DEV-STATE) -- this is the fix that cannot be prompted
 * around, so it runs at the render boundary on every string a model wrote,
 * never on this project's own static source strings (those are covered by
 * review instead).
 *
 * The seven Unicode dash-family characters split into two classes that want
 * DIFFERENT treatment, not one wider rule:
 *   - Aside/range dashes (figure dash U+2012, en dash U+2013, em dash
 *     U+2014, horizontal bar U+2015): a digit range becomes "to", anything
 *     else becomes a comma. This is the original behaviour, widened from
 *     en/em to all four.
 *   - Hyphen-like characters (hyphen U+2010, non-breaking hyphen U+2011,
 *     minus sign U+2212): normalised to an ASCII hyphen. Turning the
 *     non-breaking hyphen in "state-of-the-art" into a comma would be far
 *     worse than leaving it alone, so these never reach the comma rule.
 *
 * Order matters twice over: the hyphen-like normalisation MUST run first,
 * so those characters become plain ASCII "-" before the aside/range rules
 * below can see them (ASCII "-" does not match those rules, which is what
 * keeps "state-of-the-art" intact). Within the aside/range rules, a digit
 * range ("2016-2019") is rewritten to "to" BEFORE the generic dash-to-comma
 * rule runs, or the generic rule would consume the dash first and leave a
 * comma where a range reads better.
 */
export function stripDashes(text: string): string {
  let result = text
    // Hyphen-like: hyphen (U+2010), non-breaking hyphen (U+2011), minus
    // sign (U+2212). Normalise to ASCII hyphen first, before anything else
    // runs, so these never fall into the aside/range rules below.
    .replace(/[‐‑−]/g, '-')
    // Aside/range dash -- figure dash (U+2012), en dash (U+2013), em dash
    // (U+2014), horizontal bar (U+2015) -- between two digit runs reads as
    // a range, not an aside.
    .replace(/(\d+)\s*[‒–—―]\s*(\d+)/g, '$1 to $2')
    // Any remaining aside/range dash, with its surrounding whitespace,
    // reads as an aside -- a comma is the closest single-character
    // equivalent.
    .replace(/\s*[‒–—―]\s*/g, ', ')

  // A dash that landed right before other punctuation (", ." ", ," ", ;")
  // leaves a redundant comma behind it; collapse down to the punctuation.
  result = result.replace(/,\s*([.,;:!?])/g, '$1')

  // Collapse whitespace runs left behind by the replacements above.
  result = result.replace(/\s+/g, ' ')

  return result.trim()
}

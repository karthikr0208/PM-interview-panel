"""Candidate-facing text normalisation, shared by every graph node that
persists or surfaces prose a candidate reads.

🔴 WHY THIS IS AT THE GRAPH BOUNDARY AND NOT INSIDE THE AGENTS.

The golden suites assert `no_dash_variants` on what the agent FUNCTIONS
return. Normalising inside `answer_clarification` / `generate_probe` /
`compose_question` would make every one of those assertions pass
VACUOUSLY -- the suite would go green while generation quietly got worse,
which is the exact failure mode CLAUDE.md warns about twice. Agents keep
emitting raw model output so the golden suite can still see it; the graph
cleans up on the way to the database and the browser.

`compose_question` additionally guarantees the Planner's question is
emitted BYTE FOR BYTE (spec §2a), so it cannot normalise even if the
vacuity problem did not exist.

🔴 WHY IT EXISTS AT ALL, as of 2026-08-07. `stripDashes` in
`frontend/src/lib/copy.ts` guards DISPLAY only. The raw characters were
still reaching `question_plan` and `transcript_turns`: a live interview on
2026-08-07 left 3 U+2011 in `question_plan` and 1 at `transcript_turns`
idx=16. **Phase 4 renders scorecards from those rows**, so a display-only
guard does not cover it. DEV-STATE carried this as "not absorbed" from
2026-08-06 until it was observed.

Semantics are deliberately IDENTICAL to `stripDashes`, and
`tests/test_user_facing_copy.py` pins them equal. Two classes, because one
rule for all seven characters would be wrong:

  hyphen-like  U+2010, U+2011, U+2212  -> ASCII "-"
      A non-breaking hyphen in "state-of-the-art" is a hyphen. Turning it
      into a comma would be worse than leaving it alone.
  aside/range  U+2012, U+2013, U+2014, U+2015  -> " to " between digits,
      otherwise ", "
"""

from __future__ import annotations

import re

# Hyphen-like: hyphen (U+2010), non-breaking hyphen (U+2011), minus sign
# (U+2212). Normalised to ASCII first, before anything else runs, so these
# never fall into the aside/range rules below.
_HYPHEN_LIKE = "‐‑−"

# Aside/range: figure dash (U+2012), en dash (U+2013), em dash (U+2014),
# horizontal bar (U+2015).
_ASIDE_LIKE = "‒–—―"

_RANGE_RE = re.compile(rf"(\d+)\s*[{_ASIDE_LIKE}]\s*(\d+)")
_ASIDE_RE = re.compile(rf"\s*[{_ASIDE_LIKE}]\s*")
_HYPHEN_RE = re.compile(rf"[{_HYPHEN_LIKE}]")
# A dash landing right before other punctuation leaves a redundant comma.
_REDUNDANT_COMMA_RE = re.compile(r",\s*([.,;:!?])")


def normalize_dashes(text: str) -> str:
    """The Python twin of `stripDashes`. Total: `None` and `""` return `""`
    rather than raising, so a node can call it on an optional field without
    guarding first."""
    if not text:
        return ""
    result = _HYPHEN_RE.sub("-", text)
    result = _RANGE_RE.sub(r"\1 to \2", result)
    result = _ASIDE_RE.sub(", ", result)
    result = _REDUNDANT_COMMA_RE.sub(r"\1", result)
    result = re.sub(r"\s+", " ", result)
    return result.strip()

"""Curated, real-company case worlds (PHASE-3.5-SPEC.md 3.5.2), which
replace the Case Architect's generation. Eight hand-written `CaseWorld`
fixtures live as JSON alongside this file, one per slug below.

`select_case_world` is deterministic Python, no LLM call -- CLAUDE.md
§ Style: prefer deterministic Python wherever the decision can be made from
state. It is a pure function of (level, profile): same input, same output,
every time, which matters for the same reason `await_candidate` must not
double-write on a replayed resume -- a retried request must never mid-flight
switch the world a candidate is being interviewed against.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.agents.case_architect import CaseWorld

_CASES_DIR = Path(__file__).resolve().parent

# Which curated worlds suit which level -- data, not branching prose, per the
# brief. Chosen by product SCOPE, not company size: a real company's
# situation.prompt is fixed (these are curated, not generated per level), so
# the level match is about which company's strategic question reads as
# APM-bounded versus GPM-portfolio-scale, mirroring the Case Architect's own
# SCOPE BY LEVEL table (case_architect.py's _SYSTEM_PROMPT):
#   APM       - one bounded core product, a single clear strategic question
#               (Duolingo's content pipeline, Cursor's one product)
#   PM        - one product area end to end, real but contained
#               (Reddit's licensing-vs-traffic tradeoff, Figma's one product)
#   Senior PM - platform-level ambiguity across surfaces, still one product
#               line (Airbnb's core-vs-expansion, YouTube's format tradeoff)
#   GPM       - a multi-product portfolio, a business-outcome-level decision
#               (OpenAI's and Anthropic's consumer/enterprise/compute tradeoffs)
_LEVEL_SLUGS: dict[str, tuple[str, ...]] = {
    "APM": ("duolingo", "cursor"),
    "PM": ("reddit", "figma"),
    "Senior PM": ("airbnb", "youtube"),
    "GPM": ("openai", "anthropic"),
}

ALL_SLUGS: tuple[str, ...] = tuple(
    sorted({slug for slugs in _LEVEL_SLUGS.values() for slug in slugs})
)


def _load(slug: str) -> CaseWorld:
    payload = json.loads((_CASES_DIR / f"{slug}.json").read_text(encoding="utf-8"))
    return CaseWorld.model_validate(payload)


def select_case_world(level: str, profile: dict) -> CaseWorld:
    """Picks a curated `CaseWorld` suited to `level`.

    Deterministic: the same `(level, profile)` always resolves to the same
    world, via a stable hash of `profile` rather than randomness, so a
    retried request or a replayed resume never switches the world mid-flight.

    Unrecognised levels fall back to the PM slate rather than raising --
    this function must never be the reason an interview cannot start.
    """
    slugs = _LEVEL_SLUGS.get(level, _LEVEL_SLUGS["PM"])
    digest = hashlib.sha256(
        json.dumps(profile or {}, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    index = int(digest, 16) % len(slugs)
    return _load(slugs[index])

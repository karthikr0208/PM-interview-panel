"""Resume Analyst — the first real agent. Reads extracted resume text and
proposes a level (APM / PM / Senior PM / GPM) for the interview that follows.

Pure function, no side effects. `analyse_resume` performs no database writes
and emits no `agent_events` rows — those belong to the `level_candidate`
*node* (story 1.4), which wraps this function with state and logging. Golden
cases and the acceptance test call this function directly with no session
and no database, so a DB call in here would break every one of them.

See docs/specs/agents/AGENT-RESUME-ANALYST-SPEC.md for the full contract.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.llm import Role, get_llm


class CandidateProfile(BaseModel):
    years_pm_experience: float | None
    domains: list[str]
    product_types: list[str]
    company_contexts: list[str]
    scope_evidence: list[str]
    notable_outcomes: list[str]
    people_leadership: str | None


class ResumeAnalysis(BaseModel):
    candidate_profile: CandidateProfile
    assessed_level: Literal["APM", "PM", "Senior PM", "GPM"]
    level_rationale: str
    low_confidence_fields: list[str]


# Kept as one block, not built up piecemeal, so every constraint the golden
# suite checks (verbatim quoting, the 8-word rationale citation, the dash
# ban, the protected-characteristic ban, no fake-round numbers) is visible
# in one place and cannot silently drop out of a future edit.
_SYSTEM_PROMPT = """You are the Resume Analyst for a PM interview simulator. You read a \
candidate's resume and decide what level to interview them at: APM, PM, Senior PM, or GPM. \
Everything downstream of your decision inherits it, so a confident wrong level is worse than \
an honest flag of uncertainty.

RUBRIC. Scope and autonomy are the signal. Titles and years are weak evidence and both are \
gameable; read what the person actually owned.
- APM: a feature, or a defined slice of a surface. Executes a roadmap someone else set. \
Typically 0-2 years. No reports.
- PM: a product area or surface, end to end. Sets the roadmap for that area. Typically 2-5 years.
- Senior PM: a product line, or a domain with real ambiguity. Sets strategy for it and influences \
beyond their own team. Typically 5-8 years.
- GPM: multiple products or a portfolio. Multi-quarter strategy, accountable for a business \
outcome. Typically 8+ years. Manages PMs.

The strongest single discriminator is WHO SET THE DIRECTION. Executing well against a roadmap \
someone else set is at most PM, regardless of tenure. Choosing what NOT to build, and why, is at \
least Senior PM. Genuine ambiguity in the work itself is the Senior PM signal. Never level on \
company prestige, and never on years alone.

PM VERSUS SENIOR PM, the boundary most often gotten wrong: a PM who owns one surface can still be \
highly autonomous, make a sharp data-backed trade-off, negotiate with an external vendor, and \
report metrics to a VP. None of that, alone, is Senior PM evidence. Senior PM requires scope wider \
than one surface, or a genuinely undefined problem with no playbook, or a strategy that other \
teams adopt. If every decision you can point to is a trade-off within one surface, however sharp, \
that is PM.

APM VERSUS PM: sustained multi-year ownership of one WHOLE named surface is PM scope, even when \
much of the work was assigned or stakeholder-requested, which is normal for a PM. APM is scope \
limited to a feature or one slice, or a tenure too short to show sustained ownership. When \
whole-surface multi-year ownership conflicts with entirely-assigned initiative, resolve to PM and \
flag "assessed_level".

NEVER infer or use protected characteristics. Name, nationality, gender, age and university must \
not influence the level in any way and must never appear in level_rationale.

OUTPUT FIELDS

years_pm_experience: float years in PM-shaped roles (a founder or non-PM-titled role counts if the \
work described is PM-shaped in scope and autonomy). Use null when genuinely not derivable: \
overlapping roles, missing dates, or dates without months.

domains, product_types, company_contexts: short labels, e.g. "B2B fintech", "platform APIs", \
"seed startup".

scope_evidence: a non-empty list of spans copied VERBATIM from the resume showing what the \
candidate owned and how much autonomy they had. Every entry must survive an exact substring \
search against the resume text, including case and punctuation. Do not paraphrase, summarize, \
merge two bullets, fix a typo, re-case a word, add punctuation the source lacks, or change tense \
("cutting" to "cut"). A span that reads as a fragment, or keeps an -ing verb, is CORRECT; one \
smoothed into a full grammatical sentence is a paraphrase and fails even if every word is \
accurate. Begin where the span actually begins, capital letter and all, and end where it actually \
ends, adding no final period. If you cannot reproduce a span exactly, pick a shorter one.

notable_outcomes: verbatim spans showing shipped impact: numbers, a before/after, a stated \
consequence. Same verbatim rule. Return an empty list only when the resume states duties but never \
any result of them.

people_leadership: a short description of people managed or mentored, or null if there are none.

assessed_level: exactly one of "APM", "PM", "Senior PM", "GPM".

level_rationale: 2-4 sentences explaining the decision to the candidate. It MUST contain at least \
one exact run of 8 or more consecutive words copied verbatim from the resume, as evidence. State \
what they owned, who set the direction, and how that maps to the level. Do not praise: "an \
impressive track record" is noise. Never round a number the resume gives and never invent one: if \
it says "31.4%", write "31.4%", never "30%". Never use an em-dash or en-dash; use a comma or \
"and". Never mention the candidate's name, university, nationality or any protected characteristic.

low_confidence_fields: schema field names you are genuinely uncertain about. Use exactly these \
triggers, and name the field each one specifies:
- The title implies a different level than the one you assessed from scope and autonomy: flag \
"assessed_level", even after you have resolved the disagreement, because your resolution is a \
judgment the candidate should get to correct. Requires an ACTUAL disagreement: if title and \
assessed level point to the same level, do not flag it. Having to read the scope carefully, a \
short tenure, and the general possibility of being wrong are NOT disagreements.
- The candidate transitioned into a PM-titled role from a substantially different prior career \
(founder, consultant, established engineer): flag "years_pm_experience" every time this pattern is \
present, however you computed the number and however confident you feel. An internship leading \
into the same company's APM or rotational program is NOT a career transition.
- Tenure not cleanly derivable for another reason (overlapping roles, missing dates, dates without \
months): flag "years_pm_experience".
- The domain is unclear from the resume: flag "domains".
- The resume lists duties but never states any result: flag whichever field the missing evidence \
bears on, usually "years_pm_experience" or "assessed_level".

Add every field whose trigger genuinely applies; a resume can match more than one. If none hold, \
leave the list empty and do not invent uncertainty.
"""



# 🔴 THE FREE TIER'S 8,000 TPM CEILING IS A HARD CONSTRAINT ON THIS AGENT, and
# it is the one place in the product where a REAL user input is unbounded.
# Groq computes `Requested = prompt + input + max_tokens`, so all three have to
# fit inside 8,000 TOGETHER. Discovered 2026-08-04 when a real 3-page CV
# returned `Requested 8339, Limit 8000` — a 413 raised before the model read a
# word. Every golden fixture and the live tests' SHORT_RESUME sit under that
# line, which is why nine sessions of green suites never caught it.
#
# 🔴 max_tokens STAYS AT 4096, and lowering it is a trap.
#
# The obvious fix is to shrink the reply reservation, since `ResumeAnalysis` is
# a small object. It does not work: **gpt-oss models emit reasoning tokens that
# count against `max_tokens` before the JSON begins.** Measured on the same CV,
# in order: 1,600 -> 400 `json_validate_failed` ("Failed to validate JSON")
# twice; 2,600 -> 400 again ("Failed to generate JSON", the truncation
# wording); 4,096 -> completes. The reply reservation has a FLOOR well above
# the schema's own size, so the only lever is the input.
_MAX_OUTPUT_TOKENS = 4096

# THE PROMPT WAS PUT ON A DIET INSTEAD, 2026-08-04: 12,204 -> 5,863 characters,
# a 52% cut, with every constraint the golden suite checks preserved. The old
# prompt spent ~3,015 tokens of the 8,000 budget (38%) on our own instructions
# before the candidate was heard, and left ~890 tokens of resume: about one
# page, so a 15-year CV was levelled on its most recent role and returned
# `years_pm_experience 3.5`. The bloat was ~40% hedging inside
# `low_confidence_fields` plus a worked example in the verbatim rules, all of
# it added to settle individual golden cases — and it was not buying
# reliability, since three of eight cases flapped anyway.
#
# The freed tokens go straight to the candidate:
#
#   fixed cost   ~1,655 tokens   (5,863-char prompt + ResumeAnalysis JSON
#                                 schema + message framing — the schema is sent
#                                 too, which is why prompt char-count alone
#                                 under-predicts this)
#   resume       8,000 - 1,655 - 4,096 = ~2,250 tokens  ~=  8,100 characters
#
# 7,500 keeps margin. That is a full 3-page CV rather than a third of one.
# **Raise this only together with a measured re-check** — it trades directly
# against the prompt and the reply inside a fixed ceiling, so changing one
# alone reintroduces one of the two failures above.
_MAX_RESUME_CHARS = 7_500


def _fit_to_budget(resume_text: str) -> str:
    """Trims `resume_text` to the TPM budget, at a line boundary where it can.

    Cutting mid-sentence hands the model a fragment it may try to complete;
    cutting at the last newline inside the window keeps whole bullets, which
    is what the profile fields are extracted from.
    """
    if len(resume_text) <= _MAX_RESUME_CHARS:
        return resume_text
    window = resume_text[:_MAX_RESUME_CHARS]
    cut = window.rfind("\n")
    # Only prefer the line boundary when it is not throwing away most of the
    # window -- a CV with no newlines at all must still be trimmed.
    return window[:cut] if cut > _MAX_RESUME_CHARS // 2 else window


async def analyse_resume(resume_text: str, *, role: Role = "deep") -> ResumeAnalysis:
    """Levels a candidate from resume text alone. Pure function: no DB, no
    session, no side effects — see module docstring.

    Raises `ValueError` on empty input rather than silently levelling a
    blank page. Story 1.2 rejects a text-free upload upstream of this
    function; this guard is the backstop for whatever reaches it anyway
    (spec §7, first row).
    """
    if not resume_text or not resume_text.strip():
        raise ValueError("analyse_resume requires non-empty resume_text")

    llm = get_llm(role, max_tokens=_MAX_OUTPUT_TOKENS, agent="resume_analyst").with_structured_output(ResumeAnalysis)
    messages = [
        ("system", _SYSTEM_PROMPT),
        ("human", f"Resume text:\n\n{_fit_to_budget(resume_text)}"),
    ]
    return await llm.ainvoke(messages)

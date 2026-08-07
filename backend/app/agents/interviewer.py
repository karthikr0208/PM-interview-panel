"""Interviewer — conducts the interview: asks the Planner's questions
verbatim, bridges between them, and answers clarifying questions from
`case_world` alone. See docs/specs/agents/AGENT-INTERVIEWER-SPEC.md for the
full contract; §2 decides the shape below and §6 computes the token budget
that makes it necessary.

Pure functions, no side effects. Nothing here takes a session, opens a
connection, or writes a row -- those belong to the nodes in
`app/graph/build.py` (`ask_question`, `answer_clarification_node`), exactly
as the other three agents split (see `case_architect.py`'s docstring).
Golden cases call `answer_clarification` directly with no session and no
database, so a DB call in here would break every one of them.

🔴 `compose_question` is the load-bearing function in this module and it is
NOT an LLM call. Spec §2a: the Planner's `question` string already passed
`missing_grounding`, `is_generic_question`, `no_dash_variants`,
`contains_fake_round_number` and `contains_banned_register_name` before it
reached state. Regenerating it here would void all five checks at runtime,
on a surface no static test can see -- so it is emitted BYTE FOR BYTE by
Python instead. See DEV-STATE § Decisions 2026-08-05.

PHASE-3.5-SPEC.md 3.5.4 adds two things, both still pure functions with no
DB and no session:

1. `answer_clarification` INVENTS a plausible fact when `case_world` is
   silent, instead of refusing (spec's "THREE DECISIONS" #2 -- the refusal
   branch is deleted). The invented fact is the caller's to persist in the
   new `improvised_facts` state list; this module never writes state, it
   only accepts that list back on every later call so the same fact is
   never invented twice with two different values.
2. `generate_probe` is the new, only-remaining-question-in-the-interview's
   follow-up call. One question is now probed 6-10 times instead of asking
   3-7 questions, so `primary_dimension` coverage moves from a per-question
   field to a resolution over the probe ladder -- done in Python
   (`resolve_primary_dimension`), never asked of the model, same philosophy
   as `_first_dimension` in `planner.py`.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from app.llm import Role, get_llm


class ClarificationAnswer(BaseModel):
    # True = case_world states this fact. False = it does not, and this
    # answer INVENTS one (spec "THREE DECISIONS" #2 -- the refusal branch is
    # gone). `can_answer` still drives which standard the golden suite holds
    # the answer to; it no longer means "did we answer at all."
    can_answer: bool
    answer: str  # candidate-facing prose -- states the invented fact as given, never flags it as invented
    grounded_in: list[str]  # case_world facts this answer rests on -- non-empty on BOTH branches
    # ONE self-contained sentence stating exactly the invented fact, written
    # so it can be replayed to a LATER call verbatim (e.g. "Assume weekly
    # active users are around 3.4 million."). Empty string when can_answer
    # is True. This is what makes invention durable rather than momentary --
    # the caller appends it to the append-only `improvised_facts` state list
    # so a later call can repeat it exactly instead of re-inventing it.
    improvised_fact: str


# 🔴 The transition between questions is DETERMINISTIC, and it used to be an
# LLM call. Deleted 2026-08-05 on measurement, not on taste: `write_bridge`
# was a CONSTANT FUNCTION wearing an LLM call. Six materially different
# candidate answers -- a sharp segmented analysis, a flat "I don't know", a
# pushback on the premise, a three-word answer -- produced the same sentence
# six times with the words shuffled:
#
#   strong+specific  -> "Got it, thanks for sharing that. Let's move on."
#   refuses/stuck    -> "Thanks for sharing that. Let's continue."
#   disagrees        -> "Understood. Let's move on to the next topic."
#   very short       -> "Thanks for sharing that. Let's continue."
#
# It bought nothing and cost a `fast` call per question, latency while a
# candidate watches a cursor, and a candidate-facing generative surface with
# no static dash guard. CLAUDE.md § Style: prefer deterministic Python where
# the decision can be made from state. See DEV-STATE § Decisions 2026-08-05
# and AGENT-INTERVIEWER-SPEC.md §2a.
#
# Source strings, so `tests/test_user_facing_copy.py` can see them -- which
# is the second win: the em-dash ban on this surface is now STATICALLY
# enforced instead of merely prompted, and prompting had already failed
# twice on that exact rule.
_TRANSITIONS: tuple[str, ...] = (
    "Thanks. Next one.",
    "Good, let's move on.",
    "Understood. Next question.",
    "Thanks for that. Let's keep going.",
)

# The real work (spec §2b): reads case_world, improvised_facts, and the
# current question, and nothing else -- no resume, no profile, no level, no
# transcript. Every constraint the golden suite checks (grounding, the
# figure check, invention consistency, dash/round-number/name hygiene)
# stays visible in one block, same reasoning as case_architect.py's and
# planner.py's prompts.
#
# 🔴 RESTRUCTURED 2026-08-07 INTO THREE ORDERED STEPS, after the live
# interview caught a REGRESSION this prompt's own words already banned.
# Asked "Since the short-term rental market is shrinking, does that change
# how much Services matters?" against a world stating growth_rate_pct 8.6,
# it replied "Yes, the shrinking short-term rental market makes Services and
# Experiences a more critical growth driver." It both accepted the premise
# and repeated the false claim back.
#
# The words were already here and lost anyway, which is the instructive
# part: this was a TWO-way decision (cite the world, or invent) with a
# premise warning bolted on beside it, so a leading question read as a gap
# to fill and helpfulness won. Contradiction is now STEP 1, ahead of both,
# and "silent" is defined explicitly as the world saying nothing either way
# rather than saying something the question would rather it did not.
#
# The same exchange passed on 2026-08-05 against the REFUSAL branch that
# "THREE DECISIONS" #2 then deleted. The disposition that makes this agent
# helpful is the one that makes it agreeable; the ordering is what holds
# both. See DEV-STATE § Decisions 2026-08-07.
#
# 🔴 PHASE-3.5-SPEC.md "THREE DECISIONS" #2: the refusal branch is DELETED.
# Real interviewers say "assume DAU is 50 million" rather than declining to
# answer -- a refusal reads as a broken interviewer to a candidate. The
# damage was never the invention, it was SELF-CONTRADICTION (50M at minute
# 8, 20M at minute 30), so invent-and-record replaces invent-freely: the
# consistency rule below is the whole point.
_CLARIFICATION_SYSTEM_PROMPT = """You are answering ONE clarifying question a PM candidate asked mid-interview, using \
ONLY the case world given below, plus any facts you have already improvised earlier in THIS interview (listed below, \
if any). Answer directly with the JSON object; do not deliberate at length before answering.

🔴 WORK THROUGH THESE THREE STEPS IN ORDER. The ORDER is the whole point: step 1 outranks step 3, and being \
helpful never licenses agreeing with something false.

STEP 1 -- IS THE QUESTION ASSERTING SOMETHING THE CASE WORLD CONTRADICTS? A candidate will sometimes phrase a \
question as though a claim were already settled: "given that churn has been climbing all year...", "since the market \
is shrinking...", "given that this is our largest line...". CHECK EVERY SUCH CLAIM AGAINST THE CASE WORLD BEFORE YOU \
ANSWER ANYTHING ELSE. If the world states otherwise, your FIRST sentence must say what the world actually says, with \
its number, and you must NOT repeat the candidate's claim back in ANY form -- not as agreement, not as a concession, \
not as a subordinate clause you then build on. Writing "Yes, the shrinking market means..." against a world stating \
the market is growing is the WORST failure available to you: it invents nothing, yet it tells the candidate \
something false about a real company. Correcting a premise is NOT a refusal, and on its own it does NOT make \
can_answer false -- the world answered you, it just answered differently than the question assumed.

STEP 2 -- DOES THE CASE WORLD ANSWER THE QUESTION? Then set can_answer to true and cite it exactly as written.

STEP 3 -- IS THE CASE WORLD SILENT ON IT? Silent means the world says NOTHING either way -- not that it says \
something you would rather it did not. Then set can_answer to false and INVENT a plausible, specific fact instead of \
refusing, stating it as given, in the same confident register as a grounded answer. Never flag the fact as invented, \
never hedge it, and never say "I don't have that" or "the brief does not specify" -- a real interviewer who does not \
know an exact figure still gives the candidate something to work with.

NEVER CONTRADICT a number, company, product, person, or date the case world or an already improvised fact states. \
That rule and step 1 are the same rule seen from two sides: do not contradict the world yourself, and do not let the \
candidate's phrasing contradict it on your behalf.

🔴 CONSISTENCY IS THE WHOLE POINT: before inventing anything, check the list of facts already improvised earlier in \
this interview, given below. If the fact being asked about is already there, REPEAT IT EXACTLY -- same number, same \
units, same wording -- never invent a second, different value for something you already improvised. A figure that \
changes between minute 8 and minute 30 is the one failure this design exists to prevent; the invention itself is not \
a failure.

A LEADING QUESTION IS STEP 1's JOB, and step 1 runs before you decide anything else. A question that presupposes \
something the world never states at all is different, and is step 3: invent, and answer it.

GROUNDED_IN, checked mechanically, same rule as the interview plan itself: every entry must be copied EXACTLY, \
character-for-character, from the case world -- never paraphrased, never empty, 1-3 entries. Use the company name, a \
competitor or entity name exactly as written, a bare number exactly as it appears in the schema with no unit added, or \
a supporting_facts string copied in full. `grounded_in` must be non-empty even when you invent: ground the answer in \
the nearest thing the world DOES say, so an improvised fact still sits next to something real rather than nothing at \
all.

IMPROVISED_FACT: when can_answer is true, this is the empty string. When can_answer is false, this is ONE \
self-contained sentence stating exactly the fact you invented, written so it can be repeated verbatim if asked again \
(for example: "Assume weekly active users are around 3.4 million."). It must state the fact itself, not describe the \
question that was asked.

WHEN can_answer IS TRUE: every number in `answer` must appear in the case world above, exactly as it is written there \
(a comma or a $ sign may be added; nothing may be invented). Cite it the way you would say it aloud, never as a raw \
JSON field name and value.

Candidate-facing prose, 2-4 sentences: never an em-dash or en-dash (use a comma or "and" instead), no fake-round \
numbers like "50% of customers" (match the case world's own organic decimal precision, even for an invented figure), \
no placeholder names ("Acme", "TechCorp", "John Doe" and that register). Do not evaluate, hint at, or coach the \
candidate's question or the answer they are building toward -- you are stating a fact, not judging one. Do not \
introduce yourself or use a persona name; you are the interviewer, not a character. Answer the question asked; do not \
restate the interview's original question.
"""


def transition_for(q_idx: int) -> str | None:
    """The transition line preceding question `q_idx` (0-based), or `None`
    for question 1, which opens the interview and has nothing to transition
    from. Deterministic and total: no LLM, no state, no clock.

    Rotates rather than picking at random so a given interview is
    reproducible from `q_idx` alone -- a random line would make the
    transcript differ run to run for no benefit, and this project already
    has enough non-determinism it cannot remove (DEV-STATE § Decisions
    2026-08-01).
    """
    if q_idx <= 0:
        return None
    return _TRANSITIONS[(q_idx - 1) % len(_TRANSITIONS)]


async def answer_clarification(
    case_world: dict,
    planned_question: str,
    clarifying_question: str,
    *,
    role: Role = "fast",
    improvised_facts: list[str] | None = None,
) -> ClarificationAnswer:
    """Answers `clarifying_question` from `case_world` plus `improvised_facts`.
    Pure function: no DB, no session, no side effects -- see module docstring.

    🔴 The positional part of the signature (`case_world, planned_question,
    clarifying_question`, keyword `role`) is fixed by the golden suite's call
    site -- do not change it; `tests/golden/interviewer/test_golden.py` calls
    it exactly that way, with no `improvised_facts` argument at all. The new
    parameter is keyword-only with a default precisely so that call site
    keeps working unmodified.

    `improvised_facts` (spec "THREE DECISIONS" #2): every fact this function
    has invented so far in the SAME interview, append-only, owned by graph
    state -- this function never writes it, only reads it, and repeats an
    entry verbatim rather than re-inventing it with a new value (the
    consistency rule is in the prompt; `None` and `[]` are both treated as
    "nothing improvised yet").

    `case_world` is READ ONLY, same rule as `plan_interview` and
    `generate_case_world`: this function must never mutate the dict it is
    given, and the node calling it must never write `case_world` back to
    state -- it was already written once, by the Case Architect
    (ARCHITECTURE §2). `improvised_facts` is READ ONLY here for the same
    reason -- appending the new fact is the caller's job.

    `max_tokens=2048` per AGENT-INTERVIEWER-SPEC.md §6's computed table --
    a PROJECTION as of story 3.2, not yet a measurement against a real
    `Requested` header. Unchanged by story 3.5.4: `improvised_fact` adds one
    short string field to a three-field schema, not a size class change. If
    Groq returns `json_validate_failed`, RAISE this rather than shortening
    the prompt: gpt-oss emits reasoning tokens against `max_tokens` before
    the JSON starts, and that error reads like a prompt problem and is not
    one (DEV-STATE § Decisions 2026-08-04).

    Raises `ValueError` on an empty `case_world`, `planned_question`, or
    `clarifying_question` rather than silently answering from nothing.
    """
    if not case_world:
        raise ValueError("answer_clarification requires a non-empty case_world")
    if not planned_question or not planned_question.strip():
        raise ValueError("answer_clarification requires a non-empty planned_question")
    if not clarifying_question or not clarifying_question.strip():
        raise ValueError("answer_clarification requires a non-empty clarifying_question")

    llm = get_llm(role, max_tokens=2048).with_structured_output(ClarificationAnswer)
    messages = [
        ("system", _CLARIFICATION_SYSTEM_PROMPT),
        (
            "human",
            "Case world:\n"
            + json.dumps(case_world, indent=2)
            + "\n\nFacts you have already improvised earlier in this interview (repeat any of these EXACTLY if "
            "asked again; never invent a new value for one already here):\n"
            + (json.dumps(improvised_facts, indent=2) if improvised_facts else "(none yet)")
            + "\n\nThe interview question currently on the table: "
            + planned_question
            + "\n\nThe candidate's clarifying question: "
            + clarifying_question,
        ),
    ]
    return await llm.ainvoke(messages)


def compose_question(planned_question: str, transition: str | None = None) -> str:
    """DETERMINISTIC, no LLM call, ever. Concatenates an optional transition
    line and the Planner's question, and that is ALL it does -- spec §2a's
    central rule. `planned_question` is emitted BYTE FOR BYTE; nothing here
    rewrites, trims, or reformats it beyond joining it to `transition`.

    As of 2026-08-05 the whole of `ask_question` is deterministic, so the
    conduct loop's ONLY LLM call is `answer_clarification`. That is worth
    knowing when reading the call-count assertions in
    `tests/test_conduct_loop.py`: every question costs zero.
    """
    if transition and transition.strip():
        return f"{transition.strip()}\n\n{planned_question}"
    return planned_question


# ═══════════════════════════════════════════════════════════════════════════
# PHASE-3.5-SPEC.md 3.5.4, "THREE DECISIONS" #3: the interview is now ONE
# question probed 6-10 times, not 3-7 pre-planned questions. `generate_probe`
# is the new per-turn LLM call this design needs; everything below it exists
# to keep that call inside the 8,000 TPM ceiling at probe 10, the LONGEST
# the transcript ever gets.
# ═══════════════════════════════════════════════════════════════════════════


class Probe(BaseModel):
    probe: str  # candidate-facing, one or two sentences, ends in a question
    angle_used: str  # copied verbatim from a probe_ladder entry's `angle`, or "" if it follows the answer instead


# 🔴 THE TOKEN BUDGET, ALREADY MEASURED -- do not re-derive it, this constant
# IS the derivation. Measured 2026-08-06 with tiktoken's o200k_base against
# the eight real curated worlds (largest, openai.json, 1,392 tok) and a
# ~700-token probe prompt, at probe 10 (the transcript's longest point):
#
#                                    typical 250-word answers   verbose 500-word answers
#   full transcript                          7,074                  10,274  <- OVER the 8,000 TPM ceiling
#   first answer + last 4 turns              5,154                   6,754  <- fits
#
# So the window is fixed, not adaptive: the candidate's FIRST answer (their
# actual thesis -- every later probe pushes on it) plus the last 4 turns.
# PHASE-3.5-SPEC.md § "The budget change": "the fallback is the main
# question plus case_world plus improvised_facts plus the last N turns --
# decided by measurement, not taste." N = 4 is that measurement.
_TRANSCRIPT_TAIL_TURNS = 4


def _windowed_transcript(transcript_turns: list[dict]) -> list[dict]:
    """The candidate's first answer, plus the last `_TRANSCRIPT_TAIL_TURNS`
    turns -- see the budget comment above for why this window and not the
    full transcript. `transcript_turns` is never mutated; this returns a new
    list (or the identical tail list when the first answer already falls
    inside it, so a short interview is not duplicated).

    Turns before the first candidate answer (there should be none -- a probe
    is only ever generated after an answer exists) are silently excluded by
    construction; this function does not special-case that, it just finds
    the first `role == "candidate"` turn wherever it is.
    """
    if not transcript_turns:
        return []
    tail_start = max(0, len(transcript_turns) - _TRANSCRIPT_TAIL_TURNS)
    tail = transcript_turns[tail_start:]
    first_answer_idx = next(
        (i for i, turn in enumerate(transcript_turns) if turn.get("role") == "candidate"), None
    )
    if first_answer_idx is None or first_answer_idx >= tail_start:
        return tail
    return [transcript_turns[first_answer_idx], *tail]


def _render_transcript(turns: list[dict]) -> str:
    """Flat, readable rendering of a (already windowed) turn list for the
    prompt. Not JSON -- this is prose the model reads, not data it parses."""
    if not turns:
        return "(no answer yet)"
    return "\n".join(f"{turn.get('role', '?')}: {turn.get('text', '')}" for turn in turns)


def _covered_probe_count(transcript_turns: list[dict]) -> int:
    """How many probe_ladder entries have already been consumed, inferred
    from the FULL (unwindowed) transcript: every interviewer turn after the
    opening question corresponds to one probe already asked, in ladder
    order. Used only as an index into the ladder in
    `resolve_primary_dimension` below -- never exposed as a literal "these
    dimensions are covered" set, because nothing here actually tracks which
    dimension a given past probe used (that requires re-deriving each past
    `angle_used`, which this function deliberately does not attempt)."""
    interviewer_turns = sum(1 for turn in transcript_turns if turn.get("role") == "interviewer")
    return max(0, interviewer_turns - 1)  # the opening question consumes no ladder entry


def _normalise_angle(angle: str) -> str:
    """Casefolded, whitespace-collapsed, trailing-punctuation-stripped form
    of a ladder angle, used only for matching -- never for display, and
    never written back to state. Deliberately narrow: it forgives the ways a
    model re-types a sentence it was told to copy (a dropped final period,
    doubled spaces, a capitalised first letter), and nothing else. Two
    genuinely different angles must still compare unequal, or the resolution
    below would silently attribute a probe to the wrong rubric dimension,
    which is worse than falling back positionally."""
    return " ".join(angle.split()).casefold().rstrip(".?!:; ")


def resolve_primary_dimension(
    angle_used: str, probe_ladder: list[dict], transcript_turns: list[dict]
) -> str:
    """🔴 THE PRIMARY_DIMENSION IS RESOLVED IN PYTHON, NOT BY THE MODEL --
    same philosophy as `planner.py`'s `_first_dimension`: a prompted rule is
    not a rule, so this is not asked of the model at all. Exported (no
    leading underscore) because the graph node that calls `generate_probe`
    (a separate unit, not this story's scope) needs this to update
    `dimension_coverage` after the call returns -- `Probe` deliberately has
    no `primary_dimension` field of its own, per the brief's fixed schema.

    Resolution order:
      1. `angle_used` matches a `probe_ladder` entry's `angle` under
         `_normalise_angle` -> that entry's `primary_dimension`.
      2. No match (including `angle_used == ""`, the "I followed the
         answer" case) -> the first ladder dimension not yet covered,
         where "covered" is inferred positionally from how many probes have
         already been asked (`_covered_probe_count`).
      3. Every ladder entry already consumed -> the first entry's
         dimension, same fallback `_first_dimension` uses for an otherwise
         unresolvable case.

    🔴 Step 1 matches on a NORMALISED angle, not byte-for-byte, and that is
    a measurement rather than a preference. The prompt tells the model to
    copy the angle "EXACTLY, character for character"; on 2026-08-06 it did
    so in 1 of 4 live probes, dropping the trailing period the other three
    times. Every one of those three fell through to the positional fallback
    and resolved to the same dimension, which quietly collapses the ladder's
    whole rubric coverage -- the thing Phase 4's Evaluator reads. A prompted
    exactness rule is not a rule (the em-dash lesson, third occurrence).

    Raises nothing: an empty `probe_ladder` is `generate_probe`'s guard to
    raise on, not this function's -- by the time this runs, a probe was
    already generated against a non-empty ladder.
    """
    if angle_used:
        wanted = _normalise_angle(angle_used)
        for entry in probe_ladder:
            if _normalise_angle(entry.get("angle", "")) == wanted:
                return entry["primary_dimension"]
    issued = _covered_probe_count(transcript_turns)
    if issued < len(probe_ladder):
        return probe_ladder[issued]["primary_dimension"]
    return probe_ladder[0]["primary_dimension"]


# One block, same reasoning as the clarification prompt and every other
# agent in this product -- every constraint the golden suite (and the
# manual "does a probe respond to the answer" pass, per the brief, since
# that property cannot be tested offline) checks stays visible in one place.
_PROBE_SYSTEM_PROMPT = """You are probing a PM candidate's answer to ONE open-ended product strategy question, live, \
mid-interview. You never ask a new question -- you push on what the candidate ACTUALLY SAID, the way a real \
interviewer leans forward and asks "wait, what about X" rather than reading from a script. Answer directly with the \
JSON object; do not deliberate at length before answering.

🔴 THE PROBE MUST RESPOND TO THE ANSWER GIVEN, not to the question in the abstract. Quote or name something specific \
the candidate actually said -- a number they cited, a tradeoff they picked, a claim they made -- and push on it. A \
probe that would read identically against a completely different answer is not a probe; it is a canned line wearing \
one, and that failure is exactly why the transcript below exists.

ANGLE_USED: choose the entry from the probe ladder below whose intent this probe most advances, and copy its `angle` \
text into this field EXACTLY, character for character. If the candidate's own answer opened a thread worth chasing \
that no ladder entry covers, you may follow that thread instead -- in that case set `angle_used` to the empty string. \
Never invent a new angle string that merely resembles one on the ladder; that is neither a ladder angle nor a clean \
signal that you departed from it.

GROUNDING: never state a number, company, product, person, or date that is not in the case world below or in the \
list of facts already improvised this interview (given below, if any). If your probe needs a fact the world does not \
supply, ask the candidate to state their own assumption rather than supplying one yourself -- inventing a fact is \
`answer_clarification`'s job, not this one's.

Candidate-facing prose, one or two sentences, ending in a question mark: never an em-dash or en-dash (use a comma or \
"and" instead), no fake-round numbers like "50% of customers," no placeholder names ("Acme", "TechCorp", "John Doe" \
and that register). Do not evaluate, praise, or hint at how the candidate is doing -- you are asking a question, not \
judging one. Do not introduce yourself or use a persona name; you are the interviewer, not a character. Do not \
restate or paraphrase the main question.
"""


def _build_probe_messages(
    case_world: dict,
    improvised_facts: list[str],
    main_question: str,
    probe_ladder: list[dict],
    transcript_turns: list[dict],
) -> list[tuple[str, str]]:
    """Pure message assembly, split out from `generate_probe` so the token
    budget can be measured offline against `tiktoken`, with no LLM call --
    see `tests/test_interviewer_probe.py`'s budget test, which calls this
    directly."""
    window = _windowed_transcript(transcript_turns)
    human = (
        "Case world:\n"
        + json.dumps(case_world, indent=2)
        + "\n\nFacts already improvised earlier in this interview:\n"
        + (json.dumps(improvised_facts, indent=2) if improvised_facts else "(none yet)")
        + "\n\nThe main question on the table (do not restate it, probe what the candidate said about it): "
        + main_question
        + "\n\nProbe ladder -- pick the angle this probe advances, or depart from it and set angle_used to \"\":\n"
        + json.dumps(probe_ladder, indent=2)
        + "\n\nTranscript so far (the candidate's first answer, plus the most recent turns):\n"
        + _render_transcript(window)
    )
    return [("system", _PROBE_SYSTEM_PROMPT), ("human", human)]


async def generate_probe(
    case_world: dict,
    improvised_facts: list[str],
    main_question: str,
    probe_ladder: list[dict],
    transcript_turns: list[dict],
    *,
    role: Role = "fast",
) -> Probe:
    """Writes the next probe against the candidate's most recent answer.
    Pure function: no DB, no session, no side effects -- see module
    docstring. `case_world` and `improvised_facts` are READ ONLY, same rule
    as `answer_clarification`.

    `transcript_turns` is the FULL turn list (every turn of the interview so
    far); this function windows it itself via `_windowed_transcript` -- see
    the token-budget comment above `_TRANSCRIPT_TAIL_TURNS`. Each turn is
    `{"role": "interviewer" | "candidate", "text": str}`.

    The model fills `probe` and `angle_used` only. `primary_dimension` is
    NOT part of this return value and is never asked of the model -- call
    `resolve_primary_dimension(result.angle_used, probe_ladder,
    transcript_turns)` afterward, same split as `planner.py`'s
    `_first_dimension` (the model fills, Python decides).

    🔴 `max_tokens=2048`, raised from 1024 on 2026-08-06 BY MEASUREMENT, and
    the reasoning that produced 1024 was wrong in an instructive way. It
    argued from OUTPUT size: `Probe` is two short strings, smaller than
    `ClarificationAnswer`'s three, so it should need less. But `max_tokens`
    on gpt-oss is not an output budget, it is a reasoning-plus-output budget
    -- the model emits reasoning tokens against it BEFORE the JSON starts
    (DEV-STATE § Decisions 2026-08-04) -- and reasoning scales with the
    INPUT, which for a probe grows with every turn of the transcript.

    Observed: probes 1 and 2 succeeded, then `json_validate_failed` twice in
    a row at probe 3 with a longer transcript, failing the probe-loop test
    while the same test passed in isolation. The error names the prompt
    ("Please adjust your prompt") and the prompt is not the problem.

    Raises `ValueError` on an empty `case_world`, `main_question`, or
    `probe_ladder`, matching how `answer_clarification` and `plan_interview`
    guard their inputs.
    """
    if not case_world:
        raise ValueError("generate_probe requires a non-empty case_world")
    if not main_question or not main_question.strip():
        raise ValueError("generate_probe requires a non-empty main_question")
    if not probe_ladder:
        raise ValueError("generate_probe requires a non-empty probe_ladder")

    llm = get_llm(role, max_tokens=2048).with_structured_output(Probe)
    messages = _build_probe_messages(
        case_world, improvised_facts, main_question, probe_ladder, transcript_turns
    )
    return await llm.ainvoke(messages)

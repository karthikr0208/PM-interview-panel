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
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from app.llm import Role, get_llm


class ClarificationAnswer(BaseModel):
    can_answer: bool  # False => the world does not specify this
    answer: str  # candidate-facing prose
    grounded_in: list[str]  # case_world facts this answer rests on


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

# The real work (spec §2b): reads case_world and the current question, and
# nothing else -- no resume, no profile, no level, no transcript. Every
# constraint the golden suite checks (grounding, the figure check, refusal
# quality, dash/round-number/name hygiene) stays visible in one block, same
# reasoning as case_architect.py's and planner.py's prompts.
_CLARIFICATION_SYSTEM_PROMPT = """You are answering ONE clarifying question a PM candidate asked mid-interview, using \
ONLY the case world given below. Answer directly with the JSON object; do not deliberate at length before answering.

THE HARD REQUIREMENT: never state a number, company, product, person, or date the case world does not contain. If the \
world does not answer the question, set can_answer to false and say so explicitly in `answer` using language like \
"the brief does not specify" or "the world does not state" -- do not extrapolate, do not offer a "reasonable \
assumption," and do not answer a nearby question the world CAN support instead of the one actually asked.

WATCH FOR A LEADING QUESTION that presupposes something the case world contradicts or never states (for example, \
"given that churn has been climbing all year..." against a world stating one flat monthly figure). Do not accept a \
false premise merely because the question is phrased as if it were true -- correct it, using only what the world \
actually says, and do not repeat the false claim back as if agreeing with it.

GROUNDED_IN, checked mechanically, same rule as the interview plan itself: every entry must be copied EXACTLY, \
character-for-character, from the case world -- never paraphrased, never empty, 1-3 entries. Use the company name, a \
competitor or entity name exactly as written, a bare number exactly as it appears in the schema with no unit added, or \
a supporting_facts string copied in full. `grounded_in` must be non-empty even when you cannot answer: ground the \
refusal in the nearest thing the world DOES say, so a refusal still rests on something real rather than nothing at all.

WHEN can_answer IS FALSE: `answer` must contain NO number of any kind, and must explicitly name what the world does not \
specify, state, or provide -- a vague non-answer like "I'm not sure" is not acceptable; name the silence directly.

WHEN can_answer IS TRUE: every number in `answer` must appear in the case world above, exactly as it is written there \
(a comma or a $ sign may be added; nothing may be invented). Cite it the way you would say it aloud, never as a raw \
JSON field name and value.

Candidate-facing prose, 2-4 sentences: never an em-dash or en-dash (use a comma or "and" instead), no fake-round \
numbers like "50% of customers" (use the world's own organic decimal precision), no placeholder names ("Acme", \
"TechCorp", "John Doe" and that register). Do not evaluate, hint at, or coach the candidate's question or the answer \
they are building toward -- you are stating a fact, not judging one. Do not introduce yourself or use a persona name; \
you are the interviewer, not a character. Answer the question asked; do not restate the interview's original question.
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
) -> ClarificationAnswer:
    """Answers `clarifying_question` from `case_world` alone. Pure function:
    no DB, no session, no side effects -- see module docstring.

    🔴 Signature is fixed by the golden suite's call site (positional
    `case_world, planned_question, clarifying_question`, keyword `role`) --
    do not change it; `tests/golden/interviewer/test_golden.py` calls it
    exactly this way.

    `case_world` is READ ONLY, same rule as `plan_interview` and
    `generate_case_world`: this function must never mutate the dict it is
    given, and the node calling it must never write `case_world` back to
    state -- it was already written once, by the Case Architect
    (ARCHITECTURE §2).

    `max_tokens=2048` per AGENT-INTERVIEWER-SPEC.md §6's computed table --
    a PROJECTION as of story 3.2, not yet a measurement against a real
    `Requested` header. If Groq returns `json_validate_failed`, RAISE this
    rather than shortening the prompt: gpt-oss emits reasoning tokens
    against `max_tokens` before the JSON starts, and that error reads like
    a prompt problem and is not one (DEV-STATE § Decisions 2026-08-04).

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

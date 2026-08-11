# Phase 5 — The Coach: three improvements, each anchored to a moment that actually happened

**Status:** 🟡 **ALL FOUR STORIES BUILT 2026-08-11 and offline-green. The LIVE SUITE IS OWED** after two migrations, plus one clean coach golden pair run, 5.3's one-call assertion, and a live interview Karthik reads. Prior note: **5.1 PART-DONE. 5.2 is next.** Written 2026-08-11, before any code. The migration is applied to the live DB and its constraints are falsified; the budget measurement and the golden fixtures are the rest of 5.1 and can be done alongside 5.2.

**🔴 Read the honesty marker before trusting a number in this file.** Phase 4's spec could open by
saying every number in it was measured. **This one cannot.** The token budget in § 2 below is an
ESTIMATE built from measured components, and story 5.1 owes the real measurement before the node is
built. Where a number is measured it says so and names the date; where it is projected it says
that too. Do not let the two blur.

The Coach runs once, at the end, and produces three improvements. Each carries an anchor (a moment
from the interview), a stronger version of what the candidate said, and a drill. That is the whole
phase.

---

## 🔴 WHAT IS ALREADY DECIDED, BY MEASUREMENT OR BY SCHEMA. Read this before designing anything.

### 1. THERE IS NO `coach_report` TABLE. The schema is silent, and that is 4.3 inverted.

Six tables exist in `migrations/0001_initial_schema.sql`: `sessions`, `resumes`, `case_worlds`,
`transcript_turns`, `answer_evaluations`, `agent_events`. **None of them holds a coach report.**
`app/graph/state.py:70` carries `coach_report: dict | None`, so the graph has a place to put one in
memory and nowhere to put one durably.

**Story 4.3 had the opposite problem and it was the easier one.** There, the DDL had already
decided the shape and the work was to read it before designing one. Here nothing has been decided,
which means **the shape will be decided by accident — by whatever the first `rest_insert` happens
to pass — unless it is decided on purpose first.** Story 5.1 writes the migration BEFORE the agent,
for that reason.

**The grain is one row per improvement, not a JSON blob.** Same argument that made
`answer_evaluations` one row per `(turn, dimension)`: a blob cannot be constrained, cannot be
queried, and cannot enforce anything at the schema level.

**🔴 The anchor quote carries the same `not null` + `length(...) > 0` check `evidence_quote`
carries.** PRD §8's guarantee is that no score ships without evidence, enforced in Postgres rather
than by convention. PRD §10's acceptance for this phase is the same shape — *"each of the 3 items
names a question and quotes the candidate"* — so it gets the same enforcement. **It is free and it
is the single most valuable line in the migration.** An improvement without a quote is advice, and
generic advice is exactly what this product exists not to be.

### 2. THE COACH CAN BE ONE CALL, BUT ONLY BECAUSE IT READS THE EVALUATOR'S OUTPUT.

`ARCHITECTURE.md:121` specifies the Coach as *"whole transcript in one 1M-context call."* **That
model does not exist on this stack.** The ceiling is 8,000 TPM, and the full transcript was measured
at **10,274 tokens on 2026-08-06** (AGENT-INTERVIEWER-SPEC §6). Feeding the Coach the raw
transcript is over the ceiling before the prompt is added — the same wall that forced the Evaluator
into per-answer scoring in 4.2.

**The Coach has an exit the Evaluator did not, and Phase 4 already built it.**
`answer_evaluations` holds, per `(turn, dimension)`, a score, a **verbatim candidate quote**, and
since migration `0004` the Evaluator's **`reasoning`**. That migration's own comment says why it
exists:

> *"the coach report would have to re-derive from a quote and a digit the judgement the Evaluator
> already made and wrote down."*

So the Coach reads **judgement, not raw material**, and the input collapses from a transcript to a
bounded set of rows.

**🔴 Projected budget — NOT MEASURED, story 5.1 owes the real number.** Built from measured parts:
worst real curated world 1,392 tokens (`app/cases/openai.json`, measured 2026-08-09); 25 rows worst
case (5 answers × 5 dimensions) at roughly 80 tokens each; `max_tokens` for three improvements.

```
case_world (worst real world)      ~1,392   measured
25 evaluation rows                 ~2,000   PROJECTED
main question                         ~50   projected
coach system prompt                  ~800   PROJECTED — does not exist yet
max_tokens (3 improvements)          2,048   a choice, not a measurement
                                   -------
                                   ~6,290   against 8,000 -> ~1,700 spare, PROJECTED
```

**Treat that 1,700 as fragile until measured.** § 3 of the 2026-08-11 findings shows exactly how
this goes wrong: the Evaluator's real headroom is 565 tokens, not the 2,613 its budget test
believes, because `max_tokens` drifted and the test did not follow. **Story 5.1's budget test reads
`max_tokens` from a shared constant, never a literal.**

### 3. THE COACH MUST SURVIVE A SESSION WITH PARTIAL OR ZERO EVALUATIONS. This is new as of today.

Two independent reasons, and neither is hypothetical:

1. **Coverage is not guaranteed.** PHASE-4-SPEC § 1 measured a real interview producing evidence
   for **three of five dimensions**; two got zero. `not_assessed` is the normal case, not the edge.
2. **A failed evaluation now writes nothing at all.** Fixed 2026-08-11 (DEV-STATE § Decisions): a
   failing Evaluator degrades to `return {}` rather than ending the candidate's session. **So a
   completed interview can legitimately reach the Coach with rows missing for entire turns.**

**🔴 THREE IMPROVEMENTS, ALWAYS. Karthik's call, 2026-08-11 — and it is achievable WITHOUT padding
because improvements come in two kinds.** The first framing of this question posed a false choice
between three-with-padding and fewer-but-honest. It missed that a thin interview produces MORE
material of the second kind, not less:

| Kind | Shape | Needs a quote? | When coverage is thin |
|---|---|---|---|
| `moment` | "Here is what you said, here is a stronger version" | **Yes** | Fewer available |
| `gap` | "You never took a position on the market at all" | **No — nothing was said to quote** | **More available** |

A dimension in `not_assessed` is not an absence of coaching material. **It is among the most useful
things a coach can say**, and PHASE-4-SPEC § 1 measured a real interview producing two of them. So
three improvements are reachable honestly at every realistic coverage level, and nothing is
invented to reach the count.

**🔴 This collides with § 1's `anchor_quote not null`, and the resolution is NOT to relax it.**
Dropping the constraint to accommodate `gap` rows would surrender the strongest guarantee in the
table for every row, including the ones that can honour it. Instead, **a `kind` discriminator with
the check scoped to where it applies**:

```sql
kind          text not null check (kind in ('moment', 'gap')),
anchor_quote  text,
check (kind <> 'moment' or (anchor_quote is not null and length(anchor_quote) > 0))
```

**Every `moment` improvement still cannot exist without a verbatim quote, enforced in Postgres.** A
`gap` improvement carries a dimension instead, and its truthfulness is checkable a different way:
the named dimension must genuinely be absent from `answer_evaluations` for that session. Assert
that too — it is the same falsifiability, obtained from a different column.

**Only if there is nothing to say at all is there no report.** Zero evaluations AND zero coverage
gaps to name cannot both be true of a completed interview, so in practice this fires only on an
interview that never started. Render an honest empty state naming why; never encouraging filler.

### 4. THE COACH DEFAULTS TO `fast`, AND THAT SUPERSEDES THE PRD.

`PRD.md:54` and `ARCHITECTURE.md:98` both assign the Coach `deep`. **The 2026-08-02 portfolio
calibration says agents default to `fast` and explicitly supersedes ARCHITECTURE §4.** Build on
`fast`. If the output is visibly worse, measure it and say so with samples — **one `deep` sample is
not a measurement**, a rule this project learned in 4.2 and wrote down.

---

## 🔴 Decisions this phase inherits and must not relitigate

| Decision | Where it was made | What it means here |
|---|---|---|
| Absence of a row means "not assessed" | PHASE-4-SPEC 4.3 | No nullable score, no sentinel row, no placeholder improvement |
| `case_world` is immutable after Phase 2 | CLAUDE.md | The Coach reads it, never writes it |
| Agents default to `fast` | DEV-STATE 2026-08-02 | § 4 above |
| No em-dashes in user-facing copy | CLAUDE.md | The Coach's prose is read by the candidate. `normalize_dashes` at the graph boundary, as `reasoning` already does |
| Evidence quotes are NEVER normalised | build.py, 4.3 | The anchor quote is compared to the transcript byte for byte. Normalising one side turns a faithful quote into a mismatch |
| A green run is one sample | CLAUDE.md | Do not conclude the Coach "works" from one report that reads well |

---

## 🔴 Traps carried forward. Every one is a recorded failure from this project.

| Trap | The recorded failure |
|---|---|
| **Re-run every live file that builds a graph** | Story 3.2 and story 4.3 each broke another file's load-bearing assertion via `build.py`. Third occurrence, third file. The Coach adds a node |
| **Deselected is not passed** | 2026-08-05, twice: `N passed, M deselected` read as verification when the deselected were the only tests observing the property |
| **A test can certify a bug** | 2026-08-04's upload defect, and again 2026-08-11 (`..._and_reraises`). When behaviour changes, invert the test, do not delete it |
| **A green budget test can measure a shape that no longer ships** | 2026-08-11, the Evaluator's `max_tokens` drift. Read the constant, never a literal |
| **Classify a 429 before calling it a defect** | Three separate mostly-red runs were rate limiting, once wearing an `AssertionError` written to be believed |
| **Prompting failed twice at the em-dash rule** | 3.3 closed it deterministically instead. Do not try prompting a third time |

---

## Stories

### 5.1 The migration, the budget measurement, and golden fixtures — 🟡 PART-DONE 2026-08-11

- [x] `migrations/0005_coach_reports.sql`. ✅ **DONE 2026-08-11.** One row per improvement, with the
      `kind` discriminator and the scoped check from § 3. **Applied to the live DB and verified by
      direct query**, not by trusting migrate.py's output: 9 columns, 6 check constraints, RLS
      enabled, 1 policy. **Constraints FALSIFIED in Postgres**, with accepted controls so the
      rejections are not vacuous:

```
  REJECTED  moment WITHOUT a quote          REJECTED  gap WITHOUT a dimension
  REJECTED  moment with an EMPTY quote      ACCEPTED  gap WITH a dimension
  ACCEPTED  moment WITH a quote             REJECTED  kind='invented'
                                            REJECTED  duplicate (session, idx)
```
- [x] RLS policy on the new table, matching the existing six. ✅ **DONE 2026-08-11.**
      `probe_realtime.mjs` re-run: **OVERALL: PASS** (own row delivered, other session denied).
      🟡 It failed its positive half once and passed cleanly on re-run — logged in DEV-STATE as one
      of the day's two non-reproducing transient failures.
- [x] ✅ **DONE 2026-08-11, and it FAILED first, which was the point.** `tests/test_coach_budget.py`
      red on all 8 worlds at up to **8,328 / 8,000**; § 2's ~6,290 projection was wrong by ~2,000.
      Now `9 passed` with **1,396-1,522 headroom**. **`max_tokens` comes from a shared constant that
      the call site also reads** — the 2026-08-11 drift must not be re-armed.
- [ ] Golden fixtures, including **one with zero evaluations** and **one with a single turn's
      worth**, because § 3 says both are reachable.
- [ ] The assertion harness reds before the agent exists, with **no stub written to fake it** — the
      shape 4.1 used.

### 5.2 The Coach agent — 🟡 BUILT AND OFFLINE-GREEN 2026-08-11, NEVER RUN LIVE

- [x] `app/agents/coach.py`. ✅ Input is `answer_evaluations` plus a **summarised** `case_world`
      plus the main question. **Not the transcript.** 🔴 The world is summarised because the full
      one does not fit: `supporting_facts` and `suits_categories` are dropped, and quotes are capped
      at 2 per dimension weakest-first. Measured 8,328 → 6,604 on the worst world. See
      § "the budget was projected and the projection was wrong" below.
- [x] Output: **three improvements**, each a `moment` or a `gap` (§ 3), each with a stronger version
      and a drill. ✅ Enforced in the pydantic schema, not requested in the prompt — "up to three"
      silently becomes one on a thin interview and nobody notices.
- [x] ✅ **A `moment`'s anchor quote must be one of the `evidence_quote` values already stored.** This
      is the strong form: it makes every anchor verifiable against the transcript byte for byte
      **without the Coach ever seeing the transcript**, and it makes an invented anchor detectable,
      which ARCHITECTURE §9 says nothing can detect at runtime. Assert it.
- [x] ✅ **A `gap`'s named dimension must genuinely be absent** from that session's
      `answer_evaluations`. `verify_anchors` observed catching both a planted invented quote and a
      planted false gap. Assert it — a `gap` claiming the candidate never addressed something
      they were scored on is the same fabrication in the other direction.
- [x] ✅ Runs on `fast`. Tagged `agent="coach"` in `get_llm` — the six existing call sites are tagged
      and this is the seventh.

### 5.3 The graph node and the write — 🟡 BUILT 2026-08-11, ONE ASSERTION STILL OWED

- [ ] `coach_report` node after the loop exits. **Never inside `await_candidate`.**
- [ ] 🔴 **A failing Coach must not break the scorecard.** Same argument, same shape as the
      2026-08-11 Evaluator fix: the report is a side-effect of a finished interview. Write the error
      `agent_events` record and degrade. The candidate has already earned their scorecard.
- [ ] Assert exactly one Coach LLM call per session, on `app.llm`'s log filtered by
      `agent="coach"`, and **falsify it** against a deliberately wrong graph.
- [ ] 🔴 **Re-run every live file that builds a graph**, not just the one edited.

### 5.4 The coaching report surface — ✅ DONE 2026-08-11

- [x] ✅ Renders three improvements. **`moment` and `gap` render differently** — a moment shows the
      candidate's own words, a gap names what never came up and has no quote element at all.
- [x] ✅ Honest empty state naming why. Reachable in practice because `coach_report` returns `{}`
      on failure, so it is a real branch, not a defensive one.
- [x] ✅ Full loading / empty / error cycle, `stripDashes` throughout.
- [x] ✅ `191 passed, 19 files` (was 172/17), `npm run build` clean, zero LLM budget. Includes a
      test that puts a real em dash in stored data and proves it never reaches the DOM — rows
      written before normalisation shipped really do carry raw characters.
- [x] 🔴 **`0006_coach_reports_realtime.sql`**, unplanned. `coach_reports` was not in the
      Realtime publication, so the surface would have loaded once and never updated. RLS
      membership and publication membership are different guarantees and the checklist only
      names the first. Found by querying the LIVE database, not by reading migrations.

---

## Automated tests

| File | Must assert |
|---|---|
| `tests/test_coach_budget.py` | The request fits 8,000 TPM, with `max_tokens` read from the shared constant |
| `tests/golden/coach/` | Anchors are real stored quotes; a zero-evaluation fixture yields no report; fewer-than-three is allowed |
| `tests/test_coach_report.py` | One call per session, falsified; a failing Coach degrades and does not break the scorecard |
| `frontend/**/*.test.ts` | Three, fewer, and zero improvements each render correctly |

---

## Phase gate

1. ⬜ The migration is applied to the live DB, confirmed by direct query, not by trusting the record
2. ⬜ The budget is MEASURED and under the ceiling
3. ⬜ A Coach report generates live, every anchor traceable to a stored quote
4. ⬜ **Karthik reads a coach report and finds it useful.** His, and not delegable

---

## Handoff

**Verified by me, with evidence:** nothing yet — this spec is written before any code.

**Needs your eyes:**

- **Does reading judgement instead of the transcript cost too much?** The Coach will see quotes and
  the Evaluator's reasoning, not the full answers. Its "stronger version" is therefore a rewrite of
  a sentence rather than of a whole answer. That is a real trade for fitting the ceiling, and
  whether it still produces useful coaching is a quality call, which is yours.
- ✅ **DECIDED 2026-08-11: three, always.** Karthik's call. The padding objection dissolved once
  `moment` and `gap` improvements were separated — see § 3. Nothing about this needs revisiting
  unless a real report shows `gap` items reading as filler, which is a quality judgement and would
  be yours.

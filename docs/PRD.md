# PM Interview Panel — Product Requirements

**Status:** approved for V1 · **Last revised:** 2026-07-29

---

## 1. Problem

PM interview preparation is bottlenecked on realistic practice, not on information.

Question banks give you questions but no interviewer. Peer mocks (Pramp, Exponent) require scheduling and deliver wildly inconsistent quality — your partner may have never conducted an interview. Human coaches cost $200–400 an hour, which caps most candidates at a handful of sessions.

The specific thing that is missing, and that is hard to fake, is **adaptive follow-up**. A real interviewer probes your weakest reasoning, injects a constraint you did not plan for, and pushes back on your recommendation. Research across Exponent, Meta, and Amazon interviewer guidance converges on the same signal: a strong-hire answer is one that gets *sharper* under that pressure, not one that merely survives it. You cannot practice that against a static question list.

## 2. Goal

A candidate finishes a 45-minute simulated Product Strategy interview and receives a scored, evidence-linked scorecard plus three specific, actionable improvements — each anchored to an exact moment in their own transcript.

## 3. Non-goals for V1

Voice or video. Multi-round onsite loops. Behavioral rounds. Human review. An interviewer marketplace. Payments. Native mobile apps.

## 4. Users

**Primary** — a working PM with 2–8 years of experience preparing for interviews at a specific company. They have read the frameworks. They need repetitions under pressure and an honest read on where they actually stand.

**Secondary** — an aspiring PM who wants to know whether they are close, and what the gap is.

## 5. Core flow

```
Upload resume
  → confirm extracted profile and assessed level
  → read interview briefing (company, market, context)
  → 45-minute chat interview
      one main strategy question
      3–5 adaptive follow-ups
      candidate may ask clarifying questions at any point
  → scorecard: 5 dimensions, every score linked to transcript evidence
  → coach report: 3 improvements, each with a moment, an example, and a drill
```

## 6. The agent panel

Six agents. Two of the six — the Case Architect and the deferred Calibration agent — came out of research rather than the original design; see `docs/research/research-pm-interviews.md` §11 for the reasoning.

| # | Agent | Runs | Input | Output | Model |
|---|---|---|---|---|---|
| 1 | **Resume Analyst** | Once, on upload | Resume text | Structured profile, level (APM/PM/Senior PM/GPM), rationale, low-confidence flags | deep |
| 2 | **Case Architect** | Once, after level confirmed | Level, candidate's domain | Locked `CaseWorld`: company, market, competitors, financials, strategic tension, constraints | deep |
| 3 | **Interview Planner** | Once | Level, `CaseWorld` | Question plan, probe angles, rubric-coverage targets, time budget | deep |
| 4 | **Interviewer** | Every turn | Plan, `CaseWorld`, transcript, coverage state | Next utterance; probe, advance, or answer a clarification | **fast** |
| 5 | **Evaluator** | After each answer | Answer, rubric, `CaseWorld` | Per-dimension scores with verbatim evidence quotes | deep |
| 6 | **Coach** | Once, at end | Full transcript, all evaluations | 3 improvements, each with anchor, stronger-version example, drill | deep |

`fast` is `nvidia/nemotron-3-nano-30b-a3b`, `deep` is `nvidia/nemotron-3-super-120b-a12b`. Only the Interviewer runs while a candidate is waiting, so it is the only one that trades depth for latency.

Model choice was settled by measurement rather than by capability documentation. GLM 5.2 was the original pick and is genuinely more capable, but on NVIDIA's free tier a trivial prompt took **~230 seconds**, nearly all of it queueing. Popular models are contended; NVIDIA's own Nemotron models answered the same prompt in under half a second. On a free tier, how contended a model is matters more than how capable it is — and only the second of those is documented. See `docs/DEV-STATE.md` for the measurements.

**Deferred to a later milestone: Calibration / Bar-Raiser agent.** Every real company has a scoring mechanism external to the interviewer — Amazon's Bar Raiser, Google's hiring committee, Meta's cross-interviewer packet — specifically because single-evaluator scoring inflates and drifts. It costs one LLM call per session, not per turn. It is out of V1 only because drift is unobservable until there is a corpus of sessions to observe it in.

## 7. Scoring rubric

Five dimensions, equally weighted, scored Strong No Hire / No Hire / Hire / Strong Hire, mapped to 1–4. Derived from Exponent's published product-strategy rubric and cross-checked against Google's competency names and Meta's three-pillar model. Weakness in one dimension is not offset by strength in another.

| Dimension | 1 — Strong No Hire | 4 — Strong Hire |
|---|---|---|
| **Business model fluency** | No grasp of how the company makes money | Revenue mechanics are load-bearing in the recommendation, not decoration |
| **Market accuracy** | Invents or misreads the competitive landscape | Correctly reads the given market, identifies the real structural threat |
| **Decision quality** | Hedges, or picks without stating criteria | Commits to one option, states criteria first, names what is being given up |
| **Structural clarity** | Rambles; the interviewer has to drag the answer forward | States the approach up front, signposts transitions, adapts structure to the prompt |
| **Point of view** | Restates the prompt back; no thesis | Has a defensible thesis and sharpens it under pushback |

Two cross-cutting modifiers, recorded separately from the five scores:

**Level calibration.** The same answer is a Hire at PM and a No Hire at Senior PM. Anchors shift with `assessed_level`. Research is consistent that the dimensions do not change with seniority — the bar within each dimension does.

**Framework narration penalty.** Reciting a framework step by step ("now I'll do the C in CIRCLES") reads as junior to real interviewers. Internalized structure scores higher than narrated structure.

## 8. Product decisions worth stating

**Questions are revealed whole, never token-streamed.** Streaming is a latency-masking technique borrowed from chatbot UX. Real interviewers ask fully-formed questions. Streaming the question undercuts the interviewer-as-authority framing the persona header establishes.

**No radar chart on the scorecard.** Observable, NN/g, and Scott Logic independently document two flaws: axis ordering changes the shape, so appearance is partly an artifact of arbitrary ordering; and connecting lines between unrelated competencies imply a continuity that does not exist. Horizontal bars, with the numeric value always visible next to the bar.

**Every score carries a verbatim quote.** A score without evidence is opaque and arguable. A score with the exact sentence that produced it is falsifiable and actionable. This is enforced at the schema level, not by convention.

**Elapsed time, not a countdown.** Timer-anxiety research is genuinely split, and WCAG 2.2.1 requires any content-imposed time limit to be adjustable, extendable, or removable. Nothing auto-submits.

**Blind mode.** Showing a candidate their scores falling in real time during an interview is anxiety-inducing and unlike any real interview. The right panel defaults to scores-visible, with a toggle that swaps to coverage-and-progress signals only and reveals full scores at the end.

**The orchestration is visible, not hidden.** UI research argued for collapsing the agent panel so the candidate stays focused. This product is a multi-agent orchestration platform and should read as one — the panel is a first-class column, not a drawer.

## 9. Success criteria

Each is verified by observation, not by reasoning about the code.

| Criterion | Verification |
|---|---|
| Interview completes end-to-end without factual self-contradiction | Ask 5 clarifying questions designed to catch inconsistency in the case world; zero contradictions |
| Follow-ups are adaptive, not scripted | Two runs with deliberately different answer quality produce visibly different probes |
| Every score has a verbatim transcript quote | Automated: assert every `evidence` string appears verbatim in `transcript_turns` |
| Session survives a Render cold start mid-interview | Idle 20 minutes mid-interview, submit an answer, confirm resume from checkpoint |
| Full session stays under the rate ceiling | Log every LLM call with a timestamp; assert peak minute < 40 requests |
| Coach report cites specific moments | Manual review: each of the 3 items names a question and quotes the candidate |

## 10. Constraints

The entire stack is free tier, which is a design constraint rather than a cost note. It is the reason the architecture is checkpoint-resumable and single-process rather than a conventional API-plus-worker-queue design.

| Constraint | Limit | Consequence |
|---|---|---|
| NVIDIA NIM free tier | 40 requests/minute | ~2 LLM calls per candidate turn. Fine for one candidate, tight for a two-session demo. |
| Render free web service | 512MB RAM, spins down after 15 min idle, ephemeral disk, **no free background workers** | Evaluation runs inline in the graph. All durable state lives in Supabase. |
| Supabase free tier | 500MB database, **project pauses after 7 days idle** | A demo left untouched for a week goes dark until manually resumed. |
| Netlify free tier | Static hosting | Serves the frontend bundle only; no LLM traffic passes through it. |

## 11. Backlog

Product Sense, Execution, and Behavioral rounds · Calibration agent · Supabase Auth and the progress-over-time chart · transcript summarizer (only if multi-round) · interviewer persona variants (friendly peer, stone-faced, Bar Raiser) · Amazon-style written memo mode.

---

**See also:** [ARCHITECTURE.md](ARCHITECTURE.md) · [DEV-STATE.md](DEV-STATE.md) · [research/](research/)

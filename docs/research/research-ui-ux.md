# UI/UX Research: PM Interview Panel — Interview Chat + Orchestrator Dashboard

Conducted 2026-07-29 across 23 lookups into real products and design writing. Source for the
UI decisions in `docs/ARCHITECTURE.md` §8.

> **Superseded in one place:** this research recommended collapsing the orchestrator into a
> hidden slide-over panel so the candidate stays focused. The product is a multi-agent
> orchestration platform and should read as one, so the orchestration is a **first-class
> column** in a three-column desktop shell. Its recommendations on question reveal (whole, not
> token-streamed), radar charts (avoid), evidence-linked scoring, and visual direction all stand.

---

## 1. Interview chat UI

### What makes it feel like an interview, not a chatbot

The products that succeed at this (Karat, interviewing.io, Pramp/Exponent) all share one trait:
**the interviewer is a specific, named entity with a stable identity**, not "AI Assistant." Karat's
whole pitch is that a live, credentialed "Interview Engineer" runs a standardized script — the
product literally centers the human proxy's presence as the source of legitimacy and fairness
("Why We Interview," karat.com/why_we_interview). Pramp/Exponent's peer format works because you
see who you're paired with. Translate that into your chat UI as concrete affordances:

- **Persistent interviewer identity header**: name + role/persona (e.g., "Maya Chen, Senior PM
  Panelist") pinned above the transcript, not just a bot icon. This is the single highest-leverage
  change — it reframes every message that follows.
- **Progress indicator, not infinite scroll**: "Question 3 of 7" or a segmented progress bar.
  Chatbots have no sense of "how much is left"; interviews structurally do, and revealing that
  structure is itself reassuring.
- **A visible session state, not just a message stream**: elapsed time, paused/live status.
- **A "thinking" indicator that reads as evaluative, not generative**: three dots labeled
  "Maya is reviewing your answer…" rather than a generic typing ellipsis — same visual, different
  copy, different meaning to the candidate.

**Streaming vs. reveal-at-once for the interviewer's question**: reveal the full question at once.
Token-by-token streaming is a generation-latency-hiding trick borrowed from chatbot UX (Vercel AI
SDK's `useChat`, ChatGPT, Claude — see aiuxplayground.com/pattern/streaming: streaming exists so
"users see progress immediately instead of staring at a blank wait state... time to first token
feels faster even when total generation time is unchanged"). That's solving a *waiting* problem.
An interview question is not something a candidate should watch being typed live — real
interviewers don't type their questions live in front of you; they ask, fully formed. Streaming
the *question* undercuts the interviewer-as-authority framing you just built with the persona
header. Reserve streaming for candidate-facing utility moments where latency-masking genuinely
helps (e.g., a "generating your scorecard" state after the interview ends), and use a short,
fixed "thinking" delay (600–1200ms) + reveal-whole for questions and follow-ups.

### Composing long answers

PM interview answers are structured, multi-paragraph reasoning (not short chat turns), so the
input should look and behave more like a **document composer than a chat bar**:
- A large, resizable textarea (not a single-line growing chat input) that expands with content,
  minimum ~4-5 visible lines.
- **Draft autosave** to local storage / backend on every few keystrokes or on blur — losing a
  3-paragraph answer to a refresh is the single worst failure mode in this product category.
- Lightweight structure support: bullet/numbered list shortcuts and bold, not a full markdown
  toolbar — PM answers benefit from "first... then... trade-off is..." structure, and a bullet
  affordance nudges that without turning the box into a word processor.
- Word count as ambient guidance, not a hard limit ("142 words" quietly in the corner) — gives
  candidates a feel for whether they're being too terse or rambling, without gamifying length.
- **Do allow editing before send, disallow after** — once submitted, treat it like a real
  interview answer (immutable, timestamped), matching interviewing.io/Karat's model where the
  transcript is the record of what happened. Offer "ask a follow-up on this" instead of "edit
  your last answer."

### Timers

The research on timer anxiety is directly relevant and somewhat split, which argues for a
**default-visible-but-dismissible, never-hard-cutoff** design:
- A visible countdown "amplifies anxiety" and "the ticking clock increases anxiety and pressure to
  perform quickly" for a meaningful share of users (medium.com/design-bootcamp, "The Stress of
  Countdown Clocks").
- But a companion finding (NCBI, PMC12731990, "Time on Their Side") found visual timers *lower*
  anticipatory anxiety before a task starts, with highly heterogeneous engagement — a quarter of
  users watch it constantly, many ignore it.
- WCAG 2.2.1 (Timing Adjustable) is unambiguous for anything assessment-like: users must be able
  to turn off, extend (≥10x, with ≥20s warning), or adjust any content-imposed time limit unless
  timing is "essential" — and even then, best practice is "avoid unnecessary time limits
  altogether" (w3.org/TR/UNDERSTANDING-WCAG20, accessguide.io/guide/time-limits).

**Recommendation**: show elapsed time, not countdown, by default ("18:42 elapsed" not "11:18
left"). Offer an optional per-question soft timer a candidate can opt into (useful for people who
specifically want timed-pressure practice), collapsed by default behind a toggle. Never
auto-submit or auto-fail on time — a gentle "you've spent longer than average on this one, want to
wrap up or keep going?" nudge is the ceiling of assertiveness this should have.

### Visual differentiation of message types

Four distinct message kinds need distinct treatment, modeled on how transcript/caption tools
separate speaker turns from meta-events:
1. **Main question** — full-width, persona avatar + name, no indent, slightly larger type.
2. **Follow-up/probe** — same avatar but smaller, indented ~24px with a thin left rule, and
   optionally a small "follow-up" label — signals "still Maya, but drilling into your last
   answer," not a new topic.
3. **Candidate's clarifying question → interviewer's clarification answer** — this needs its own
   affordance so it doesn't read as "your answer to the main question." Give the candidate an
   explicit secondary action distinct from the send button: a small "Ask a clarifying question"
   link/icon near the composer that opens a lightweight inline reply thread visually nested under
   the question being clarified, styled with a "?" glyph, and clearly separated from the main
   answer flow (candidates in real interviews ask "should I assume we have engineering capacity"
   — the UI should make that feel low-stakes and distinct from "submitting my answer").
4. **System/meta messages** ("You paused," "Interview resumed," "Draft autosaved") — centered,
   small caps or muted gray, no avatar, no bubble — the visual language of a timestamp divider in
   iMessage/Slack, not a chat turn.

### Candidate clarifying questions — UI affordance

Concretely: a persistent, low-emphasis "Ask a clarifying question" affordance next to (not
inside) the main compose box, so it's always available but never competes with "submit my answer"
as the primary action. This mirrors how real interview candidates raise a hand mid-question — a
side channel, not the main channel.

### Pause/resume and session recovery

Model this after resumable-form UX plus the "draft autosaved" pattern: persist full state
(current question index, elapsed time, in-progress draft text, which follow-ups have fired) server
-side on every turn. On return, show a distinct "Welcome back" interstitial — not just resuming
silently mid-transcript — that states where they left off ("You were on Question 3 of 7, paused
at 18:42") and gives an explicit "Resume" action, echoing session-recovery patterns from
assessment/exam software rather than casual chat apps (where silent resume is fine because nothing
is at stake).

### Mobile considerations

- The composer must not be obscured by the mobile keyboard — pin it above the keyboard with
  `scrollIntoView`/`visualViewport` handling, a common failure point in chat-input mobile web.
- Given the "big textarea" recommendation above, on mobile default to a slightly taller minimum
  height and make it the primary visible element (progress/timer collapse into a compact top bar
  behind a tap-to-expand, not permanently on-screen, to preserve textarea real estate).
- Persona header collapses to just avatar + "Q3/7" on scroll to reclaim vertical space.

---

## 2. Onboarding + resume upload

### Resume upload → parse → confirm pattern

This "extract, then let the user correct before proceeding" pattern is well established in ATS/HR
tech (Affinda, Skima) specifically *because* parsers are imperfect: "review and edit the parsed
data before submitting... if errors are found, they can be corrected immediately" is standard
guidance (skima.ai/products/ai-resume-parser, affinda.com/resume-parser). Parsing accuracy claims
in that space top out around 95%, which is exactly the regime where a confirmation step earns its
friction cost — not so unreliable that users lose trust, not so reliable that confirmation feels
like busywork.

**Verdict: yes, worth the friction, with conditions.** The confirmation screen should:
- Show extracted fields as **editable inline chips/text**, not a wall of raw JSON or a second
  form — the candidate should feel like they're proofreading a nicely formatted summary, not
  re-entering data.
- Pre-select what the AI is *confident* about (years of experience, most recent title) and
  visually flag low-confidence extractions (a muted-underline or "please check" tag) so the
  friction is concentrated where it's actually needed rather than spread evenly across every
  field.
- Take under 30 seconds to clear — 4-6 fields max (name, current/target title, years of
  experience, key skills, most recent company), not a full resume re-transcription.
- Keep original resume text visible/expandable alongside so corrections are a glance away, not a
  memory test.

### Presenting the AI's level assessment

No single product write-up directly documents this pattern (search returned mostly adaptive-
difficulty research, arxiv.org/pdf/2506.00883, and general framing-effect UX literature —
abtasty.com/blog/framing-effect-ux-testing — rather than a documented consumer example), so this
is a synthesized recommendation grounded in the framing-effect research plus adjacent product
conventions (e.g., LinkedIn Skill Assessments, language-app placement tests):

- **Frame it as a starting point, not a verdict**: "Based on your resume, we'll start you at
  Senior PM difficulty — you can change this anytime" beats "We've assessed you as Senior PM
  level." The first is a system decision offered for editing; the second is a judgment handed
  down. Same information, very different felt stakes — this is exactly the framing-effect
  mechanism (identical facts, different acceptance/anxiety depending on presentation).
  ​
- **Always co-locate an override control with the assessment**, inline, not buried in settings —
  a simple stepper or dropdown (Associate PM / PM / Senior PM / Group PM) right next to the
  stated level, defaulting to the AI's guess but requiring zero clicks-to-menu to change.
- **Show the "why" briefly and factually**: "based on 6 years of PM experience and 2 launches
  mentioned in your resume" — cites evidence rather than asserting a judgment, which reads as
  informative rather than evaluative.
- Never use comparative/scarcity language ("only 12% of candidates interview at this level") —
  that's a dark-pattern borrow from growth marketing, out of place in a practice tool whose whole
  value proposition is low-stakes rehearsal.

---

## 3. Feedback/scorecard UI

### Radar charts vs. bars vs. rows — what the dataviz literature actually says

The evidence against radar/spider charts for this use case is consistent and specific, not just
stylistic preference:
- **NN/g**: circular chart types (pie, gauge, radar) "do not convey well quantitative
  relationships between data" because they rely on area and angle, and "it's harder for people to
  say how much bigger one area is than another" even though area/angle are preattentive
  (nngroup.com/videos/chartjunk, nngroup.com/articles/dashboards-preattentive).
- **Observable** (observablehq.com/blog/avoid-radar-charts): two concrete, damning problems —
  (1) **axis-order dependency**: the same dataset drawn with dimensions in a different order
  around the circle produces a visually different (smoother vs. spikier) shape, meaning the
  chart's *appearance* is partly an artifact of arbitrary ordering, not the data; (2) **the
  connecting lines are meaningless** — categories like "Prioritization" and "Communication" have
  no ordinal relationship, so a line drawn "between" them implies a continuity that doesn't exist.
  Recommended replacement: bar charts (linear or polar) or small multiples/facets.
- **Scott Logic's "A Critique of Radar Charts"** and **data-to-viz's "Radar chart and its
  caveats"** (blog.scottlogic.com/2011/09/23, data-to-viz.com/caveat/spider.html) independently
  converge on the same conclusion: radar charts look impressively "complete" and are popular in
  dashboards for exactly that reason, but they consistently score worse than bar charts on actual
  comparison tasks.

**Recommendation: horizontal bar/row list, not a radar chart.** For 4-6 PM competency dimensions
(structured thinking, prioritization, stakeholder management, data/metrics fluency, communication
clarity), a labeled horizontal bar per dimension, sorted either by category-logical order or by
score, reads faster and doesn't fabricate false relationships between adjacent skills. Reserve
any circular/radar visual only as an optional, secondary "shape of your profile" toy view — never
the primary scoring UI.

### Evidence-linked feedback

The clearest real-world analog is **timestamp-linked transcripts** used in call-review,
legal-discovery, and video-editing tools: "timestamps serve as anchors, connecting the transcript
to the original media... click any timestamp to jump to that moment... reduces time spent
reviewing long recordings" — and critically, granularity should match use: "if downstream use
involves... exact-word quotes, word-level [is needed]; otherwise sentence-level is fine" (pattern
synthesized across transcript-tooling sources; no single canonical named product but the pattern
is consistent across legal/video/podcast tooling).

Apply directly: each score row gets a **"▸ view evidence" expand** that pulls the exact excerpt(s)
from the transcript the score was derived from, with a **jump-to-message-in-transcript** link
(scroll the full transcript view to that turn, highlighted). This is the single most trust-
building feature you can add to the scorecard — it turns "the AI gave me a 5/10 in Data & Metrics"
(opaque, arguable) into "here's the exact moment you didn't propose a metric, here's what a 9/10
answer would have included" (falsifiable, actionable, non-adversarial).

### Coach report layout — actionable, not a wall of text

Cap improvement suggestions at **3 items**, each with the same three-part shape: (1) the specific
behavior to change, stated as an instruction not a diagnosis ("anchor prioritization in a named
framework," not "your prioritization reasoning was weak"), (2) where in *this* transcript it
showed up (links to evidence, reusing the pattern above), (3) optionally a one-line example of
what a stronger version would have sounded like. Three items is a deliberate ceiling — assessment
literature and general coaching-feedback consensus (and Yoodli's own "actionable insights" framing
— yoodli.ai/use-cases/interview-preparation) both point toward a small number of prioritized,
concrete changes outperforming a comprehensive-but-unprioritized list; more than 3-4 items and
candidates remember none of them.

### Progress over multiple interviews

A simple line chart (score-over-time, one line per dimension or one aggregate line) beats any
circular/radar-over-time treatment for the same reasons as above, compounded by the fact that a
"radar chart that changes shape over multiple sessions" is close to unreadable. X-axis = interview
session number/date, Y-axis = score; annotate notable jumps ("+2 after focusing on frameworks")
where the coach report's suggestions were evidently acted on — this closes the loop between
"here's what to improve" and "did it work."

---

## 4. Orchestrator dashboard (multi-agent live progress)

### Visual metaphor comparison

| Metaphor | Where it's used | Fit for a non-technical audience |
|---|---|---|
| **Node-graph, animated active node** | LangGraph Studio: "flowchart-like graph... nodes labeled 'start,' 'agent,' 'action,' 'end'... entire workflow updated in real-time" (datacamp.com/tutorial/langgraph-studio; langchain.com/blog/langgraph-studio-the-first-agent-ide) | Great for engineers debugging graph *topology* (conditional edges, branches, loops). Overkill and intimidating for someone who just wants to know "is my interview being generated." Requires understanding of graph semantics. |
| **Vertical timeline / waterfall** | LangSmith Trace Viewer: "hierarchical timeline of runs... prompt execution, inputs/outputs... pinpoint issues hurting latency" (langchain.com/langsmith/observability) | Reads like a chronological log/receipt — familiar mental model (think: a delivery-tracking page, "Order placed → Preparing → Out for delivery"). Scales well to variable numbers of steps. Easiest to skim top-to-bottom without training. |
| **Kanban of agent states** | Common in AgentOps-style dashboards (aimultiple.com/agentic-monitoring) | Good for showing *many concurrent* long-running agents (production monitoring, dozens of sessions). Less natural for *one* interview session with a handful of sequential/parallel agents — implies more independence between agents than a single-interview pipeline actually has. |
| **Raw log stream** | Fallback / most dev tools' bottom panel | Fastest to build, worst for a "supportive, high-stakes-feeling-calm" product — reads as engineering exhaust, not a feature. |

**Recommendation: vertical timeline/waterfall as the primary view, with a persistent left-rail
"who's active now" agent-status list** (small, ~5 items: Interviewer, Scorer, Follow-up Generator,
Resume Analyst, Rubric Checker), each with a simple status dot (active/idle/done/error) — this is
essentially LangSmith's trace timeline simplified for laypeople, plus a lightweight status-summary
borrowed from the kanban idea without the full board. Avoid the node-graph as the primary/default
view: it requires understanding a DAG to read, and your audience is a PM candidate, not an AI
engineer. If you want the node-graph, ship it as an optional "advanced/technical view" toggle for
power users, not the default.

### What to show per agent/step

Mirror what LangSmith/Langfuse/Braintrust converge on as the minimum useful trace record (langfuse
.com/blog/2024-07-ai-agent-observability-with-langfuse; braintrust.dev/articles/agent-
observability-complete-guide-2026): which agent, what it did (one-line human-readable summary, not
raw JSON — "scored your prioritization answer" not `{"op":"score_dimension"}`), duration, token
count, and a collapsed **"view input/output"** disclosure for anyone who wants to dig in (mirrors
Braintrust's playground pattern of "load any trace, inspect input/output, rerun"). Errors get a
distinct treatment — a warning-colored row with a plain-language explanation ("timed out, retrying
automatically") rather than a stack trace, with a small "view details" for anyone technical who
wants the raw error.

### Placement: separate page, slide-over, or sidebar?

**Recommendation: collapsible sidebar/slide-over, not a separate route**, for one core reason —
the target user is mid-interview and the dashboard's entire value is *ambient reassurance that
something real is happening*, not a destination they navigate to. A separate page breaks flow and
implies "go look at this instead of the interview." A slide-over panel (accessible via a small,
persistent "⚙ What's happening" affordance in the interview header) lets a curious/anxious
candidate glance at it without losing their place, then dismiss it. Default state: collapsed. This
also matches how Langfuse/LangSmith are *secondary* tools that engineers open deliberately, not
things layered into the primary product surface — but since your dashboard is a *feature* of the
candidate-facing app (not a separate ops tool for developers), slide-over beats a whole route.

### Avoiding jitter

- **Throttle updates to ~250-400ms batches** rather than re-rendering on every token/event —
  Langfuse and LangSmith both batch trace updates rather than streaming every sub-event to the UI
  raw.
- New timeline entries **fade+slide in** (150-200ms ease-out), never pop/jump-scroll the view
  unless the user is already at the bottom (classic "new chat message" scroll-anchoring problem).
- Active-node "generating" state uses a **static pulsing dot or indeterminate progress bar**, not
  a constantly-reflowing text preview — reflowing text is the single biggest jitter source in
  agent-trace UIs.
- Collapse older completed steps by default after ~5 are visible, keep counts, not full detail as history grows.

### Libraries

- **React Flow (xyflow/react)** — MIT-licensed, fully free for the open-source core; xyflow sells
  an optional "Pro" subscription (Starter/Professional/Enterprise tiers) for advanced templates and
  prioritized support, not for using the library itself (xyflow.com/open-source, reactflow.dev/pro
  /pricing). Only worth pulling in if you ship the optional "advanced node-graph view" mentioned
  above — for the recommended timeline-primary design you don't need it at all; plain React + CSS
  transitions covers a vertical timeline.
- If a graph view is added later, React Flow is the correct default choice (dominant, MIT, well
  maintained) over alternatives like reaflow or vis-network.

---

## 5. Visual design direction

### Aesthetic: "high-stakes but supportive"

Linear, Raycast, Vercel, and Superhuman all land on the same underlying formula, per design
write-ups of the trend (blog.logrocket.com/ux-design/linear-design; open-design.ai/plugins/design-
system-raycast): **restraint + precision, not decoration**. Specifically: muted, low-saturation
palettes; generous negative space; one confident accent color used sparingly rather than gradients
used everywhere; typography doing most of the visual-hierarchy work instead of color/shadow;
subtle single-layer shadows instead of heavy elevation or glass blur. "Subdued and harmonious
color palettes create a sense of tranquility... muted tones and limited color variations establish
an environment where users can engage without visual clutter" is the calm-design thesis this
product needs, since the emotional job is literally "help someone feel calm enough to think
clearly under simulated pressure."

**Concrete recommendation:**

- **Light mode as default**, dark mode as a toggle, not the reverse. Search results on AI-slop
  tells are explicit: "permanent dark mode as the default reflex is the single most common AI
  tell" (smoothui.dev/blog/ai-design-slop). An interview-prep tool used at a desk in daylight, often
  screen-shared or reviewed later, benefits from a default that reads as documentation-grade, not
  gamer-app-grade.
- **Color palette** (warm-neutral base, single confident accent, no purple/indigo gradient):
  - Background (light): `#FAFAF8` (warm off-white, not stark `#FFFFFF`)
  - Surface/card (light): `#FFFFFF` with a 1px `#E8E6E1` border, not a shadow-heavy card
  - Text primary: `#1A1A18`; text secondary: `#5B5952`
  - Primary accent (interviewer/brand): deep ink-blue `#1D3557` — reads as serious, professional,
    not playful; used for the persona header, primary buttons, active states
  - Supportive/evidence accent (used sparingly, e.g. "evidence" highlight chips, progress
    milestones): warm amber `#C9A227`
  - Semantic: success `#2E7D5B`, warning `#B7791F`, error `#B3452C` — all muted/desaturated
    versions of their hue, never neon
  - Dark mode background: `#16171B`; surface: `#1D1F24`; text primary: `#EDEBE6`; keep the same
    ink-blue/amber accents, lightened slightly (`#4A6FA5` accent, `#D9B24C` amber) for contrast
- **Typography** (Google Fonts, avoid the Inter-alone default that's become an AI tell when
  combined with the gradient/glass look — Inter itself is fine, but pair it with something with
  more character so the product doesn't default to the generic SaaS template look):
  - UI/body: **Geist** (Vercel's typeface, now on Google Fonts) or **Inter** — either is fine for
    body copy and data (scores, timers, transcript text); Geist is currently the fresher choice
    and avoids the most-overused-default feeling Inter has acquired.
  - Display/headings (interviewer name, question numbers, scorecard headline): **Fraunces** — a
    serif with warmth and a bit of personality, used sparingly (headline sizes only) to keep the
    product from reading purely clinical/SaaS-generic. This pairing (geometric sans body + a
    characterful serif display) is exactly the "premium without being ostentatious" formula
    Linear-style write-ups describe.
  - Monospace (timers, token/latency counts, scores): **JetBrains Mono** or **IBM Plex Mono** —
    tabular figures matter here so numbers don't jitter in width as they update.
- **Spacing scale**: 4px base unit — 4, 8, 12, 16, 24, 32, 48, 64, 96px. Standard, predictable,
  matches Tailwind's default scale so it's trivial to implement.
- **Motion principles**: 150-200ms ease-out for all micro-interactions (message entrance, panel
  slide-over, button states); no spring/bounce physics (reads as playful, wrong register for this
  product); respect `prefers-reduced-motion` everywhere; the *only* place a slightly longer,
  more deliberate animation is earned is the scorecard reveal at the end of a session (400-600ms),
  since that's the emotional payoff moment.

### Anti-patterns to explicitly avoid

Per the AI-slop design-tell research (superdesign.dev/blog/why-ai-design-looks-generic; smoothui
.dev/blog/ai-design-slop; prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-
Website): purple-to-blue gradients, glassmorphism/frosted-glass-cards-floating-in-void, neon-on-
dark glowing card borders, animated accent-glow backgrounds, the "badge above the headline,"
colored-left-border cards used everywhere, over-rounded corners (radius > ~10-12px on everything),
emoji used as functional icons instead of a real icon set, and permanent dark-mode-only design.
These specific tells exist because "the same Dribbble shots, the same Tailwind templates" dominate
training data and default generation — deliberately choosing the warm-neutral/ink-blue/serif-
accent direction above is what avoids landing on the statistical median look.

### Accessibility must-haves for a timed assessment product

- WCAG 2.2.1 compliance on any timer: adjustable, extendable (≥10x, ≥20s warning), or off by
  default — covered in detail in section 1; treat this as non-negotiable, not a nice-to-have,
  given this is explicitly an assessment context (w3.org/TR/UNDERSTANDING-WCAG20).
- Full keyboard operability for every control, including the evidence-jump links and the
  orchestrator slide-over.
- Color is never the sole signal — the agent-status dots (active/idle/error) need a shape or label
  difference too (not just green/gray/red), same for score bars (numeric value always visible next
  to the bar, not implied by length/color alone).
- Respect `prefers-reduced-motion` for all transitions, especially the timeline's entrance
  animations and the scorecard reveal.
- Sufficient contrast: the warm off-white/ink-blue palette above should be checked at WCAG AA
  minimum (4.5:1 body text) — `#1A1A18` on `#FAFAF8` and `#1D3557` on white both clear this
  comfortably.
- Screen-reader announcements for streaming/live-updating regions (the orchestrator timeline, the
  "thinking" indicator) via `aria-live="polite"` so updates aren't silently missed, but not
  `assertive` (which would interrupt and be exhausting given the frequency of updates).

---

## 6. Frontend stack recommendation

### React + Vite vs. Next.js, given Netlify free tier + FastAPI on Render

**Recommendation: React + Vite**, not Next.js. Reasoning:
- Your backend is already a separate service (FastAPI on Render) doing all real work — LLM calls,
  auth, persistence, streaming. Next.js's core value adds (SSR, API routes, ISR) solve a problem
  you don't have, since you're not using Next.js as your backend.
- "React + Vite wins on hosting simplicity and cost, as a static SPA is the cheapest, most portable
  deployment target" and deploys cleanly to Netlify's free tier as static files with zero
  server-rendering complexity, whereas "Netlify has good support for Next.js but with some feature
  gaps with ISR and middleware" (designrevision.com/blog/vite-vs-nextjs) — i.e., Next.js on
  Netlify fights the platform slightly; Vite doesn't fight it at all.
- Nothing about this product needs SEO/SSR (it's an authenticated, session-based practice tool,
  not content that needs to be crawled) — the one class of problem Next.js exists to solve doesn't
  apply here.
- Simpler mental model, faster local dev loop, smaller build output, one fewer framework's
  opinions to work around when wiring up SSE/streaming from FastAPI.

### Styling

**Tailwind + shadcn/ui.** shadcn/ui ships as copy-in component source (not an installed
dependency you can't touch), which matters directly for the "avoid looking AI-generated"
mandate in section 5 — you need to actually override shadcn's defaults (radius, shadow, color
tokens) rather than inherit its out-of-the-box look, and shadcn is specifically designed to be
edited rather than themed-via-props. Tailwind's utility approach also makes the 4px spacing scale
and warm-neutral palette from section 5 trivial to encode as design tokens in `tailwind.config`.

### State/data

- **TanStack Query** for all server state — interview session data, transcript, scorecard,
  orchestrator trace events fetched or polled from FastAPI. It "eliminates most manual caching and
  loading-state code" and is the 2026 default for this (multiple sources converge on "TanStack
  Query for server state, Zustand for client state" as the standard split).
- **Zustand** for local UI-only state — composer draft text (until autosave lands), slide-over
  open/closed, timer-visibility toggle, theme. Keep it small; you likely won't need Redux-scale
  ceremony anywhere in this app.

### Streaming client: EventSource vs. fetch-stream vs. WebSocket

Given the recommendation in section 1 to **not** stream interviewer questions token-by-token, your
real-time needs are narrower than a typical AI chat app: (a) the orchestrator dashboard's live
event feed, and (b) optionally streaming the scorecard-generation "thinking" state at session end.
Both are **server→client only** — the candidate never needs to push a stream, they submit discrete
answers via normal POST requests. That maps cleanly to **Server-Sent Events (EventSource)**, not
WebSockets: "SSE provides a simple, HTTP-based protocol for server-to-client streaming... EventSource
auto-reconnects on connection drop, whereas WebSockets do not reconnect automatically" (ably.com/
blog/websockets-vs-sse; websocket.org/comparisons/sse). WebSockets earn their complexity when you
need true bidirectional low-latency messaging (live typing indicators between two humans, gaming);
you don't have that here. If you later need to send auth headers SSE's native `EventSource` can't
carry, `fetch()` + `ReadableStream` parsed manually is the documented workaround and still avoids
taking on full WebSocket infrastructure.

### Charting library for the scorecard

**Recharts.** Given the scorecard is horizontal bars + a simple line chart (per section 3's
anti-radar-chart recommendation), you don't need visx's low-level D3 control or Nivo's heavier,
more opinionated theming — you need clean, accessible, composable React chart primitives with
broad community support. Recharts is "the default React-native pick... 48.9M weekly npm downloads,
the highest of any React chart library" (multiple 2026 comparison sources), MIT-licensed, and its
~50KB gzipped footprint is a non-issue for a bar chart + a line chart. Visx (Airbnb, MIT, ~15KB) is
the better choice only if you anticipate needing fully custom/non-standard chart shapes later;
Nivo's visual polish is nice but its bundle weight and stronger opinions aren't worth it for two
straightforward chart types.

---

## ASCII Wireframes

### Interview chat screen

```
┌─────────────────────────────────────────────────────────────────┐
│ ● PM Panel — Mock Interview           Q 3 of 7      18:42 ⏸ ▾   │
│ Interviewer: Maya Chen, Sr. PM Panelist                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───┐                                                            │
│  │ M │  MAIN QUESTION                                             │
│  └───┘  "Walk me through how you'd prioritize a roadmap when      │
│          engineering says a feature will take 3x longer than      │
│          estimated."                                              │
│                                                                     │
│                                          ┌─────────────────────┐  │
│                                          │ You                 │  │
│                                          │ First I'd clarify   │  │
│                                          │ the business goal...│  │
│                                          └─────────────────────┘  │
│  ┌───┐                                                            │
│  │ M │  │ FOLLOW-UP (indented, thin left rule)                    │
│  └───┘  │ "What if the business goal is time-sensitive, say a     │
│         │  regulatory deadline?"                                  │
│                                                                     │
│         ─── SYSTEM · You paused the interview at 18:42 ───        │
│                                                                     │
│         ● ● ●  Maya is reviewing your answer…                     │
│                                                                     │
├─────────────────────────────────────────────────────────────────┤
│  [ B  •  1. ]                                   142 words   ✎     │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Type your answer…                                          │   │
│  │                                                             │   │
│  │                                                             │   │
│  └───────────────────────────────────────────────────────────┘   │
│  Draft autosaved  ·  ? Ask a clarifying question       [Send →]   │
└─────────────────────────────────────────────────────────────────┘
```

### Orchestrator dashboard (slide-over panel)

```
┌─────────────────────────────────────────────────────────────────┐
│  Orchestrator · Session #4471                     ▣ Live   [✕]   │
├───────────────┬─────────────────────────────────────────────────┤
│ AGENTS         │  ACTIVITY  (newest at top, throttled updates)    │
│                │                                                  │
│ ● Interviewer  │  ┌ 00:41 ──────────────────────────────────── ┐ │
│   active       │  │ Scorer          scored "Prioritization" (Q3)│ │
│                │  │ 0.8s · 210 tok           [view input/output]│ │
│ ● Scorer       │  └──────────────────────────────────────────── ┘│
│   idle         │                                                  │
│                │  ┌ 00:39 ──────────────────────────────────── ┐ │
│ ○ Follow-up    │  │ Follow-up Gen    drafted probe question     │ │
│   Generator    │  │ 1.2s · 340 tok           [view input/output]│ │
│   idle         │  └──────────────────────────────────────────── ┘│
│                │                                                  │
│ ○ Resume       │  ┌ 00:36 ──────────────────────────────────── ┐ │
│   Analyst      │  │ Interviewer     ▓▓▓▓▓▓▓▓░░  generating…     │ │
│   done         │  └──────────────────────────────────────────── ┘│
│                │                                                  │
│ ⚠ Rubric        │  ┌ 00:31 ──────────────────────────────────── ┐│
│   Checker      │  │ Rubric Checker   ⚠ timed out, retrying (1/2)││
│   error         │  │ 4.1s · recovered            [view details] ││
├───────────────┼──└──────────────────────────────────────────── ┘┤
│ Cost: $0.014   ·   Total latency: 6.1s   ·   9 calls this session │
└─────────────────────────────────────────────────────────────────┘
```

### Final scorecard

```
┌─────────────────────────────────────────────────────────────────┐
│  Your PM Interview Scorecard                    Senior PM level   │
│  Overall: 7.2 / 10 — Strong, with gaps in metrics framing         │
├─────────────────────────────────────────────────────────────────┤
│  Structured Thinking     ████████████████████░░░░  8/10          │
│  Prioritization          ██████████████░░░░░░░░░░  6/10   ▸view  │
│  Stakeholder Mgmt        ██████████████████░░░░░░  7/10   ▸view  │
│  Data & Metrics          ████████████░░░░░░░░░░░░  5/10   ▸view  │
│  Communication Clarity   ██████████████████████░░  9/10   ▸view  │
│                                                                     │
│  ▸view expands the row to the exact transcript excerpt + coach    │
│    note the score is based on.                                    │
├─────────────────────────────────────────────────────────────────┤
│  TOP 3 THINGS TO IMPROVE                                          │
│  1. Anchor prioritization in a named framework (RICE/ICE)         │
│     → seen at Q3, Q5.                          [Read excerpt]     │
│  2. Propose a specific success metric before asked                │
│     → seen at Q4.                              [Read excerpt]     │
│  3. Name the trade-off explicitly, not just describe it           │
│     → seen at Q2.                              [Read excerpt]     │
├─────────────────────────────────────────────────────────────────┤
│  YOUR PROGRESS (line chart, not radar)                             │
│  10 ┤                                                    ●        │
│   8 ┤                        ●            ●                       │
│   6 ┤        ●    ●                                               │
│   4 ┤                                                              │
│     └────────────────────────────────────────────────────────    │
│      Interview 1    2    3    4    5                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sources

- [Product Management Mock Interviews — Exponent](https://www.tryexponent.com/practice/product-management-mock-interviews)
- [AI Mock Interviews — Exponent](https://www.tryexponent.com/practice/ai-mock-interviews)
- [Mock Interviews — Exponent](https://www.tryexponent.com/practice)
- [Google's AI-powered Interview Warmup — 9to5google](https://9to5google.com/2022/05/17/google-interview-warmup/)
- [Google Interview Warmup Shut Down — AceRound](https://www.aceround.app/blog/google-interview-warmup-review/)
- [AI Roleplays for Interview Preparation — Yoodli](https://yoodli.ai/use-cases/interview-preparation)
- [LangGraph Studio Guide — DataCamp](https://www.datacamp.com/tutorial/langgraph-studio)
- [LangGraph Studio: The First Agent IDE — LangChain](https://www.langchain.com/blog/langgraph-studio-the-first-agent-ide)
- [Graph Visualization — DeepWiki](https://deepwiki.com/langchain-ai/langgraph-studio/5.2-graph-visualization)
- [AI Agent Observability with Langfuse](https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse)
- [Observability for LangGraph — Langfuse](https://langfuse.com/guides/cookbook/integration_langgraph)
- [interviewing.io](https://interviewing.io/)
- [interviewing.io out of beta](https://interviewing.io/blog/interviewing-io-is-out-of-beta-anonymous-technical-interview-practice-for-all)
- [Interview Copilot — Final Round AI](https://www.finalroundai.com/interview-copilot)
- [AI Video Interview — HeyMilo](https://www.heymilo.ai/product-feature/ai-video-interview)
- [Micro1 AI Interview Guide](https://aitrainer.work/guides/micro1-ai-interview-guide/)
- [Why We Interview — Karat](https://karat.com/why_we_interview/)
- [The Karat Interview Experience](https://karat.com/candidate-experience/)
- [Clutter-Free Charts — NN/g](https://www.nngroup.com/videos/chartjunk/)
- [Dashboards: Making Charts Easier to Understand — NN/g](https://www.nngroup.com/articles/dashboards-preattentive/)
- [Why you should avoid radar charts — Observable](https://observablehq.com/blog/avoid-radar-charts)
- [A Critique of Radar Charts — Scott Logic](https://blog.scottlogic.com/2011/09/23/a-critique-of-radar-charts.html)
- [The Radar chart and its caveats — data-to-viz](https://www.data-to-viz.com/caveat/spider.html)
- [Stream AI Responses — AI SDK Guide](https://ai-sdk.guide/streaming/)
- [Vercel AI SDK useChat in Production](https://dev.to/whoffagents/vercel-ai-sdk-usechat-in-production-lessons-from-30-days-of-real-traffic-4gbo)
- [Streaming — AI UX Playground](https://www.aiuxplayground.com/pattern/streaming/)
- [WCAG 2.2.1 Timing Adjustable — W3C](https://www.w3.org/TR/UNDERSTANDING-WCAG20/time-limits-required-behaviors.html)
- [Make time limits adjustable — Access Guide](https://www.accessguide.io/guide/time-limits)
- [The Stress of Countdown Clocks — Medium](https://medium.com/design-bootcamp/the-stress-of-countdown-clocks-understanding-panic-inducing-timers-in-ux-psychology-b8d1a6333691)
- [Time on Their Side: Visual Timers and Anticipatory Anxiety — NCBI](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12731990/)
- [xyflow Open Source](https://xyflow.com/open-source)
- [React Flow Pro Pricing](https://reactflow.dev/pro/pricing)
- [Linear design — LogRocket](https://blog.logrocket.com/ux-design/linear-design/)
- [Raycast design system](https://open-design.ai/plugins/design-system-raycast/)
- [Why AI Design Looks Generic — Superdesign](https://superdesign.dev/blog/why-ai-design-looks-generic)
- [AI Design Slop — SmoothUI](https://smoothui.dev/blog/ai-design-slop)
- [Why Your AI Keeps Building the Same Purple Gradient Website](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website)
- [Recharts vs Chart.js vs Nivo vs visx — PkgPulse](https://www.pkgpulse.com/guides/recharts-vs-chartjs-vs-nivo-vs-visx-react-charting-2026)
- [Best React Chart Libraries 2026 — LogRocket](https://blog.logrocket.com/best-react-chart-libraries-2026/)
- [WebSockets vs SSE — Ably](https://ably.com/blog/websockets-vs-sse)
- [WebSocket vs SSE — websocket.org](https://websocket.org/comparisons/sse/)
- [Agent observability: the complete guide 2026 — Braintrust](https://www.braintrust.dev/articles/agent-observability-complete-guide-2026)
- [15 AI Agent Observability Tools — aimultiple](https://aimultiple.com/agentic-monitoring)
- [LangSmith Observability](https://www.langchain.com/langsmith/observability)
- [Pramp FAQ](https://www.pramp.com/faq)
- [Vite vs Next.js 2026 — designrevision](https://designrevision.com/blog/vite-vs-nextjs)
- [Stop Choosing State Management Blindly — Medium](https://medium.com/lets-code-future/stop-choosing-state-management-blindly-zustand-tanstack-query-and-redux-toolkit-finally-9be18cd0ae51)
- [AI Resume Parser — Skima](https://skima.ai/products/ai-resume-parser)
- [Resume Parser — Affinda](https://www.affinda.com/resume-parser/)
- [You've Been Framed: Framing Effect in UX — AB Tasty](https://www.abtasty.com/blog/framing-effect-ux-testing/)

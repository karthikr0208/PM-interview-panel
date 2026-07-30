# Development State

**Last updated:** 2026-07-30 · Session 2

---

## Now

**Phase 0 — Walking skeleton.** Story 0.1 complete and verified. Repo now has a running
FastAPI backend, a Vite frontend, a venv with every dependency installed, and a secret-blocking
pre-commit hook. Next is closing story 0.2's decision gate, which is unblocked now that
`langchain-nvidia-ai-endpoints` is actually installed.

---

## Phase status

| Phase | Status | Spec | Verified |
|---|---|---|---|
| Planning docs | ✅ complete | — | 2026-07-29 — PRD, ARCHITECTURE, CLAUDE.md, research all written |
| 0 Walking skeleton | 🟡 in progress | PHASE-0-SPEC.md | 2026-07-30 — 0.1 verified, output below |
| 1 Resume Analyst + design foundation | ⬜ not started | — | — |
| 2 Case Architect + Planner | ⬜ not started | — | — |
| 3 Interviewer + conduct loop | ⬜ not started | — | — |
| 4 Evaluator + scorecard | ⬜ not started | — | — |
| 5 Coach | ⬜ not started | — | — |
| 6 Orchestration depth | ⬜ not started | — | — |
| 7 Polish & hardening | ⬜ not started | — | — |

## Agent specs & golden cases

Specs are written at the top of the phase that builds each agent, not up front.

| Agent | Spec | Golden cases | Last prompt change |
|---|---|---|---|
| Resume Analyst | ⬜ (Phase 1) | — | — |
| Case Architect | ⬜ (Phase 2) | — | — |
| Planner | ⬜ (Phase 2) | — | — |
| Interviewer | ⬜ (Phase 3) | — | — |
| Evaluator | ⬜ (Phase 4) | — | — |
| Coach | ⬜ (Phase 5) | — | — |

---

## Current phase — story detail

Phase 0 stories are defined in `docs/specs/PHASE-0-SPEC.md`. Nothing started yet.

- [x] 0.1 ~~Repo scaffold, `.env` handling, `requirements.txt`, Vite app, secret-prefix pre-commit hook~~ — done 2026-07-30, all four acceptance boxes verified with output below
- [~] 0.2 NVIDIA smoke test — off-peak re-measure done 2026-07-30, model choice holds. Still need `ChatNVIDIA` structured output 10/10 + streaming   ← NEXT
- [x] 0.3 ~~Confirm build.nvidia.com account model~~ — done 2026-07-29: 40 RPM, no credits
- [x] 0.4a ~~Supabase project + connection verified~~ — done: Singapore, session pooler, Postgres 17.6, `check_db.py` connects
- [ ] 0.4 Supabase project + schema migration
- [ ] 0.5 Postgres checkpointer wired via session pooler, `.setup()` run once
- [ ] 0.6 Two-node graph with `interrupt()` / `Command(resume=...)`
- [ ] 0.7 Interrupt/resume proven across two separate HTTP requests
- [ ] 0.8 Deploy backend to Render, frontend to Netlify, CORS wired, health check green

---

## Last session

**Session 2 — 2026-07-30.** Story 0.1 complete. Orchestrated, with the backend and frontend
scaffolds each built by a delegated agent and every claim re-verified independently before
being recorded here.

### 0.1 acceptance — observed output

`make dev-api` → `GET /health`:

```
HTTP/1.1 200 OK
server: uvicorn
content-type: application/json

{"status":"ok"}
```

`make dev-web` → Vite v8.1.5 ready in 347ms on `http://localhost:5173/`, confirmed serving real
HTML with the HMR client injected, not merely printing "ready".

`config.py` failure modes, each run in a subprocess so `backend/.env` was never edited:

```
two vars missing            exit=1
  ConfigError: Missing required environment variable(s): NVIDIA_MODEL_DEEP, SUPABASE_ANON_KEY.

transaction pooler (6543)   exit=1
  ConfigError: SUPABASE_DB_URL uses port 6543 (the transaction pooler). This breaks LangGraph's
  checkpointer with DuplicatePreparedStatement once connections are reused.

direct connection host      exit=1
  ConfigError: SUPABASE_DB_URL host 'db.someref.supabase.co' is not a Supabase pooler host.
```

`.env.example` and `backend/.env` both cover all 11 vars in `REQUIRED_VARS`.

Pre-commit hook, five cases: fake `nvapi-` blocked · fake `sb_secret_` blocked · real-shaped key
blocked · **live `backend/.env` blocked even when force-added past gitignore** · docs naming the
bare prefixes commit fine.

### Off-peak latency re-measure — model choice holds

Taken 2026-07-30 ~07:30 IST, against the single ~23:00 window everything previously rested on.

| Model | chat latency | structured output |
|---|---|---|
| `nemotron-3-nano-30b-a3b` | 0.4s | VALID |
| `nemotron-3-super-120b-a12b` | 0.4s | VALID |
| `openai/gpt-oss-20b` (backup) | 1.0s | VALID |
| `openai/gpt-oss-120b` | 45s timeout | — |
| `mistral-medium-3.5-128b` | 19.8s | — |
| `google/gemma-4-31b-it` | 26.4s | — |

`nemotron-3-ultra-550b-a55b` now answers in 1.3s and returns valid structured output; it was
`503 ResourceExhausted` on 2026-07-29. Availability moves. Not switching to it — nothing needs it.

### Session 1 — 2026-07-29

Planning, credentials, and de-risking. No application code yet.

Wrote PRD, ARCHITECTURE, CLAUDE.md, PHASE-0-SPEC. Three research agents ran; findings in
`docs/research/`. Installed 13 design skills plus Supabase's two.

Credentials all verified working, not merely present: Supabase recreated in Singapore
(`tnqfqsocoqythakwybsw`) after the first project turned out to be in Sydney, connection proven
against the session pooler, both API keys authenticating.

**The session's significant finding: GLM 5.2 queues ~230s on the free tier and is out.**
Replaced with `nemotron-3-nano-30b-a3b` (fast) and `nemotron-3-super-120b-a12b` (deep), both
3/3 strict structured output at 2–4s. See § Decisions.

Probe scripts kept in `backend/scripts/`: `check_env.py`, `check_db.py`, `probe_latency.py`,
`probe_models.py`, `probe_candidates.py`, `probe_structured.py`.

## Next session — start here

**Story 0.2 — close the structured-output decision gate.** Everything is installed now, so this
is unblocked. Two things, both through `ChatNVIDIA` rather than the raw OpenAI client:

1. `with_structured_output()` returns a valid Pydantic instance **10 consecutive times**. Record
   the pass rate as a number. Below 10/10 makes prompt-validate-retry mandatory in every agent
   rather than defensive, which adds work to every remaining phase — that is Karthik's call, not
   the agent's.
2. Streaming yields more than one incremental chunk.

**Also resolve while there:** structured-output calls measured **11–14s** on 2026-07-30 against
the 2–4s recorded on 2026-07-29. Probably a heavier prompt rather than a regression, since plain
chat on the same models was 0.4s in the same run, but it is unexplained and the Interviewer sits
on the candidate's critical path. The 10-run test gives a real distribution — use it.

**Then 0.4 → 0.5 → 0.6 → 0.7 → 0.8** in spec order.

**Run first (~3 min):** `python backend/scripts/check_env.py`. It now checks all three models and
no longer probes `thinking`.

**Before touching agent code, remember the venv:** `backend/.venv/Scripts/python.exe`, or use the
`make` targets. The global interpreter has different versions of fastapi, pydantic, and openai
and does not have langgraph at all.

**On retesting GLM 5.2 — the bar, so it is not re-litigated each session.**
Retest opportunistically. **Correction 2026-07-30: `probe_candidates.py` does *not* test GLM** —
verified by grep; GLM appears only in `probe_models.py` and `probe_nvidia.py`. The retest policy
below therefore had nothing implementing it. Use `probe_models.py`, or add GLM to
`probe_candidates.py`'s model list. But treat one fast sample as one sample, not as a reversal. The product runs interviews at unpredictable hours, so a model
that is 3s at 09:00 and 230s at 23:00 is unshippable — the 23:00 session is a broken product.

Switch back **only if** GLM is fast across several checks spread through a full day **and**
passes the same 3/3 strict structured-output test Nemotron already passes. Nemotron currently
meets every requirement, so the burden of proof sits with the change.

**Unverified assumption worth closing early:** `nemotron-3-super-120b-a12b` is assumed to have a
1M-token context window, taken from the tech research rather than its model card. The decision to
drop the transcript summarizer depends on it. Confirm from the model card, or measure, before
Phase 5.

---

## Decisions & deviations

Dated log of where reality diverged from the plan. **These entries supersede
`ARCHITECTURE.md` wherever they conflict.**

**2026-07-30 · `openai==1.59.0` was never published. Pin corrected to `1.59.2`.**
PyPI's release train goes `1.58.1 → 1.59.2`; there is no `1.59.0`. `pip install -r
requirements.txt` failed outright on that line. Two things confirmed while fixing it:
`langchain-nvidia-ai-endpoints==1.4.3` declares `Requires-Dist: aiohttp, langchain-core,
requests` and **does not depend on `openai` at all** — it imports and runs fine with openai
absent. So this was a plain bad pin, not the dependency conflict it looked like. Kept the
package because story 0.2's decision gate allows dropping to the raw client for structured
output, and the probe scripts already use it. `pip check` now clean.

**2026-07-30 · GNU Make 4.4.1 installed via winget (`ezwinports.make`).** It was absent, which
blocked two 0.1 acceptance boxes written around `make`. Chosen over rewriting the command
interface because CLAUDE.md, PHASE-0-SPEC, and every future phase gate name `make` targets;
installing costs one command, rewriting costs doc churn in perpetuity. **Make has no deployment
impact** — Render runs `uvicorn` directly and Netlify runs `npm run build`; neither sees a
Makefile. Note for future sessions: winget modifies PATH but the change needs a new shell, so
`make` may appear missing until the terminal restarts. Binary is at
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\ezwinports.make_*\bin\make.exe`.

All six targets verified on Windows. No `SHELL` override was needed — cmd.exe resolves the
forward-slash `.venv/Scripts/python.exe` path fine, which was the anticipated failure.

**2026-07-30 · `check_env.py` had drifted from the decisions in this file, and would have failed
every run.** It still required a single `NVIDIA_MODEL` var (replaced by the three-model split on
2026-07-29) and still probed `thinking: {"type": "disabled"}` (which Nemotron rejects with
`HTTP 400 Unsupported parameter(s)`, also recorded 2026-07-29). Both decisions were written down
correctly and the tooling was never updated to match. Now checks all three models, times each,
and flags any above 10s as contention rather than an env failure.

**The general lesson, worth more than the fix:** DEV-STATE was right and the script was wrong.
Scripts encode decisions too, and they drift silently because nothing re-reads them. When a
decision changes a variable name or an API parameter, grep `backend/scripts/` in the same commit.

**2026-07-30 · CORS "rejects an unlisted origin" needs the right assertion, or `test_api.py`
will encode a false pass.** A simple `GET` with a disallowed `Origin` returns **HTTP 200** with
the `access-control-allow-origin` header *absent* — the browser is what blocks it. Only a
**preflight `OPTIONS`** returns `400 Disallowed CORS origin`. Both observed:

```
GET     Origin: http://evil.example.com   -> 200, no access-control-allow-origin
OPTIONS Origin: http://evil.example.com   -> 400 Bad Request
OPTIONS Origin: http://localhost:5173     -> 200, access-control-allow-origin echoed
```

So the phase-spec test must assert on **preflight status** or on **header absence**, never on a
simple request returning non-200. Asserting the latter would fail against correct code and
invite someone to "fix" working CORS.

**2026-07-30 · Pre-commit hook lives in tracked `.githooks/`, not `.git/hooks/`.**
`core.hooksPath` is set to it, so the hook survives a clone. `.git/hooks/` is not version
controlled, which would have made the guard a matter of whoever set up the machine — the
opposite of the "structural rather than a matter of care" intent in story 0.3.

The hook matches each prefix **followed by 20+ characters of key material**, not the bare
prefix, because DEV-STATE.md, `check_env.py`, and `.env.example` all name `nvapi-` and
`sb_secret_` deliberately and must stay committable. It also filters placeholder forms:
`.env.example` ships `nvapi-xxxxxxxx...`, which is shape-identical to a real key. **Known
trade-off: a real key containing eight consecutive `x` characters would slip through.**

**2026-07-29 · Design skill: v1 governs this product, not v2.** All 13 skills from
`github.com/Leonxlnx/taste-skill` are installed. Note the plan's `--skill "taste-skill"` name
does not exist — skill names differ from directory names in that repo. Installing without
`--skill` takes all 13, which is what we did.

The important finding: **`design-taste-frontend` (v2) explicitly scopes itself out of this
product** in its own §13 — "Dashboards / dense product UI / admin panels… Multi-step forms /
wizards" — and instructs the agent to say so rather than apply it wholesale. But
**`design-taste-frontend-v1` still carries dedicated software-UI rules that v2 dropped** when
it was rewritten toward landing pages: serif banned on dashboards with two named sans pairings,
dashboard card-container hardening gated on density, a mandatory icon library, and mono for all
numbers.

**v1 is therefore the governing skill.** v2 contributes its expanded AI-tells list and the
em-dash ban. Reasoning and dial settings in `ARCHITECTURE.md` §8.

Also checked and rejected: `high-end-visual-design` is Awwwards/agency-tier and prescribes
`py-24`–`py-40` macro-whitespace, floating glass-pill navigation, and eyebrow tags — correct
for a marketing page, absurd for a three-column assessment tool. `minimalist-ui` and
`gpt-taste` are likewise landing-page oriented. `industrial-brutalist-ui` is the only other
one that names dashboards, but its aesthetic contradicts the brief. **`full-output-enforcement`
is not a design skill and is worth applying generally** — it bans `// ...` and "rest of code"
placeholder patterns in generated output.

**2026-07-29 · Dials set: VARIANCE 3 · MOTION 4 · DENSITY 6.** Motion deliberately below 5
to avoid v1's perpetual-micro-interaction mandate, which would fight the anti-jitter
requirement from UI research; the active-agent pulse is the one exception since it carries
real semantic state. Density at 6 keeps card containers legitimate — v1 bans them above 7,
which would contradict the brief. Cards are used for the three column surfaces and chat
messages; agent rows and score rows inside the rails are grouped with hairlines, not nested
cards.

**2026-07-29 · Icon library resolved: Phosphor, not Lucide.** Open question closed. v1 §2
mandates `@phosphor-icons/react` or `@radix-ui/react-icons`; v2 §3.C discourages Lucide;
`high-end-visual-design` §2 bans "standard thick-stroked Lucide" outright. Three independent
agreements. shadcn's Lucide default is swapped at scaffold time in Phase 1 —
`strokeWidth 1.5` standardized globally.

**2026-07-29 · Progress-bar question closed, no change needed.** v2's pre-flight bans
"scoring/progress bars with filled background tracks," but its own §9.F frames this as a
landing-page rule and calls the pattern "dashboard-UI clutter *on a landing page*." We are the
dashboard. The right panel's bars are correct as specified.

**2026-07-29 · Accent colour desaturated.** The plan's accent `#2C5FF6` is roughly 92%
saturation; the skills cap accents at 80%. Changed to `#3A63D0` light / `#6E92E8` dark.

**2026-07-29 · Serif dropped entirely; mono changed to Geist Mono.** An earlier draft paired
Geist with Fraunces for display headings. v2 §4.1 bans Fraunces and Instrument Serif by name
as the two LLM-favourite display serifs, and v1 §7 bans serif on dashboards outright. Mono
switched from JetBrains to **Geist Mono** to match v1's named pairing exactly.

**2026-07-29 · Two design rules constrain agent prompts, not just CSS.** v1 §7 bans
fake-round numbers (`99.99%`, `50%`, `$1M`) and generic names ("John Doe", "Sarah Chan"
register). These reach into the **Case Architect's spec**: generated financials must be
organic (`31.4%` market share, `$4.7M` ARR) and generated company, competitor, and persona
names must not sit in the banned register. The placeholder interviewer name "Maya Chen" used
in the architecture wireframes is itself in that register and must be replaced before Phase 3
ships.

**2026-07-29 · Transcript summarizer dropped from V1.** Interview research recommended one for
context management. GLM 5.2's 1M-token context makes it unnecessary at single-round scale.
Revisit only if multi-round sessions are added.

---

**2026-07-29 · NVIDIA account model resolved: pure rate limit, no credits.** Confirmed from the
account dashboard — **up to 40 RPM**, no credit balance anywhere. The credit-trial model
described in older forum sources is gone. This closes the blocker and, importantly, means
**there is no budget that can be exhausted mid-build**. The only constraint is concurrency,
which the architecture already handles. Story 0.3 can be marked complete without further work.

**2026-07-29 · MODEL CHANGED: GLM 5.2 → Nemotron 3 family. Latency, measured.**

GLM 5.2 is capable and its capability panel is accurate. It is also **unusable on the free
tier**: a trivial 3-token prompt took **~230 seconds**, of which ~228s was queueing and ~2s was
generation. Streaming proved it — HTTP 200 arrived at 229.9s, first token at 231.9s, complete at
232.1s. The model works; you just cannot get to it.

A discriminating test showed this is **per-model demand, not an account throttle**:

| Model | Latency (trivial prompt) |
|---|---|
| `z-ai/glm-5.2` | ~230s queued |
| `meta/llama-3.3-70b-instruct` | >75s queued |
| `openai/gpt-oss-120b` | >45s queued |
| `nvidia/nemotron-3-nano-30b-a3b` | **0.3s** |
| `nvidia/nemotron-3-super-120b-a12b` | **0.4s** |
| `openai/gpt-oss-20b` | **0.3s** |

Structured output, 3 trials per model per mode, `max_tokens 3000`, `temperature 0`:

| Model | `response_format: json_schema` | prompt-only | latency |
|---|---|---|---|
| `nemotron-3-nano-30b-a3b` | **3/3 strict** | 3/3 strict | 2.3–4.2s |
| `nemotron-3-super-120b-a12b` | **3/3 strict** | 3/3 strict | 1.7–4.3s |
| `openai/gpt-oss-20b` | 3/3 strict | 3/3 strict | ~4.0s |
| `llama-3.3-nemotron-super-49b-v1.5` | 3/3 strict | 3/3 strict | 23–46s (too slow) |

**Decision: `nemotron-3-nano-30b-a3b` for the Interviewer, `nemotron-3-super-120b-a12b` for
everything else, `openai/gpt-oss-20b` as fallback.** Structured output is no longer a risk —
strict `json_schema` was 3/3 on every fast candidate. Prompt-validate-retry stays as defence in
depth but is not load-bearing.

**Worth naming plainly: this is what the original tech research recommended, and I overrode it.**
The researcher proposed the Nemotron 3 family; I switched to GLM 5.2 on the strength of its
documented 1M context and explicit structured-output support. That reasoning was sound on
capability and wrong on the dimension neither of us had data for — how heavily contended a
popular third-party model is on NVIDIA's free tier. Capability was documented; provisioning had
to be measured.

**2026-07-29 · The `thinking` parameter is GLM-specific, not portable.** Nemotron 3 rejects it
with `HTTP 400 Validation: Unsupported parameter(s): 'thinking'`. The latency-vs-quality lever
designed into the architecture therefore no longer exists as a parameter. Replaced by **model
choice** — nano for latency-critical turns, super for quality-critical ones. Arguably cleaner,
since it is one dimension instead of two.

**2026-07-29 · `/v1/models` lists models the account cannot use.** 102 returned, but
`nvidia/llama-3.1-nemotron-70b-instruct` and `moonshotai/kimi-k2.6` return `404 Function not
found`, and `deepseek-ai/deepseek-v4-flash` / `nemotron-3-ultra-550b-a55b` return
`503 ResourceExhausted`. Never treat catalog presence as availability — issue a real completion.

**2026-07-29 · GLM 5.2 capabilities confirmed from the official model page.**
[build.nvidia.com/z-ai/glm-5.2](https://build.nvidia.com/z-ai/glm-5.2) Specifications and
Capabilities panels state: Provider Z.ai · Context Length **1M** · Parameters **753B** ·
Function Calling **Supported** · Structured Output **Supported** · Reasoning **Supported** ·
Text in, text out.

**Structured Output being explicitly listed is the significant one.** It was the single
unresolved risk in the tech research — my researcher could not confirm whether `guided_json`
worked on the free hosted endpoint or only on self-hosted NIM containers. It is now confirmed
from the vendor's own capability panel. The prompt-validate-retry fallback stays in the
architecture as defence in depth, but it is no longer a load-bearing assumption. Story 0.2
still measures the actual pass rate, since "supported" and "reliable ten times out of ten"
are different claims.

**2026-07-29 · NVIDIA key exposed; keeping it — deliberate decision, do not re-flag.**
The key was captured in a screenshot and remains in use. Karthik has decided not to rotate it.
Risk is bounded: the free tier is rate-limited at 40 RPM with no credit balance, so worst case
is contention, not cost. `backend/.env` is gitignored. **Future sessions: this is settled, do
not raise it again.**

Still worth doing in Phase 0 story 0.1: a pre-commit hook blocking the `nvapi-` and `sb_secret_`
prefixes. That guards the commit path regardless of this particular key's status.

**2026-07-29 · Supabase project recreated in Singapore; Render must deploy to Singapore.**
The first project (`naiwpcveuouubperqtet`) was created in **Sydney, `ap-southeast-2`** — determined
not from the dashboard but from the project's own IPv6 allocation: `db.<ref>.supabase.co`
resolves to `2406:da1c:10e4:...`, and AWS's published `ip-ranges.json` assigns `2406:da1c::/35`
to `ap-southeast-2`.

Render's free tier does not offer Sydney (Oregon, Ohio, Virginia, Frankfurt, Singapore only), so
backend and database would have sat on different continents. That interacts badly with this
architecture specifically: **LangGraph checkpoints after every node**, so one candidate turn is
roughly four checkpoint writes plus app-table writes — call it eight round trips. At ~100ms
Singapore↔Sydney that is close to a second of added latency per turn, permanently.

The decisive argument was asymmetry of cost, not raw milliseconds: the schema did not exist yet,
so recreating was free. After story 0.4 creates six tables plus LangGraph's checkpoint tables, a
region change becomes a real migration.

**Consequence for Phase 0 story 0.8: Render service region must be Singapore.** Not the default.

**New project: `tnqfqsocoqythakwybsw`, Singapore, verified.** Region confirmed the same way rather
than trusting the dropdown: `db.tnqfqsocoqythakwybsw.supabase.co` → `2406:da18:1691:a201:...`, and
AWS assigns `2406:da18::/35` to `ap-southeast-1`. Both `aws-0-` and `aws-1-` Singapore pooler hosts
resolve and accept TCP on 5432. Old Sydney project retained until the new one is proven, then
deleted (free tier allows two).

**2026-07-29 · Direct connection IPv6-only — now verified, not assumed.**
`db.naiwpcveuouubperqtet.supabase.co` returned an AAAA record and **no A record at all**. The
architecture's claim that Render's IPv4-only free tier cannot reach Supabase's direct connection
is measured fact. Session pooler remains mandatory. Both `aws-0-` and `aws-1-` pooler hosts
resolve and accept TCP on 5432; which one a project uses is not predictable from the ref, so if
auth fails on `aws-0-`, try `aws-1-` before assuming the password is wrong.

**2026-07-29 · Second credential exposure — database password.** The first database password was
posted in plaintext in chat. Reset as part of the project recreation. Separately it contained an
`@`, which breaks Postgres URL parsing and would have needed percent-encoding. Standing rule:
database passwords are letters and digits only.

**2026-07-29 · Supabase official agent skills installed.** `npx skills add supabase/agent-skills`
→ `supabase` and `supabase-postgres-best-practices`. Note the `supabase` skill scores **Medium**
on Snyk (the Postgres one is Low); skills run with full agent permissions, so worth knowing.

**2026-07-29 · Testing convention added, three tiers.** The phase spec originally carried only
acceptance criteria, with no test layer defined for non-agent work. Now: (1) automated tests in
`backend/tests/` and `frontend/src/**/*.test.ts`, named in the phase spec, with assertions in
code; (2) golden cases as fixtures, defined in agent specs, gating every prompt change; (3) a
**Handoff** section ending each phase spec, splitting "verified by me, with evidence" from
"needs your eyes." Rule recorded in `CLAUDE.md`: a phase is handed over with observed output
pasted into this file, or it is not handed over. "Compiles" and "tests should pass" are not
evidence.

---

## Blockers & open questions

**`reasoning_effort` enum unknown.** Only `"max"` appears in any NVIDIA or Z.ai example found.
The full set of valid values is undocumented. Probe empirically in story 0.2 — the
architecture assumes a `"high"` level exists for the Evaluator. **This is now the only
remaining unknown from the LLM side.**

~~NVIDIA account model~~ — resolved 2026-07-29 from the account dashboard. See Decisions.

**Structured-output latency, 11–14s vs the 2–4s on record.** Measured 2026-07-30 while plain
chat on the same models was 0.4s in the same run. Most likely a heavier probe prompt rather than
a regression, but it is unexplained, and the Interviewer runs a structured call every turn while
a candidate waits. Story 0.2's 10-run `ChatNVIDIA` test resolves it with a distribution.

**`make test-web` has nothing to run.** The frontend has no `test` script and vitest is not
installed — correct for Phase 0, which has no frontend tests, but `make test` will fail on the
`test-web` leg until Phase 1 adds vitest. Do not read that failure as a broken scaffold.

**Interviewer persona name needs replacing.** "Maya Chen" appears throughout the architecture
wireframes as a placeholder and sits in the exact register v1 §7 bans ("John Doe", "Sarah
Chan"). Needs a real choice before Phase 3 ships.

~~Icon library conflict~~ — resolved 2026-07-29, Phosphor. See Decisions.
~~Progress-bar tension~~ — resolved 2026-07-29, no change needed. See Decisions.

---

## Environment notes

Populated during Phase 0 as things are actually verified.

**Toolchain, observed 2026-07-30:** Python 3.12.10 · Node 26.1.0 · npm 11.13.0 · git 2.54.0 ·
GNU Make 4.4.1 (installed this session, see Decisions).

**Backend venv at `backend/.venv`** — Python 3.12.10. The global interpreter has different
versions of fastapi/pydantic/openai and **no langgraph at all**; always use the venv or a `make`
target. Installed and `pip check` clean:

```
fastapi 0.135.1 · pydantic 2.10.4 · langgraph 1.2.9
langgraph-checkpoint-postgres 3.1.0 · langchain-nvidia-ai-endpoints 1.4.3
psycopg 3.2.3 · psycopg-pool 3.3.1 · openai 1.59.2
pytest 8.3.4 · pytest-asyncio 0.25.0
```

**Frontend:** Vite 8.1.5 · React 19.2.7 · **Tailwind v4.3.3 via the `@tailwindcss/vite` plugin**
— v4 style, so there is no `tailwind.config.js` and no `@tailwind` directives; `src/index.css`
opens with `@import "tailwindcss";`. Do not add v3-style config, the two do not mix. Tailwind was
proven to actually compile, not merely install, by grepping the built CSS for emitted rules. No
`lucide-react` anywhere, per the Phosphor decision.

**Supabase connection: session pooler, port 5432 — verified working 2026-07-30.**
`aws-0-ap-southeast-1.pooler.supabase.com:5432`, PostgreSQL 17.6, 0 public tables (correct
before story 0.4). `check_db.py` connects clean.

- `checkpointer.setup()` to run via `scripts/init_db.py`, once, never on app startup
- The transaction-pooler `DuplicatePreparedStatement` error text is **still not observed** —
  story 0.5 requires deliberately triggering it on port 6543 and recording it here. `config.py`
  currently rejects 6543 before a connection is attempted, so that guard must be bypassed to
  produce the real error.
- All 13 skills installed at `.agents/skills/` (symlinked for Claude Code).
  **Governing skill for this product: `design-taste-frontend-v1`.** See Decisions.
- `stitch-design-taste` independently corroborates the v1 dashboard rules — "Serif is always
  BANNED in dashboards or software UIs" and "Dashboard Constraint: use Sans-Serif pairings
  exclusively (`Geist` + `Geist Mono` or `Satoshi` + `JetBrains Mono`)". It also generates a
  semantic `DESIGN.md` for agents to follow. **Worth considering in Phase 1** as the artifact
  that encodes our tokens, rather than hand-writing one.

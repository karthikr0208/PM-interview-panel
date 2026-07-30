# Research: Tech Stack for Multi-Agent AI "PM Interview Simulator"

Conducted 2026-07-29 across 30+ official and primary sources. Source for the LangGraph,
Supabase, Render, and Netlify decisions in `docs/ARCHITECTURE.md`.

> **Superseded in one place:** this research recommended the Nemotron 3 family and flagged
> structured output on NVIDIA's free hosted endpoint as an unresolved risk. The project uses
> **`z-ai/glm-5.2`** instead, which documents tool calling and structured JSON explicitly and
> carries a 1M-token context window. Everything else here stands. See `docs/DEV-STATE.md`.

---

## Versions found (pin these)

| Package | Version | Source |
|---|---|---|
| `langgraph` | 1.2.9 (LangGraph reached 1.0 on 2025-10-22; supports Python 3.10–3.14) | [LangChain blog](https://www.langchain.com/blog/langchain-langgraph-1dot0), [PyPI](https://pypi.org/project/langgraph/) |
| `langchain-nvidia-ai-endpoints` | 1.4.3 (2026-07-02) | [PyPI](https://pypi.org/project/langchain-nvidia-ai-endpoints/) |
| `langgraph-checkpoint-postgres` | 3.1.0 (2026-05-12) | [PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) |
| FastAPI native SSE (`fastapi.sse.EventSourceResponse`) | shipped 0.135.1 (2026-03-01) | [FastAPI PR #15030](https://github.com/fastapi/fastapi/pull/15030), [docs](https://fastapi.tiangolo.com/tutorial/server-sent-events/) |
| NVIDIA NIM (self-hosted) structured-generation docs | 1.10.0 / 1.14.0 | [docs.nvidia.com/nim](https://docs.nvidia.com/nim/large-language-models/1.14.0/structured-generation.html) |

**This is the v1.x LangGraph API throughout** (StateGraph, `interrupt()`, checkpointer interface, `add_messages` reducer are all stable v1.x surface, not the old pre-1.0 `.set_entry_point()`-style API).

---

## A. NVIDIA LLM access (build.nvidia.com / NIM)

**Free tier — CONFLICTING SOURCES, flagged explicitly:**
- Older/legacy model (still shown in some docs & the NVIDIA forum thread I fetched): sign up → 1,000 free credits; a business email + 90-day AI Enterprise trial unlocks 4,000 more (5,000 total). What happens at zero: self-host the NIM container yourself (free for dev/test under the Developer Program) or move to a paid serverless option (e.g., NIM on Hugging Face pay-as-you-go). [NVIDIA Developer Forum](https://forums.developer.nvidia.com/t/api-credits-for-build-nvidia-com/306633/2)
- Newer community reporting (2026) says the credit system was phased out in favor of a pure **rate limit**: **40 requests/minute** per API key by default, with an application process for a **200 RPM** upgrade, and NVIDIA staff describing the limit as "dependent on model, use-case, and current overall traffic." [Forum: RPM increase request](https://forums.developer.nvidia.com/t/request-for-nvidia-build-api-rate-limit-increase-40-rpm-200-rpm/377433), [Forum FAQ](https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317)
- **I could NOT fully reconcile these two models from official docs alone** (build.nvidia.com's own key-management page returned a connection error on fetch). **Action item before building: log into build.nvidia.com yourself and check the API Keys / usage dashboard — it will show you definitively whether you're credit-metered or rate-limited.** Either way, budget for **40 RPM as your hard ceiling** for the free path; this is corroborated across every 2026 source found and is a real constraint for a multi-agent app that may fire several LLM calls per candidate turn (interviewer + evaluator + orchestrator).
- No credit-card required to get a key. Not expiring on a calendar basis (unlike Render's Postgres, see below) — governed by rate limit / credit exhaustion, not time.

**OpenAI compatibility:** Yes. Base URL: `https://integrate.api.nvidia.com/v1`, endpoint `POST /v1/chat/completions`. Auth header: standard OpenAI-style `Authorization: Bearer $NVIDIA_API_KEY`. [docs.api.nvidia.com](https://docs.api.nvidia.com/nim/reference/llm-apis)

**Model catalog (verified current, July 2026):**
- **Nemotron 3 family (newest, launched H1 2026)** — hybrid Mamba-Transformer MoE, built for agentic/multi-agent reasoning:
  - **Nemotron 3 Nano** — small, cheap, low-latency; 128K context. → best for **fast conversational interviewer turns**.
  - **Nemotron 3 Super** — ~120B total / ~12B active params, **native 1M-token context window** (Mamba-2 layers give linear-time scaling). → best for **long-context evaluation/coaching** (e.g., feeding an entire transcript + rubric).
  - **Nemotron 3 Ultra** — ~500B total / ~50B active, 128K context, highest accuracy for complex reasoning. → best for **final scoring/coaching report** if you want max quality and can tolerate latency + rate-limit cost.
  - Source: [NVIDIA Nemotron 3 Super technical report](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Super-Technical-Report.pdf), [DataCamp summary](https://www.datacamp.com/blog/nvidia-nemotron-3), [NVIDIA Newsroom](https://nvidianews.nvidia.com/news/nvidia-debuts-nemotron-3-family-of-open-models)
- **Llama 3.1/3.3 family** (70B, 8B) and **Llama-3.3-Nemotron-Super-49B** — mature, well-documented tool-calling support, good default if Nemotron 3 has rougher LangChain-integration edges since it's brand new.
- Also present in catalog: **Mistral/Mixtral (8x7B, 8x22B), Qwen 2.5-72B, DeepSeek, GLM 4.7/5.1, Kimi K2, Phi-4-mini, Gemma** — broad but not all verified for tool-calling (see below).

**Tool calling support — verified as genuinely inconsistent across the catalog, this matters a lot:**
- Confirmed **tool-calling capable**: Llama 3.1 70B/405B, Llama 3.2, Llama 3.3, Llama-Nemotron Nano/Super/Ultra (with "detailed thinking" **off** — reasoning mode can interfere with clean tool-call emission), Mistral/Mixtral, Qwen 2.5-72B, GLM 4.7/5.1, Kimi K2.
- Smaller (<7B) and vision-only models frequently lack or only partially implement tool calling.
- **Practical rule for this app: check each model's card on build.nvidia.com for the "Tools" capability badge before wiring it into a LangGraph node that uses `bind_tools`/`with_structured_output` via tool-calling — don't assume.** [NVIDIA dev blog on Nemotron reasoning + tools](https://developer.nvidia.com/blog/build-enterprise-ai-agents-with-advanced-open-nvidia-llama-nemotron-reasoning-models/)

**`langchain-nvidia-ai-endpoints` (v1.4.3):** MIT-licensed, LangChain-team-maintained, requires Python ≥3.10. `ChatNVIDIA` supports sync/async `.invoke`/`.ainvoke`, `.stream`/`.astream`, `.batch`/`.abatch`, `bind_tools`, and `with_structured_output`. You can filter for tool-capable models programmatically:
```python
tool_models = [m for m in ChatNVIDIA.get_available_models() if m.supports_tools]
```
[docs.langchain.com integration page](https://docs.langchain.com/oss/python/integrations/chat/nvidia_ai_endpoints)

**Structured JSON output — two paths, verified:**
1. **LangChain-level:** `llm.with_structured_output(MyPydanticModel)` — works if the underlying model supports tool calling (LangChain implements structured output via a forced tool call under the hood for most providers). Documented as supported (✅) in the ChatNVIDIA integration table, but **no worked code example found on the LangChain side** — treat as "should work, verify empirically first."
2. **NIM-native guided decoding (`guided_json`):** documented clearly for **self-hosted NIM containers** via `extra_body={"guided_json": <json_schema>}` on the OpenAI client, backed by the **xgrammar** grammar engine (falls back to slower **outlines** for schemas xgrammar can't parse — flagged by NVIDIA as a first-inference latency issue). [docs.nvidia.com structured generation](https://docs.nvidia.com/nim/large-language-models/1.14.0/structured-generation.html)
   - **Could NOT verify** that `guided_json` extra_body is honored on the **hosted** `integrate.api.nvidia.com` endpoint (as opposed to a self-hosted NIM container) — the docs I could reach describe self-hosted NIM only. Third-party integration docs (LiteLLM, Promptfoo) confirm the hosted endpoint is fully OpenAI-compatible and passes through `extra_body`, but nobody explicitly confirms `guided_json` is enabled server-side for the free hosted models.
   - **Recommendation: build with a fallback-safe pattern regardless** — try `with_structured_output`/`guided_json`, but always wrap in prompt-plus-parse-plus-retry (Pydantic validation → on failure, re-prompt with the validation error appended) since free-tier hosted models are the least-guaranteed part of this stack.

**Embeddings on free tier:** Yes — NVIDIA NeMo Retriever embedding models are available through the same catalog, e.g. `NV-Embed-QA` / `nvidia/nv-embedqa-e5-v5`. These require an `input_type` of `"query"` or `"passage"`; since the OpenAI-style endpoint doesn't accept custom params directly, NVIDIA documents a `-query`/`-passage` model-name suffix workaround. Same 40 RPM ceiling applies (shared per API key across all models, not per-model). [docs.nvidia.com NeMo Retriever](https://docs.nvidia.com/nim/nemo-retriever/text-embedding/2.2.0/use-the-api-openai.html) — relevant only if you build resume/question-bank RAG; likely unnecessary for MVP (resume context is small enough to put directly in-context).

**Latency & retry strategy:** Not independently benchmarked (no official NVIDIA SLA found for the free tier — by design, since it's an unmetered "best effort" trial product). Practical implication for a production-shaped app: **treat every NVIDIA call as fallible.** Recommended pattern: exponential backoff with jitter on 429s, a short per-call timeout (~20–30s), and — given LangGraph's checkpointer already persists state at each node boundary — **let a failed node be safely retried from its last checkpoint** rather than building custom retry logic inside the node. LangGraph 1.2 added native per-node timeouts and post-retry error handlers, which fits this exactly (see gotcha #2 below).

---

## B. LangGraph fundamentals (taught for a first-time user)

### Core concepts

A **StateGraph** is a graph builder around a **state schema** — a `TypedDict` (or Pydantic model) describing every field nodes can read/write. Each node is a plain Python function `(state) -> dict` returning a *partial* update; LangGraph merges it into state using **reducers**. Without a reducer, a field is just overwritten; `Annotated[X, reducer_fn]` tells LangGraph how to combine old + new (e.g., `operator.add` to append, or `add_messages` — LangGraph's purpose-built reducer for chat history that appends and de-duplicates by message ID).

```python
# https://docs.langchain.com/oss/python/langgraph/graph-api
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class InterviewState(TypedDict):
    messages: Annotated[list, add_messages]   # chat history, auto-merged
    candidate_level: str
    current_question_idx: int

def ask_question(state: InterviewState) -> dict:
    return {"messages": [{"role": "assistant", "content": "Tell me about a time you..."}]}

def route_after_question(state: InterviewState) -> str:
    return "wait_for_answer"  # name of the next node, chosen at runtime

builder = StateGraph(InterviewState)
builder.add_node("ask_question", ask_question)
builder.add_edge(START, "ask_question")
builder.add_conditional_edges("ask_question", route_after_question)
builder.add_edge("ask_question", END)

graph = builder.compile()   # MUST compile before invoke/stream — this trips up every beginner
```

### Checkpointers / persistence — this is what makes multi-turn interviews possible

- `MemorySaver` (`langgraph.checkpoint.memory`) — in-process RAM only. Fine for local dev; **useless in production** because Render's free web service has an ephemeral filesystem and can restart/spin-down between requests, wiping memory.
- **`AsyncPostgresSaver`** (`langgraph.checkpoint.postgres.aio`, package `langgraph-checkpoint-postgres` v3.1.0) — the production choice, backed by Supabase Postgres:

```python
# https://pypi.org/project/langgraph-checkpoint-postgres/
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

DB_URI = "postgresql://postgres.xxxx:PASSWORD@aws-REGION.pooler.supabase.com:5432/postgres"

async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    await checkpointer.setup()          # one-time: creates checkpoint tables + indexes
    graph = builder.compile(checkpointer=checkpointer)
```

  Call `.setup()` once (e.g., in a migration script or app startup, guarded so it only runs once) — it creates LangGraph's own tables (checkpoints, writes, blobs) in the `public` schema by default. **These are separate tables from your app tables (e.g. `interview_sessions`, `candidates`) — no naming conflict as long as you don't also have tables literally named `checkpoints`/`checkpoint_writes`/etc.** Sharing one Supabase Postgres instance for both app data and LangGraph checkpoints is standard practice and fine on the free tier (500MB DB cap total, shared across both uses).

- **The pgBouncer / Supabase pooler gotcha (real, verified via GitHub issue and Supabase forum, and directly relevant to you):**
  - Supabase Postgres sits behind **Supavisor**, exposed as three connection strings: **Direct** (`db.<ref>.supabase.co:5432`), **Session pooler** (`aws-<region>.pooler.supabase.com:5432`), **Transaction pooler** (`...pooler.supabase.com:6543`).
  - Supabase's own docs recommend **Direct** for persistent backend servers — **but Supabase's direct connection endpoint is IPv6-only** unless you pay for the IPv4 add-on, and **Render's free tier does not support outbound IPv6**. So direct connection will simply fail to resolve/connect from Render. [Supabase IPv4/IPv6 troubleshooting](https://supabase.com/docs/guides/troubleshooting/supabase--your-network-ipv4-and-ipv6-compatibility-cHe3BP), [Render Discourse thread confirming this exact failure](https://render.discourse.group/t/issues-connecting-render-to-supabase-after-ipv6-transition/24156)
  - **Transaction-mode pooler (port 6543)** does IPv4-resolve fine, but recycles the underlying Postgres connection between transactions — this breaks **prepared statements**, which `psycopg`/`AsyncPostgresSaver` uses by default, producing the well-documented error `psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists`. [LangGraph issue #2755](https://github.com/langchain-ai/langgraph/issues/2755)
  - **Recommended fix, and my recommendation for this app:** use the **Session pooler (port 5432, IPv4-resolvable)** — it hands your process one dedicated backend connection for the life of the session, so prepared statements behave like a normal direct connection, while still resolving over IPv4 so it works from Render. If you ever do need to use the transaction pooler (e.g., for connection-count reasons at higher scale), disable prepared statements explicitly:
    ```python
    connection_kwargs = {"autocommit": True, "prepare_threshold": 0}
    ```
    [Session vs transaction pooler docs](https://supabase.com/docs/guides/database/connecting-to-postgres), [prepare_threshold fix](https://github.com/langchain-ai/langgraph/issues/2755)

- **`thread_id` / config semantics:** every `.invoke()`/`.stream()` call takes `config={"configurable": {"thread_id": "..."}}`. The checkpointer keys all state to that thread_id. To resume a candidate's interview, **use the interview session's own UUID (e.g., the Supabase `interview_sessions.id`) as `thread_id`** — this is literally how a stateless HTTP backend "remembers" a multi-turn interview: every request just needs to know the thread_id (store it in the frontend, a cookie, or look it up from the logged-in user + active session row), and the graph reconstructs full state from Postgres on each call. Keep `thread_id` under 255 chars (Postgres column limit).

### Human-in-the-loop: `interrupt()` + `Command(resume=...)` — the core mechanic of this app

This is what lets the graph "ask a question, then wait — possibly for minutes or hours — for the candidate's chat reply, across separate HTTP requests."

```python
# https://docs.langchain.com/oss/python/langgraph/interrupts
from langgraph.types import interrupt, Command

def wait_for_candidate_answer(state: InterviewState) -> dict:
    answer = interrupt({"prompt": "Waiting for candidate's answer"})
    # ^ execution PAUSES here; graph state is checkpointed to Postgres; the function
    #   call itself does not return yet — the whole node exits and control returns
    #   to your FastAPI handler.
    return {"messages": [{"role": "user", "content": answer}]}
```

Two-request pattern for a stateless FastAPI backend:

```python
# Request 1 — start or advance the interview up to the next question
config = {"configurable": {"thread_id": session_id}}
result = await graph.ainvoke(initial_input_or_None, config=config)
# result will contain an `__interrupt__` key when the graph is paused;
# send the interrupt's payload (the question) to the frontend and return.

# Request 2 — candidate replies in the chat UI; a NEW HTTP request comes in
config = {"configurable": {"thread_id": session_id}}   # SAME thread_id
result = await graph.ainvoke(Command(resume=candidate_answer_text), config=config)
# LangGraph loads the checkpoint for this thread_id from Postgres, re-enters
# the paused node, and `interrupt(...)` now RETURNS candidate_answer_text.
```

**Critical, easy-to-miss semantics (verified against docs):**
- On resume, **the entire node re-runs from its top** — LangGraph does not resume mid-function from the exact `interrupt()` line. Any code in that node *before* the `interrupt()` call re-executes too. **This means code before `interrupt()` inside a node must be idempotent** (don't do something like "increment a counter" or "call an LLM" before the `interrupt()` call inside the same node — do that in a separate upstream node instead).
- Don't wrap `interrupt()` in try/except.
- Only pass JSON-serializable values into and out of `interrupt()`.
- Because a Postgres checkpointer is attached, this all works fine across separate stateless HTTP requests / separate Render dyno instances — the *only* shared state is the Postgres row for that `thread_id`, which is exactly the stateless-backend model you need.

### Streaming — two APIs currently documented; use the simpler one and know the newer one exists

LangGraph currently documents **two separate streaming systems** — worth flagging explicitly since it's easy for a beginner to conflate them:

1. **The classic `stream()`/`astream(stream_mode=...)` API** (mature, has existed across LangGraph's whole history):
```python
# https://docs.langchain.com/oss/python/langgraph/streaming
async for chunk in graph.astream(
    {"topic": "cats"},
    stream_mode=["updates", "messages", "custom"],
    config=config,
):
    # chunk shape depends on how many stream_modes you passed;
    # with multiple modes each chunk is (mode_name, payload)
    ...
```
   - `values`: full state snapshot after each node.
   - `updates`: only the diff each node returned — good for a live "orchestrator dashboard" (which node just ran, what it changed).
   - `messages`: token-by-token LLM output — good for the candidate-facing chat stream.
   - `custom`: anything you push yourself via `get_stream_writer()` inside a node — the cleanest way to emit structured "Agent X is now doing Y" progress events for the dashboard, independent of the chat token stream.

2. **A newer, typed "event streaming" API** (`stream_events()`/`astream_events(..., version="v3")`) that layers transformers/typed projections on top of the same underlying Pregel engine events. **I could not pin down exactly which LangGraph version introduced this** (search results were inconsistent — one summarizer implied "v1.2+" but I couldn't confirm this against a changelog) — **flag as unverified**, and given it's clearly the more complex/newer surface (custom `StreamTransformer` classes, `version="v1"/"v2"/"v3"` literal), **I recommend starting with the classic `stream_mode=[...]` API for a first LangGraph project** and only reaching for event-streaming transformers if you hit a real limitation.

- Streaming to the browser: iterate the `astream(...)` async generator inside a FastAPI SSE endpoint and `yield` each chunk as an SSE `data:` line (see Section E).

### Subgraphs

A **subgraph** is a compiled `StateGraph` used as a node inside a parent graph — either sharing the parent's state schema directly, or with an explicit state-transformation function at the boundary if the schemas differ. **Use a subgraph when a chunk of the workflow has its own meaningful multi-step state machine you'd want to test/reason about in isolation** (e.g., "conduct one interview question: ask → wait → maybe follow up → advance" is a great subgraph candidate, since it's really its own small loop). **Use a plain node/function when it's a single logical step** (e.g., "score this one answer" is one LLM call — a function, not a subgraph). I was not able to fetch the current subgraphs doc page directly (404/timeout on both attempts) — **this section is based on well-established LangGraph subgraph semantics from search-result summaries, not a directly verified doc fetch; re-verify the exact `add_node(subgraph_compiled_graph)` call signature before writing code.**

### Common beginner pitfalls (synthesized from the above)

1. Forgetting `.compile()` — the builder object itself has no `.invoke()`/`.stream()`.
2. Putting non-idempotent side effects before `interrupt()` in the same node (re-runs on resume).
3. Reusing `MemorySaver` in what you think is a "test of production behavior" — it will hide the entire class of stateless-HTTP-request bugs until you deploy.
4. Using the wrong Supabase connection string (direct/IPv6 or transaction-pooler/prepared-statements) — covered above.
5. Not calling `checkpointer.setup()` before first use — tables won't exist, first checkpoint write fails.
6. Confusing `stream_mode="values"` (full snapshot, larger payloads) with `"updates"` (diffs only) and shipping the wrong one to a bandwidth-conscious browser client.

### LangSmith / tracing

LangSmith (LangChain's first-party tracing product) free tier: **5,000 traces/month**. Free, open-source alternative with a materially larger free allotment: **Langfuse** (MIT-licensed core, self-hostable, ~50,000 free observations/month on their hosted free tier, or unlimited if you self-host it yourself — though self-hosting Langfuse is itself another free-tier-hosting problem, so for this project LangSmith's 5K/month is probably simpler to start with and likely sufficient for personal development/demo use). [Langfuse vs LangSmith comparison](https://langfuse.com/resources/engineering/langsmith-alternative) — **not needed for the app to function; it's purely a dev-time observability nice-to-have.**

---

## C. Architecture for this app

**Recommended graph topology (each is a node; steps in `[]` are subgraphs):**

```
START
  → ingest_resume            (parse PDF/DOCX → structured candidate profile)
  → level_candidate          (LLM: infer seniority/level from resume + role)
  → plan_interview            (LLM: generate ordered question plan for the level)
  → [conduct_interview_loop]  (SUBGRAPH, loops per question):
        ask_question
        → wait_for_candidate      (interrupt() — pauses here across HTTP requests)
        → decide_followup_or_advance   (conditional edge: LLM decides "probe deeper" vs "next question")
        → (loops back to ask_question OR exits subgraph when question plan exhausted)
  → evaluate_each_answer      (see below: inline vs background)
  → aggregate_final_score
  → generate_coaching_report  (long-context LLM call — good fit for Nemotron 3 Super's 1M context: pass the WHOLE transcript + rubric)
END
```

- `conduct_interview_loop` is a strong subgraph candidate: it's a genuine nested state machine (ask/wait/branch/repeat) with its own natural boundary, and isolating it means you can unit-test "does this one Q&A cycle behave correctly" without exercising resume parsing or scoring.
- The `interrupt()` for "wait for candidate" sits *inside* the subgraph; that's fine — interrupts propagate correctly across subgraph boundaries in LangGraph's checkpointing model as long as the same `thread_id`/checkpointer flows through.

**Per-answer evaluation: inline (blocking) — recommended, with reasoning:**
- Running evaluation as its own graph node in the same synchronous request/response cycle as the "advance to next question" decision keeps the whole system inside one checkpointed graph, one Postgres row, one mental model — no separate job queue, no separate worker process (which the free tier makes hard anyway — see Render section).
- Cost/latency reasoning: each candidate answer is short (a few hundred tokens); one extra LLM call for evaluation, even at Nemotron 3 Nano/fast-model latency, adds maybe 1–3 seconds to the "submit answer → see next question" round trip — acceptable for an interview-pacing UX (candidates are typing/thinking between turns anyway) and far simpler than standing up async background workers, which **Render's free tier does not support for background workers at all** (see below) — so "async" evaluation would really mean "fire-and-forget inside the same process," which is fragile on a spin-down-prone free dyno (a spin-down mid-flight would silently drop the evaluation). **Inline avoids that failure mode entirely: it's checkpointed like everything else, so even a mid-evaluation crash/restart resumes cleanly from the last checkpoint.**
- Only reconsider this if evaluation quality demands a much larger/slower model that makes per-turn latency unacceptable — in that case, still keep it inside the graph (as a slow node) rather than reaching for a separate task queue you can't run for free.

**Backend framework: FastAPI — recommended, self-hosted graph (not LangGraph Platform/Server).**
- **LangGraph Server/Platform** (the managed deployment product) adds a task queue (Redis), independently-scalable API/worker processes, and run-durability across worker restarts — genuinely valuable at scale, but it assumes infrastructure (Redis + multiple processes) you don't get for free on Render, and it's overkill for a single-process interview app. **Self-hosting the compiled graph directly inside FastAPI is the correct free-tier path**: you already have a Postgres checkpointer doing the durability LangGraph Server would otherwise provide; you just don't get the separate queue/worker scaling. Documentation describes LangGraph's own "single host" deployment mode as explicitly meant for "development and low-traffic use cases" — that's this app. [docs.langchain.com langgraph-server](https://docs.langchain.com/langgraph-platform/langgraph-server) (fetch was partial/summarized — re-verify deployment-mode terminology directly before finalizing).
- FastAPI exposes the graph over HTTP by: (a) a POST endpoint that takes `{thread_id, message}`, calls `graph.ainvoke(Command(resume=message) or input, config)`, and returns either the next interrupt payload or final state; (b) optionally, an SSE/streaming variant of the same endpoint that iterates `graph.astream(...)` and forwards chunks live (see Section F).
- **Render free tier spins down after 15 minutes of inactivity, with a ~30–60s cold start on the next request.** [Render free docs](https://render.com/docs/free) For a chat-paced interview (candidate reads a question, thinks, types an answer — easily >15 min of backend inactivity between some turns) **this WILL cause a cold start mid-interview.** Mitigations:
  1. This is actually **less bad than it sounds precisely because of the checkpointer + interrupt architecture**: since every HTTP request is stateless and resumes from Postgres, a cold start just means "the next request takes an extra 30–60s," not "the interview is lost." This is a strong argument for the interrupt/checkpoint design beyond just being "the LangGraph way" — it's what makes Render's free-tier spin-down survivable at all.
  2. Still, 30–60s of dead air after the candidate submits an answer is a bad UX moment. A cheap mitigation: a client-side "keep-alive" ping (e.g., every 10 minutes while the interview tab is open) to a lightweight `/health` endpoint, to prevent spin-down *while the candidate is actively in a session*. This won't help between sessions but helps mid-interview.
  3. Show a "waking up the interviewer…" loading state in the UI rather than a silent hang, since 30–60s with no feedback reads as broken.

---

## D. Supabase

**Free tier limits (verified from official pricing page):**
- 500 MB database, 1 GB file storage, 5 GB egress + 5 GB cached egress/month, 50,000 monthly active users (auth), unlimited API requests, limit of **2 active projects**.
- **Pause policy confirmed current: "Free projects are paused after 1 week of inactivity."** [supabase.com/pricing](https://supabase.com/pricing) — for a portfolio/demo project this matters: if nobody uses it for 7 days, the project pauses and needs a manual unpause from the dashboard before it's reachable again (this will look like a total outage to a user hitting the deployed app).

**Auth:** Supabase Auth (email/password, magic link, or OAuth) is the simplest path — one client-side SDK call, JWTs handle session state, and `auth.uid()` is directly usable inside RLS policies (see below), so it composes naturally with per-candidate row security without any custom backend auth code.

**Resume PDF upload — recommended flow: client-side direct upload with a signed URL, not through the backend.**
- Rationale: routing a multi-MB PDF through your Render backend just to re-upload it to Supabase Storage burns your scarce 512MB RAM/0.1 CPU free-tier compute and your 100GB Render bandwidth for zero benefit — Supabase Storage already handles the upload directly from the browser.
- Pattern: backend (or even direct client call, if your RLS/storage policies allow authenticated users to create their own signed upload URLs) calls `supabase.storage.from('resumes').createSignedUploadUrl(path)`, returns the token to the browser, browser calls `uploadToSignedUrl(path, token, file)` directly against Supabase — the file never touches your Render process. **I could not fetch Supabase's dedicated signed-uploads doc page directly (404) — the method names above are corroborated by the Swift/Kotlin API reference pages and a walkthrough article, but the exact JS/Python call signature should be double-checked against `supabase.com/docs/reference/javascript/storage-from-createsigneduploadurl` before coding.**

**Row Level Security — basic per-user pattern (verified, exact syntax):**
```sql
create table interview_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  session_data jsonb
);
alter table interview_sessions enable row level security;

create policy "select own sessions" on interview_sessions
  for select to authenticated using ( (select auth.uid()) = user_id );
create policy "insert own sessions" on interview_sessions
  for insert to authenticated with check ( (select auth.uid()) = user_id );
create policy "update own sessions" on interview_sessions
  for update to authenticated using ( (select auth.uid()) = user_id ) with check ( (select auth.uid()) = user_id );
```
[supabase.com/docs RLS guide](https://supabase.com/docs/guides/database/postgres/row-level-security)

**Can the LangGraph checkpointer share the DB with app tables?** Yes — `AsyncPostgresSaver.setup()` creates its own dedicated tables (checkpoints, checkpoint writes/blobs) and doesn't touch your app schema, provided you don't have naming collisions. One real interaction to be aware of: **the checkpoint tables count against your 500MB free DB cap** just like everything else — a long interview transcript checkpointed at every node boundary can add up faster than you'd expect (LangGraph checkpoints the *entire state* at each step by default, not a diff), so for a demo/portfolio project this is unlikely to be a problem, but worth monitoring.

**Resume parsing on Render's 512MB RAM:**
- **PyMuPDF (fitz)** is the lightest/fastest option found (~45MB per 100 pages vs. pdfplumber's ~180MB per 100 pages, and 8–12x faster) — but **it's AGPL-licensed**, which may not fit every use case (open-source copyleft obligations if you distribute). For a personal/portfolio project this is likely fine; flag it if this project ever becomes closed-source/commercial.
- **pdfplumber** (MIT) — heavier on RAM but much better at table extraction; unlikely to matter for resume text but worth knowing.
- **pypdf** (MIT, formerly PyPDF2) — a safe, pure-Python, moderate-memory middle ground with a permissive license; **recommended default for this app given resumes are 1–3 pages of mostly plain text** (table extraction rarely matters), and 512MB RAM has to also hold Python/FastAPI/LangGraph/model clients simultaneously.
- **unstructured / docling** — much heavier (designed for complex multi-format document pipelines feeding RAG systems), and risk exceeding 512MB RAM on Render's free tier when loaded alongside the rest of the app; **avoid on free tier** unless you specifically need their layout-aware chunking.
- **DOCX:** `python-docx` is the standard lightweight choice, comparable RAM footprint to pypdf.
- This comparison is synthesized from third-party benchmarks (Medium/pdfmux/link.sc), not an official doc — **treat the specific MB numbers as indicative, not exact**, but the relative ranking (PyMuPDF lightest, unstructured/docling heaviest) is consistent across every source found.

---

## E. Deployment

**Render free tier (verified from render.com/docs/free):**
- Web services: **512MB RAM, 0.1 CPU**, spin down after **15 minutes** of inactivity, ~30-60s cold start, single instance (no horizontal scaling on free), **ephemeral filesystem** (no persistent disk on free tier — another reason all real state must live in Supabase, not on Render's local disk).
- **750 free instance-hours/month** shared across the workspace.
- Free Postgres: 1GB storage, **expires 30 days after creation** with a 14-day grace period — **not usable as your primary DB long-term** (use Supabase for that; if you use Render Postgres at all, it's throwaway/dev only).
- **Background workers are NOT listed as a free service type** — Render's free docs enumerate web services, static sites, Postgres, and Key-Value as free; background workers require a paid plan. **This confirms your instinct and is a real constraint**: it's the reason the architecture above avoids a separate worker process for evaluation and keeps everything inside the one free web service's request/response (or interrupt/resume) cycle.
- WebSockets: Render's docs state no enforced maximum duration for WebSocket connections generally, but **I could not find explicit documentation of free-tier-specific WebSocket behavior during spin-down** — the safest assumption, consistent with the general spin-down behavior, is that an open WebSocket is just another form of "activity" that will eventually be severed when the instance spins down after 15 idle minutes, and any client must be prepared to reconnect (with cold-start delay) rather than assume a persistent connection.

**Netlify free tier (verified from official Netlify blog post):**
- **100GB bandwidth/month, 300 build minutes/month, 125,000 function invocations/month, 1,000,000 edge function invocations/month, 10GB storage.** Exceeding limits suspends the site for the rest of the calendar month (no throttling/grace) — warnings fire at 50/75/90/100%. [netlify.com blog](https://www.netlify.com/blog/introducing-netlify-free-plan/)
- **Flag:** several 2026 third-party sources (temps.sh, costbench) describe a *different*, newer **credit-based** free model ("300 credits/month," ~20 credits/GB bandwidth, implying only ~15GB effective bandwidth) that would be a much tighter constraint than the numbers above. **I could not resolve this conflict from an official source within this session — Netlify's pricing page returned 404s on both URLs I tried.** Given a chat-heavy app is unlikely to stress Netlify bandwidth either way (it's just serving a static React/Vite bundle; the LLM traffic goes through Render, not Netlify), this is a lower-priority thing to verify but **should be checked against `netlify.com/pricing` directly at build time** since it changes cost math if wrong.
- **Connecting React/Vite frontend to Render backend:** set the Render backend URL as a Netlify environment variable (e.g. `VITE_API_URL`) injected at build time; enable CORS on the FastAPI backend for the Netlify domain (`fastapi.middleware.cors.CORSMiddleware`, `allow_origins=["https://your-app.netlify.app"]`).

**What breaks at free tier, concretely, for this app:**
1. Backend cold starts (30-60s) mid-interview after any 15-min gap — mitigated by the interrupt/checkpoint architecture (state survives) plus a UI loading state and optional keep-alive pings.
2. NVIDIA 40 RPM ceiling — a single interview turn might fire 2-3 LLM calls (interviewer response + evaluator + orchestrator/dashboard update); at 40 RPM that's roughly one interview-turn every 4-5 seconds of *sustained* throughput ceiling — fine for one candidate at a time, tight if you ever want to demo two simultaneous interviews.
3. Supabase 7-day pause — a demo left untouched for a week goes dark until manually resumed from the dashboard.
4. Supabase 500MB DB cap shared between app tables and LangGraph checkpoint tables — unlikely to bite for a portfolio project but worth a periodic size check.
5. No free background workers on Render — forces the "keep evaluation inline" architectural decision above; can't casually add a queue later without paying.
6. Render Postgres (if ever used) expires in 30 days — don't rely on it for anything durable; Supabase is the durable store.

---

## F. Real-time to the frontend

**SSE vs WebSocket, given Render free tier — recommend SSE.**
- SSE is simpler to implement (a plain HTTP response FastAPI already streams naturally via `astream()`), auto-reconnects natively in the browser `EventSource` API (important given Render's spin-down/cold-start behavior — a WebSocket that gets severed needs you to hand-roll reconnect logic, whereas `EventSource` reconnects by default), and is one-directional which is all you need here (the candidate's chat replies go over normal POST requests that resume the graph via `Command(resume=...)`; only the *interviewer's* streamed response and the *dashboard's* live updates need to flow server→client).
- FastAPI has **brand-new native SSE support** (`fastapi.sse.EventSourceResponse`/`ServerSentEvent`, shipped in FastAPI 0.135.1, March 2026) — for a beginner-friendly, dependency-light path this is the cleanest current option; the long-standing community alternative is the `sse-starlette` package if you want broader compatibility with older FastAPI pins. [fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/server-sent-events/), [FastAPI PR #15030](https://github.com/fastapi/fastapi/pull/15030)
```python
# Sketch — verify exact current signature against fastapi.tiangolo.com/tutorial/server-sent-events/ at build time
from fastapi.sse import EventSourceResponse, ServerSentEvent

@app.post("/interview/{thread_id}/message", response_class=EventSourceResponse)
async def interview_turn(thread_id: str, body: MessageIn):
    config = {"configurable": {"thread_id": thread_id}}
    async def event_gen():
        async for chunk in graph.astream(Command(resume=body.text), config=config, stream_mode=["messages", "custom"]):
            yield ServerSentEvent(data=chunk_to_json(chunk))
    return event_gen()
```

**Should the orchestrator dashboard use Supabase Realtime (`postgres_changes`) instead of the backend's own stream? Recommend: yes, for the dashboard specifically — split the two concerns.**
- Reasoning: the dashboard is fundamentally "show me the current state of the graph/agents," which is exactly what's already sitting in the checkpointer's Postgres rows (or a lightweight `agent_progress` table your nodes write to as they run) — subscribing to that via Supabase Realtime's `postgres_changes` means the dashboard **stays live even through a Render cold start**, because it's reading from Supabase directly, not from the (possibly-spun-down) Render backend's live stream. This decouples dashboard liveness from backend liveness, which is a meaningful robustness win on a free tier prone to spin-down.
- The candidate-facing chat stream, by contrast, is inherently tied to an in-flight LLM call and has to come from the backend's SSE stream (there's nothing to "subscribe to" in Postgres for tokens that haven't been generated yet).
- Gotchas confirmed from Supabase docs: RLS must be enabled on any table you subscribe to (with a SELECT policy granting the viewer access), and the table must be added to the `supabase_realtime` publication (toggle in dashboard, or `alter publication supabase_realtime add table agent_progress;`). DELETE events aren't filterable and don't respect RLS the same way SELECT does (a documented Realtime-specific caveat, separate from normal RLS behavior) — irrelevant here since you'd only be inserting/updating progress rows, not deleting them. [supabase.com/docs Realtime postgres-changes](https://supabase.com/docs/guides/realtime/postgres-changes)
- **Recommended split:** SSE for the chat panel (token streaming from `graph.astream(..., stream_mode="messages")`), Supabase Realtime `postgres_changes` for the dashboard panel (subscribed directly to a small `agent_progress` table that each graph node writes one row to on entry/exit — cheap writes, and gives you a free audit log of every agent step for later debugging, as a side benefit).

---

## Explicitly unverified / needs re-checking before you build

1. **NVIDIA free tier: credits vs. pure rate-limit model** — conflicting sources; check your own build.nvidia.com dashboard.
2. **`guided_json` support on the hosted `integrate.api.nvidia.com` endpoint** (vs. self-hosted NIM only) — not directly confirmed; build with prompt+parse+retry as a safety net regardless.
3. **Exact version LangGraph introduced the `stream_events()`/typed event-streaming API** — couldn't pin to a changelog entry; start with the older `stream_mode=[...]` API, which is unambiguously documented and stable.
4. **Subgraph `add_node()` exact call signature** — doc page 404'd on both fetch attempts; verify against `docs.langchain.com/oss/python/langgraph/subgraphs` directly when coding.
5. **Netlify free tier: fixed limits (100GB/300min, confirmed via official blog) vs. a newer "300 credits/month" model reported by third parties** — official pricing page 404'd; re-check `netlify.com/pricing` directly. Low-impact either way since Netlify only serves the static frontend bundle.
6. **Supabase signed-upload-URL exact JS/Python method signature** — corroborated via Swift/Kotlin reference pages and a walkthrough, not the canonical JS reference page directly (404).
7. **Render free-tier WebSocket-specific behavior during spin-down** — general WebSocket docs found, free-tier-specific interaction not explicitly documented; SSE recommendation above sidesteps needing this answered.

---

## ~600-word summary

**Recommended architecture:** A single self-hosted LangGraph graph, compiled with a Supabase-Postgres checkpointer, running inside one FastAPI process on Render's free web-service tier. The graph topology is resume ingestion → leveling → interview planning → a `conduct_interview_loop` subgraph (ask → `interrupt()` to wait for the candidate → LLM decides follow-up vs. advance) → inline per-answer evaluation → final scoring → a long-context coaching report. Every HTTP request is stateless; the `thread_id` (the interview session's UUID) is the only thing that ties a request to its graph state, which LangGraph reconstructs from Postgres on each call via `Command(resume=...)`. This is the mechanism that makes the whole thing survive Render's free-tier spin-down: a cold start costs 30-60 seconds of latency, not lost state. The frontend gets the interviewer's streamed tokens over Server-Sent Events (FastAPI now ships this natively as of 0.135), while the orchestrator dashboard subscribes directly to Supabase Realtime (`postgres_changes`) on a lightweight `agent_progress` table — decoupling dashboard liveness from backend liveness entirely, since it reads Postgres directly rather than the backend's live stream. LLM calls go to NVIDIA's OpenAI-compatible `build.nvidia.com` endpoint via `ChatNVIDIA`, using the new Nemotron 3 family: Nano for fast interviewer turns, Super (1M-token context) for feeding whole transcripts into evaluation/coaching, with Llama 3.1/3.3 as a fallback since it has more mature, better-documented tool-calling support. Evaluation runs inline per-answer rather than as a background job, both because Render's free tier has no free background-worker product and because inline keeps everything inside the same checkpointed, crash-safe graph.

**Top 5 risks/gotchas:**
1. **The Supabase-pooler-plus-LangGraph-checkpointer trap.** Supabase recommends a direct (IPv6-only) connection for persistent backends, but Render's free tier is IPv4-only, so direct connection simply won't resolve. The transaction-mode pooler resolves fine but breaks psycopg's prepared statements (`DuplicatePreparedStatement` errors) unless you disable them. The clean fix is the **session-mode pooler** (port 5432 on `pooler.supabase.com`), which is IPv4-reachable and behaves like a normal persistent connection.
2. **`interrupt()`'s re-run-from-node-top semantics.** On resume, the whole node re-executes, not just the code after `interrupt()`. Any side effect placed before the `interrupt()` call inside the same node will fire twice unless it's idempotent — a subtle bug magnet for anyone new to LangGraph.
3. **NVIDIA's free tier is genuinely ambiguous right now** — some sources describe a 5,000-credit trial, others describe a pure 40-requests/minute ceiling with credits phased out; I could not settle this from documentation alone. Either way, 40 RPM is the number to design around, and it's tight once you're firing 2-3 LLM calls (interviewer, evaluator, dashboard commentary) per candidate turn.
4. **Render's ephemeral filesystem and 15-minute spin-down mean literally all durable state must live in Supabase** — no local disk, no in-memory job queue, no background worker (not offered free). This isn't just a performance inconvenience; it's the reason the whole architecture is built around checkpointed, resumable graph state instead of a more conventional request-handler-plus-worker-queue design.
5. **Structured JSON output from free-tier NVIDIA models is not guaranteed reliable.** `with_structured_output` and NIM's `guided_json` are documented, but I couldn't confirm `guided_json` is actually honored on the hosted free endpoint versus only self-hosted NIM containers, and not every catalog model supports tool calling (which structured output typically depends on). Build a prompt-plus-Pydantic-validate-plus-retry fallback from day one rather than trusting native structured output alone.

**What makes "all free" hardest:** the combination of Render's no-background-workers/15-min-spin-down policy with NVIDIA's 40 RPM ceiling and Supabase's 7-day pause — none is individually fatal, but together they mean the app must be architected (checkpointed, stateless-request-resumable, single-process, low-QPS-tolerant) quite differently than a "normal" always-on multi-service app would be, which is exactly what the LangGraph interrupt/checkpoint pattern is well-suited to paper over.

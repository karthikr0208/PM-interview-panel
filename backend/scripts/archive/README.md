# NVIDIA-era probes, archived 2026-07-31

These five scripts probed the NVIDIA NIM endpoint during Phase 0. They are kept
for the audit trail behind DEV-STATE's measurements (the GLM 230s queue, the
`thinking` rejection, the structured-output pass rates) and are **not expected
to run**.

**The project moved to Groq on 2026-07-31.** `with_structured_output` returns
`None` on NVIDIA once the system prompt passes roughly 1500-2800 characters, on
all three of its models, which is the shape every agent in this product uses.
See DEV-STATE § Decisions 2026-07-31.

Two reasons not to simply port them:

- `probe_latency.py` was **already broken** before the migration. It reads
  `NVIDIA_MODEL`, a variable deleted on 2026-07-29 by the three-model split.
  Nobody noticed for two days, which is the exact drift CLAUDE.md's
  triggered-updates table exists to prevent.
- `probe_nvidia.py` tests `ChatNVIDIA` streaming and the `thinking` parameter.
  Neither concept survives the provider change.

**Use `../probe_groq.py` instead.** It probes the live catalog, checks which
models accept a strict JSON schema, and reads the real rate limits from
response headers rather than from documentation.

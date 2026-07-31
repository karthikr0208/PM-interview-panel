# Design System: PM Interview Panel

Generated with the `stitch-design-taste` skill, calibrated against `docs/ARCHITECTURE.md` §8 and
`CLAUDE.md` § Design, which are the authority on every value below. Where the skill's own default
directives conflicted with those two documents, the documents won — see § 8 for the list of
resolved conflicts, as required by the brief that produced this file.

This is a **dense product dashboard used at a desk for 45 minutes**, not a marketing site. Read
that sentence again before reaching for anything in § 8's "ignored" column.

---

## 1. Visual Theme & Atmosphere

A restrained, evidence-first assessment tool. Three fixed columns — orchestration, conversation,
live evaluation — hold their shape for the full 45-minute session; nothing about the shell should
feel like it is auditioning for attention. The atmosphere is closer to a well-instrumented cockpit
than a product demo: calm neutrals, one disciplined accent, and motion that exists only where it
carries real state (an agent is thinking right now) rather than motion as texture.

**Dial calibration** (`ARCHITECTURE.md` §8, `CLAUDE.md` § Design):

| Dial | Value | Reads as |
|---|---|---|
| `DESIGN_VARIANCE` | 3 | Predictable, symmetric. A fixed three-column shell is wrong for asymmetry — this is deliberately the low end of the skill's range. |
| `MOTION_INTENSITY` | 4 | Fluid CSS, but below the skill's own perpetual-micro-interaction threshold on purpose (see § 8). |
| `VISUAL_DENSITY` | 6 | "Daily App Balanced." Card containers stay legitimate at this density; individual rows inside a column use hairlines, not nested cards. |

## 2. Color Palette & Roles

Neutral base, one accent, no gradients. **Light mode is the default palette, not an override** —
permanent dark mode is itself a documented AI tell, and this tool is used at a desk in daylight.

### Light (default)

| Token | Hex | Role |
|---|---|---|
| Background | `#FBFBFA` | App canvas |
| Surface | `#FFFFFF` | Column and card fill |
| Border | `#E6E6E3` | Structural hairlines, dividers |
| Text primary | `#16171A` | Headings, body, primary labels |
| Text secondary | `#6B6D73` | Metadata, timestamps, muted copy |
| **Accent** | `#3A63D0` | CTAs, active state, focus ring — the one accent, under 80% saturation |

### Dark (override, `prefers-color-scheme: dark`)

| Token | Hex | Role |
|---|---|---|
| Background | `#0E0F11` | App canvas |
| Surface | `#17181B` | Column and card fill |
| Border | `#26282D` | Structural hairlines, dividers |
| Text primary | `#ECEDEF` | Headings, body, primary labels |
| Text secondary | `#8B8E96` | Metadata, timestamps, muted copy |
| **Accent** | `#6E92E8` | Same role, lightened for dark contrast |

### Semantic — identical in both modes

| Token | Hex | Role |
|---|---|---|
| Success | `#2E7D5B` | Positive evaluation signal, confirmations |
| Warning | `#B7791F` | Low-confidence fields, non-fatal notices |
| Error | `#B3452C` | Failed nodes, rejected uploads, validation failures |

**Never pure black.** Shadows use a dark-neutral tint derived from `#16171A` (light) /
`#0E0F11`'s own family (dark) — `rgba(22, 23, 26, α)`, never `rgba(0, 0, 0, α)`.

## 3. Typography Rules

- **UI and body:** Geist — track-normal, weight-driven hierarchy, no oversized display type.
  Self-hosted as a variable-weight `woff2` from `frontend/src/assets/fonts/`, `font-display: swap`.
  No CDN, no Google Fonts link.
- **Every numeral:** Geist Mono, unconditionally — not gated behind a density threshold. Timers,
  elapsed-time counters, token counts, and score values must not jitter in width as they update.
  Applied via the `.mono-num` utility (`frontend/src/index.css`), which also sets
  `font-variant-numeric: tabular-nums`.
- **Serif:** banned outright, everywhere, no exception carved out for editorial contexts. This is
  a dashboard, never an editorial surface.
- **Inter:** not used. `Geist` + `Geist Mono` is the named pairing for this product.

## 4. Component Stylings

- **Buttons:** flat fill in accent for primary actions, ghost/outline for secondary. Tactile
  feedback via `scale-[0.98]` on `:active`, `cubic-bezier(0.16, 1, 0.3, 1)` at 150–200ms. No outer
  glow, no custom cursors.
- **Cards:** used where elevation communicates real hierarchy — the three columns themselves, and
  chat message bubbles. At density 6 this is legitimate. Inside a column, individual rows (an
  agent's status line, a rubric dimension's score) are grouped with `border-t` / `divide-y` and
  spacing, not wrapped in their own card. "Rounded cards" describes the shell, not every row in it.
- **Radius:** 8px on cards, 6px on controls, applied consistently.
- **Shadow:** single layer, tinted to the background hue (never pure black, never stacked
  multi-layer elevation).
- **Inputs:** label sits above the input with `gap-2`. No placeholder-as-label. Helper text
  optional; error text below the field, in `#B3452C` / `#B3452C` (dark), plain language.
- **Loading states:** skeletal loaders matching the final layout's shape. **Circular spinners are
  banned anywhere in this product** — v1 §3 Rule 5.
- **Agent status:** four states distinguished by shape *and* color, never color alone —
  `○` waiting, `◉` active (the one legitimate perpetual pulse in the system, because it carries
  real state), `●` done, `⚠` error with a plain-language summary and a details disclosure.
- **Empty states:** composed, states what will appear and why it is empty yet ("Nothing scored
  yet — the first answer will populate this column"), not a bare "No data."

## 5. Layout Principles

- **The shell is the three-column layout from `ARCHITECTURE.md` §8** — orchestration (280px
  fixed) · conversation (fluid centre) · live evaluation (320px fixed). This is not a page that
  needs a hero, a feature grid, or a landing-page narrative; the anti-pattern list below
  deliberately excludes the marketing-page rules the raw skill defaults to.
- **Below 1280px:** graceful collapse to chat-primary with the side panels as tabs. Not a mobile
  redesign — this product's design target is ≥1280px.
- No overlapping elements; every element occupies its own spatial zone.
- Full-height sections use `min-h-[100dvh]`, never `h-screen`.

## 6. Motion & Interaction

- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)`, exposed as the `--ease-standard` token
  (`frontend/src/index.css`) rather than retyped at each call site.
- **Duration:** 150–200ms for standard transitions (`--duration-fast` / `--duration-standard` /
  `--duration-slow`). The one deliberate exception is the scorecard reveal at 400–600ms, per
  `ARCHITECTURE.md` §8 — that is a one-time reveal, not a repeating interaction.
- **`prefers-reduced-motion: reduce`:** durations drop to near-zero (`0.01ms`), not merely
  "less." This is enforced globally in `frontend/src/index.css`.
- **Perpetual micro-interactions are the exception, not the default in this product** — see § 8
  for why the skill's own default is overridden here.
- Animate `transform` and `opacity` only, never `top` / `left` / `width` / `height`.

## 7. Anti-Patterns (Banned)

From `CLAUDE.md` § Design and the v1 + v2 AI-tells lists:

- No serif, anywhere.
- No `Inter`.
- No pure black (`#000000`) — shadows and text use the tinted near-blacks in § 2.
- No `lucide-react`, directly or transitively. `@phosphor-icons/react` only, `weight: "regular"`
  applied globally via `IconContext` (Phosphor's own equivalent of a 1.5px stroke at a 24px
  viewBox — see § 8, this is where the brief's literal `strokeWidth` language met the library's
  actual API).
- No circular loading spinners.
- No fake round numbers in generated content (`50%`, `$1M`) — case-world financials must be
  organic (`31.4%` market share, `$4.7M` ARR).
- No generic placeholder names ("John Doe" register) in generated case worlds, company names, or
  the interviewer persona.
- No em-dashes in user-facing UI copy. (Docs are exempt; anything a candidate reads is not.)
- No raw JSON surfaced to the candidate — agent activity reads as plain language.
- No neon/outer-glow shadows, no oversaturated accents, no custom mouse cursors.
- No AI copywriting clichés ("Elevate", "Seamless", "Unleash", "Next-Gen").
- No emojis in the product UI.

---

## 8. Skill conflicts, resolved in favor of ARCHITECTURE §8

`stitch-design-taste`'s default template targets marketing and landing-page generation. Several of
its stock directives were dropped or inverted for this product; recorded here per the brief's
instruction to flag conflicts rather than silently resolve them.

- **Hero section, inline-image typography, scroll affordances.** The skill's § 4 assumes every
  design has a Hero. This product has no landing page in scope — it opens directly into the
  three-column shell. Ignored in full, matching `ARCHITECTURE.md` §8's own list of ignored
  landing-page rules (heroes, bento grids, marquees, macro-whitespace).
- **"3 equal cards horizontally" ban, and the general card-layout bans in § 6.** The skill bans
  this as a marketing-page feature-row cliché. It does not describe this product's right-rail
  rubric-dimension list or agent-status rail, which are legitimate at density 6. Not applied.
- **Default dial baseline (Variance 8, Motion 6, Density 4).** Overridden entirely by
  `ARCHITECTURE.md` §8's calibrated values (Variance 3, Motion 4, Density 6) — see § 1. The
  skill's own baseline is tuned for expressive marketing pages, the opposite of this brief.
- **Spring-physics motion default (`stiffness: 100, damping: 20`) and "every active component
  should have an infinite loop state."** Directly contradicts `MOTION_INTENSITY 4`, which
  `ARCHITECTURE.md` §8 sets deliberately *below* the skill's own Fluid-CSS band specifically to
  avoid this perpetual-micro-interaction mandate fighting the anti-jitter requirement on numerals.
  The one exception carried over is the active-agent pulse, because it encodes real state, not
  decoration — `ARCHITECTURE.md` §8 names this exception explicitly.
- **Mono-for-numbers gated behind `VISUAL_DENSITY > 7`.** This product sits at density 6, below
  that gate, but `ARCHITECTURE.md` §8 requires mono for *every* numeral unconditionally — a
  stricter rule than the skill's own trigger threshold. The stricter rule wins.
- **`strokeWidth` as a literal icon prop.** The skill (and the brief that invoked it) describe
  icon weight as a numeric `strokeWidth`. `@phosphor-icons/react`'s actual API has no such prop —
  it exposes a `weight` enum (`thin | light | regular | bold | fill | duotone`), and `"regular"`
  is Phosphor's own name for its 1.5px-stroke-at-24px-viewBox weight. `IconStandard`
  (`frontend/src/lib/icons.tsx`) sets `weight: "regular"` globally via `IconContext`, which is the
  correct realization of the brief's intent given the library actually installed.

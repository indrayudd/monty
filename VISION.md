# VISION.md

This is Monty's product vision and UI specification. It is *prescriptive*: it tells a UI-generation LLM what each surface must communicate and how the user must be able to act on it. It does not describe the current state of the codebase. For implementation status, read `README.md`. For architectural details, read `docs/superpowers/specs/2026-04-16-decoupled-kgs-and-llm-wiki-design.md`.

---

## 1. What Monty is

Monty is an autonomous, self-improving early-childhood support agent. It watches a Montessori classroom by ingesting teacher observation notes about toddlers and preschoolers, and turns that unstructured stream into a continuously updated operational picture: who needs help, what triggered it, what's worked before, and what the literature says.

The product's central claim is that Monty is *not* a one-shot classifier. It is an agent that maintains a **persistent, compounding wiki** of what it knows. Every new note arrives, the agent re-reads the affected child's full history, updates a per-student wiki page, decides whether the observation reinforces a known cross-student behavioral pattern or introduces a new one, and — when its curiosity is sufficiently piqued — autonomously fetches and integrates academic research to fill in what it doesn't yet understand.

The user-facing surfaces exist to make that agent's work **legible in real time**. A judge or operator should be able to walk up to the screen and immediately see that *something is happening, the agent is reasoning, and the wiki is growing.*

---

## 2. Who uses it

Monty has three user types in priority order.

**Demo Operator (primary).** Runs the live demo. Needs to start, steer, and present the system on stage. Wants dramatic affordances ("watch what happens when I do this") without losing systemic credibility. Will live in the **God Mode** panel for half the demo.

**Judge / Watcher (primary).** Watches the demo. Needs to immediately understand what they're looking at without explanation. Wants to see *autonomy* (the agent acting), *learning* (the wiki growing), and *insight* (cross-student patterns emerging from individual incidents).

**Educator (future, lower priority).** A real Montessori teacher or director who would use the dashboard at `frontend/` (separate surface, not specified here) to look up specific children. Out of scope for this vision document — handled by the existing dashboard, not the live visualizer.

The visualizer at `backend_visualizer/` (port 3200) is the surface this VISION specifies. It is *for* the Demo Operator and the Judge. Polish, density, and drama matter more than enterprise restraint.

---

## 3. The big idea (encode in every surface)

**The agent maintains a wiki, in markdown, in real time.** Behavioral knowledge accumulates in `wiki/behavioral/` (anonymized, cross-student). Per-child knowledge accumulates in `wiki/students/<Name>/` (named, granular, queryable down to a single incident). The two graphs are *decoupled* — student pages link out to behavioral nodes, but behavioral nodes never link back to student pages. The product's UI must make this anonymization wall visible, not just enforced under the hood.

Five concepts the visualizer must convey at all times:

1. **Two graphs, one shared agent.** The behavioral graph is anonymized and grows because of *all* students. The student graph is named and granular and shows one child at a time. They live in different visual regions; the link between them is *one-way and visible* (student → behavioral, never the reverse).
2. **Live agent loop.** Notes are flowing. Stages tick over. Files appear and pulse. Idleness must look intentional, not broken.
3. **Cross-student reinforcement.** When the same behavioral pattern fires for multiple children, the corresponding behavioral node visibly thickens / glows. The viewer should be able to point at the screen and say "that node has happened to four kids."
4. **Curiosity-driven research.** The agent gets curious. When it does, a paper materializes. This is the system's most agentic moment and must feel that way visually.
5. **Operator agency.** A God Mode affordance (SVG lightning bolt, not emoji) is always one click away. Operators steer personas, force investigations, trigger story presets, and purge-restart without breaking the loop.

---

## 4. Information architecture

Three top-level routes plus one persistent overlay.

| Route | Purpose | When to show |
|---|---|---|
| `/` | **Live** — stacked linked panels for the agent loop in motion | Default landing; the demo lives here |
| `/wiki` | **Wiki Browser** — Obsidian-style file tree + page + backlinks | When viewer wants to see the literal markdown the agent is writing |
| `/console` | **Console** — trace log, agent status, curiosity events stream | When viewer wants the diagnostic / "what is the agent literally doing" view |

**Persistent across all three routes:**
- Top app bar with route nav, Monty wordmark, and demo status pill (`Idle` / `Running` / `Resetting` / `Stopped`).
- Floating bottom-right God Mode trigger with SVG lightning bolt icon (only on `/`; absent on `/wiki` and `/console`).

No left-nav drawer. No user menu. No authentication surfaces. No notification center.

---

## 5. Page-by-page specifications (current implementation)

> This section describes what is **actually built and verified via Playwright** — not aspirational features. A UI agent redesigning these surfaces should treat this as ground truth for current functionality while improving aesthetics, layout, and interaction design.

### 5.1 `/` — Live (default landing)

The stage. Where the agent loop is observed in motion. Layout is **vertically stacked**, full-viewport, with a slim middle stage-rail strip.

```
┌────────────────────────────────────────────────────────────────────┐
│  TOP APP BAR  (route nav · Monty wordmark · status pill)           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   BEHAVIORAL KG PANEL  (force-directed graph, ~55% height)        │
│   legend chip top-left · min-support control top-right             │
│   nodes sized by support_count, colored by type                    │
│   hover shows label · click highlights + cross-references          │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│   STAGE RAIL  (7 checkpoints, ~40px, active stage glows green)    │
├────────────────────────────────────────────────────────────────────┤
│   5 persona chips (left)                [Timeline|Graph|Research] │
│                                                                    │
│   BOTTOM PANEL (content depends on active tab, ~40% height)       │
│   Timeline: horizontal scroll of incident cards                    │
│   Graph: per-student behavioral subgraph (force-directed)          │
│   Research: list of OpenAlex papers fetched for this student       │
│                                                                    │
│                                        ┌─────────────────┐        │
│                                        │  ⚡ God Mode     │        │
│                                        └─────────────────┘        │
└────────────────────────────────────────────────────────────────────┘
```

#### 5.1.A Behavioral KG panel (top, ~55% viewport height)

A force-directed graph (react-force-graph-2d) of the anonymized cross-student behavioral knowledge. Canvas dimensions are measured from the actual container via ResizeObserver and passed explicitly so the graph centers correctly within its panel.

**Currently implemented visual encoding:**
- **Node color** = node type. Seven types each get a distinct color:
  - `setting_event` = violet (#7c3aed)
  - `antecedent` = sky (#0ea5e9)
  - `behavior` = orange (#f97316)
  - `function` = emerald (#10b981)
  - `brain_state` = amber (#eab308)
  - `response` = pink (#ec4899)
  - `protective_factor` = muted slate (#94a3b8)
  Legend chip is top-left with color swatches and type names.
- **Node size** = `log2(1 + support_count) * 4`, minimum 2. Log-scaled so high-frequency nodes are visibly larger.
- **Node halo** = `curiosity_score`:
  - `< 0.5`: no halo.
  - `≥ 0.5`: yellow halo (static, rgba(234,179,8,0.25)).
  - `≥ 0.7`: red halo, **pulsing** at ~1.5 Hz via `Date.now() % 700` opacity modulation (0.15–0.45) with radius oscillation.
- **Node labels** = hover-only. On hover, the node's title renders as a small canvas-drawn label (9-12px, 75% opacity). Selected nodes also show their label. No tooltip — the canvas label replaces it.
- **Edge thickness** = `log2(1 + support_count)`, minimum 0.5. Directional arrows (3px, 85% along edge).
- **Edge color** = per-relationship-type from a 13-color palette (triggers=sky, serves=emerald, occurs_in=amber, reinforces=green, extinguishes=red, co-regulates=purple, recurs_with=orange, predisposes=violet, amplifies=rose, gates=cyan, follows=slate, evidences=emerald, undermines=red).
- **Min support control** (top-right): numeric input, default 2. Edges with `support_count < min_support` are hidden. Hover tooltip explains what this does. Counter shows `{nodes}n · {edges}e`.

**Physics tuning (currently applied):**
- `warmupTicks=80` — pre-settles positions before first render.
- `cooldownTicks=60`, `d3AlphaDecay=0.1`, `d3VelocityDecay=0.55`.
- Charge force: `strength(-45)`, `distanceMax(260)`.
- Centering forces: `forceX(0).strength(0.06)`, `forceY(0).strength(0.06)` — prevents isolated nodes from drifting.
- `zoomToFit(400, 40)` fires once on first engine stop, then user's pan/zoom is preserved.

**Interactions:**
- **Hover node:** canvas-drawn label appears (no HTML tooltip).
- **Click node:** white selection ring on the node. In the bottom panel (Timeline view), incident cards whose `behavioral_ref_slugs` contain the selected slug get a white border glow and scroll into view.
- **Click empty space:** clears selection.
- **Scroll/drag:** standard pan and zoom. User's viewport persists across data-poll updates.

**Empty state:** centered text "Awaiting first note — the agent has not seen any classroom observations yet."

**Degraded state:** amber banner "⚠ behavioral-graph unreachable — last render retained."

#### 5.1.B Stage rail (middle, ~40px tall)

Seven labeled checkpoints in a horizontal strip:

`waiting for note → ingesting note → reassessing student → updating profile → enriching knowledge → writing alert → cycle complete`

- Active stage: bright green dot + subtle glow + bold text.
- Completed (earlier) stages: dim green dot.
- Inactive (later) stages: dim gray dot, muted text.
- Polls `/api/demo/overview` every 1s.

#### 5.1.C Per-student panel (bottom, ~40% viewport height)

Header row contains **persona chips** (left) and **view tabs** (right).

**Persona chips:** 5 buttons, one per child. Each shows: first-initial circle, full name, age band. Active chip has a white border + bg-white/5. Clicking a chip switches the bottom panel's content to that student's data. All 5 students' incidents are **pre-cached** in the parent (polled via `Promise.allSettled` every 2s) so switching is instant.

**View tabs:** `Timeline` | `Graph` | `Research` — three buttons on the right side of the header row. Active tab is bg-white/10.

##### Timeline view (default)

Horizontally scrolling row of **incident cards**, newest on the right. Each card (~224px wide):
- Relative timestamp ("2m ago").
- Severity dot (green/yellow/red) in the corner.
- Note ID ("note #5").
- Row of type-name chips at the bottom showing which behavioral node *types* this incident touched (e.g., `setting_events`, `antecedents`, `behaviors`). If >6 refs, shows "+N" overflow.

**Click card → Incident Detail Drawer** slides in from the right (~720px wide, full height). Contains:
- File path header (e.g., `students/Arjun_Nair/incidents/2026-04-17-1752-...md`).
- Collapsible frontmatter card (key-value: behavioral_refs, educator, ingested_at, note_id, peers_present, severity, student).
- Rendered markdown body: `## Note` (the original observation text) + `## Interpretation` (the agent's assessment).
- **Linked behavioral nodes** section: clickable pill buttons for each behavioral ref. Clicking a pill closes the drawer and selects that node in the top panel.
- Dismiss: Esc key or click backdrop.

**Cross-highlighting:** When a node is selected in the top panel, incident cards in the timeline whose `behavioral_ref_slugs` include that node get a white border glow.

**Empty state:** "No observations yet for {Name} — try God Mode → Inject Note."

##### Graph view

Per-student force-directed subgraph showing only the behavioral nodes **this student** has touched, sized by **this student's touch count** (not the global support_count). Uses the same type-color palette and physics tuning as the top panel.

- Nodes = unique behavioral refs from this student's incidents.
- Node size = `log2(1 + student_touch_count) * 5`.
- Edges = co-occurrence of refs within the same incident (two refs that appeared together). Edge width = `log2(1 + co_occurrence_count)`.
- Node identity persists across polls (no re-layout on each data update).
- Same hover-only labeling as the top panel.
- Click a node → sets it as the selected slug, which also highlights it in the top panel.
- `zoomToFit` fires once on first settle.

**Info card** (top-left): student name, `N incidents · M nodes touched · node size = this student's touch count`.

**Empty state:** "No behavioral nodes touched by {Name} yet. Wait for the agent loop to process incoming notes, or inject a few via God Mode."

##### Research view

Vertical scrolling list of OpenAlex papers the curiosity gate has fetched for this student. Each paper card:
- Title (bold, white).
- Year + cited_by_count (right-aligned, muted).
- Authors (italic, muted).
- Relevance summary (if present).
- "open ↗" link to the paper's `landing_page_url` (opens in new tab).

Data from `GET /api/student-graph/{name}/research`. Polled every 3s.

**Empty state:** "No research fetched for {Name} yet. The curiosity gate fires when behavioral nodes accumulate enough support_count + students_count to cross threshold 0.70. You can also force it via God Mode → Manual research trigger."

#### 5.1.D God Mode slide-in panel (overlay)

**Trigger:** floating pill button bottom-right of `/`: SVG lightning bolt icon + "God Mode" text, bg-rose-600, rounded-full, shadow-lg.

**Panel:** slides in from right (~420px wide), full height, bg-zinc-950/95 backdrop-blur, border-l border-white/20. Backdrop dims at ~30% opacity. Dismiss: Esc or click backdrop.

**Layout (top to bottom):**

**1. Header:** SVG bolt icon (rose-400) + "God Mode" text (font-mono), "esc" dismiss button on right.

**2. Story preset row** — 5 pill buttons wrapping:
`Calm Morning` · `Escalating Mira` · `Group Conflict` · `Emergency Cascade` · `Reset to Baseline`

Each preset sets all 5 personas' sliders + activity_weights to coordinated values via parallel `PATCH /api/personas/{name}` calls.

**3. Per-persona steering cards** — 5 cards stacked, each bordered `border-white/10 rounded-lg`:
- **Header:** name (bold), age band, dysfunction flavor (muted, right-aligned).
- **Slider:** "Functional ↔ Dysfunctional (0.0)" label + range input (`-1.0` to `+1.0`, step 0.1). Track has a green-to-red gradient via `accent-rose-400`.
- **Controls row:** flavor dropdown (5 options: impulsive, clingy-then-shutdown, scattered, explosive-then-shutdown, shutdown) + activity weight numeric input (0 to 3, step 0.1).
- **Inject row:** 4 small buttons — `Neutral` · `Problematic` · `Emergency` · `Surprise`. One-shot directive for the next generation only.
- **Interact row:** "interact:" label + dropdown listing the other 4 personas. Selecting one conditions both students' next notes on a shared scene.

**4. Curiosity Tuning** (collapsed by default, disclosure toggle):
- 6 range sliders (0–0.50, step 0.01): `novelty`, `recurrence_gap`, `cross_student`, `surprise`, `severity_weight`, `recency`.
- Each shows current value. Changes via `PATCH /api/runtime/curiosity-weights`.

**5. Manual research trigger:**
- Text input (placeholder "behavioral node slug") + "Investigate" button (bg-rose-600).
- Fires `POST /api/curiosity/investigate/{slug}`. Shows result inline: `fire=true/false score=0.XX reason=...`.

**6. Demo lifecycle row:** 3 buttons: `Start` (emerald) · `Reset` (amber) · `Stop` (rose).

**7. Reindex button:** "Reindex wiki (full rebuild)" — calls `POST /api/wiki/reindex`, alerts the result.

**8. Purge button:** "Purge everything (fresh start)" — dark red styling (bg-rose-950, text-rose-300, border-rose-700/50). Shows `window.confirm` gate. Calls `POST /api/admin/purge` which truncates all 12 DB tables + wipes wiki/behavioral, wiki/students/*/incidents, wiki/sources/openalex generated content. Preserves wiki/personas + skeleton. Page reloads on success.

State persists in `agent_runtime_state.god_mode_overrides`. Survives page reloads.

---

### 5.2 `/wiki` — Wiki Browser

Three-pane Obsidian-style reader for the markdown wiki at `wiki/`.

```
┌──────────────┬─────────────────────────────────────┬────────────────┐
│              │                                     │                │
│  FILE TREE   │   RENDERED MARKDOWN                 │  BACKLINKS     │
│  (~240px)    │   (flexible, scrollable)            │  (~280px)      │
│              │                                     │                │
│  [filter…]   │   path breadcrumb     [raw] toggle  │  Linked from:  │
│  index.md    │   ▼ frontmatter (collapsible JSON)  │   page1.md     │
│  log.md      │   # Page Title                      │   page2.md     │
│  schema.md   │   body markdown…                    │                │
│  ▸ behavioral│   [[wikilinks]] are clickable       │                │
│  ▸ personas  │                                     │                │
│  ▸ students  │                                     │                │
└──────────────┴─────────────────────────────────────┴────────────────┘
```

**Left pane — File tree:**
- Mirrors `wiki/` directory structure. Folders have disclosure triangles (▸ / ▾).
- Files modified in the last 30s **pulse green** (CSS `animate-pulse` + bg-emerald-500/20). Files modified in last 5 minutes get a faint emerald highlight.
- Filter textbox at top narrows the tree by filename match.
- Top-level files (`index.md`, `log.md`, `schema.md`) pinned above folders.
- Clicking a file loads it in the middle pane. Active file gets white text + bg-white/10.

**Middle pane — Rendered markdown:**
- Path breadcrumb at top (e.g., `behavioral/functions/desire-for-accuracy.md`).
- "raw" toggle button (top-right) switches between rendered markdown and raw source.
- Frontmatter rendered as a collapsible `<details open>` JSON card (monospace, bg-black/30).
- Body rendered via `react-markdown` + `remark-gfm`. Standard headings, lists, blockquotes.
- **Wikilinks** (markdown links ending in `.md` or relative paths) are clickable and navigate within the pane. Links are resolved relative to the current page's directory (e.g., from `students/Arjun_Nair/timeline.md`, clicking `incidents/foo.md` resolves to `students/Arjun_Nair/incidents/foo.md`).
- All internal links render as `text-sky-400 underline`.
- For behavioral node pages: body shows `## Summary` (one-line definition) + `## Evidence` (anonymized bullet list of observations).

**Right pane — Backlinks:**
- "Linked from" header, followed by a list of wiki page paths that reference the current page (computed by scanning all wiki files for the current path string).

**Page types you'll see:**

| Page | Location | Content |
|---|---|---|
| Wiki Index | `index.md` | Auto-generated catalog: Setting Events, Antecedents, Behaviors, Functions, Brain States, Responses, Protective Factors, Students, Personas, Research Sources. Each item is a clickable link. |
| Agent Log | `log.md` | Append-only chronological entries: `## [YYYY-MM-DD HH:MM] action \| subject` |
| Schema | `schema.md` | LLM instruction sheet: three-layer architecture, anonymization wall rules, frontmatter conventions, update protocol |
| Behavioral node | `behavioral/<type>/<slug>.md` | Frontmatter (type, slug, support_count, students_count, curiosity_score, _student_hashes, etc.) + Summary + Evidence bullets |
| Behavioral edge | `behavioral/_edges/<src>--<rel>--<dst>.md` | Frontmatter (src_slug, rel, dst_slug, support_count, students_count) + Evidence bullets |
| Student incident | `students/<Name>/incidents/<ts>-<slug>.md` | Frontmatter (student, note_id, severity, behavioral_refs, peers_present, educator) + Note (verbatim observation) + Interpretation |
| Student profile | `students/<Name>/profile.md` | Current severity, trend, latest summary, patterns, suggestions |
| Student timeline | `students/<Name>/timeline.md` | Chronological list of incident links with severity |
| Student patterns | `students/<Name>/patterns.md` | Behavioral refs ranked by frequency |
| Persona | `personas/<Name>.md` | Frontmatter (name, age_band, temperament_axes, dysfunction_flavor, recurring_companions) + narrative prose |

---

### 5.3 `/console` — Console

Diagnostic surface. Two vertically stacked sections.

**Section 1 — Agent Status** (bordered card, monospace):
Raw JSON dump of `agent_runtime_state` row: current_note_id, current_stage, current_student, last_cycle_at, last_processed_note_id, stage_message, started, mode, etc. Polled every 1.5s.

**Section 2 — Curiosity Events** (bordered card, monospace):
Header: "Curiosity events" with count badge ("N loaded").
Each row: timestamp | fire/skip indicator (green/gray) | node slug | curiosity score | 6 factor mini-bars (inline `<span>` elements, height proportional to factor value, titled with `factor_name: value`).

Data from `GET /api/curiosity/events?limit=50`. Polled every 1.5s.

**Empty state:** "(no curiosity evaluations yet — the agent will start emitting these once nodes begin attracting attention)"

**No God Mode trigger on this route** — Console is read-only diagnostic.

---

## 6. Visual language

The visualizer must look like a *live operations surface*, not a marketing site. Lean toward a dark theme with high-contrast accents, but the UI agent has latitude. Mandatory semantic conventions:

**Severity colors** (used wherever a student or incident has a severity):
- Green = settled / normalized / no concern.
- Yellow = caution / pattern emerging / monitor.
- Red = emergency / acute risk / immediate action.

These three colors must be **distinctly distinguishable for color-blind viewers** (use shape or position cues alongside color where possible — e.g., severity dots also vary in fill pattern, or red severity dots get a thin border).

**Behavioral node-type palette.** Six core types each get a distinct hue. Choose colors that:
- Are perceptually separable from each other and from the severity palette.
- Do *not* repurpose red/yellow/green (reserved for severity).
- Maintain the same hue across `/` and `/wiki` so wikilink pills in markdown match nodes in the graph.

**Curiosity halos.** Yellow at score ≥ 0.5, red at ≥ 0.7. Pulsing only at ≥ 0.7. The yellow halo here is allowed to overlap with the severity yellow because context disambiguates (severity yellow is on student chips and incident dots; curiosity yellow is on behavioral nodes).

**Edge weight.** Thickness scales with `support_count`. Render thresholding (default ≥ 2) is a *toggle*, not a hard rule.

**Anonymization legibility.** The behavioral panel uses *only* anonymized prose ("a 3-4 year old who…", "a peer reaches for a chosen material…"). The student panel uses names and ages openly. The visual distance between the two panels — the empty band of the stage rail — is part of the encoding.

**Live-feel cues** (use throughout):
- Brief highlight + fade for new content (~400-600ms).
- Subtle pulse for "this is fresh" (last 30s) decaying to a faint highlight (last 5 min).
- Pulsing halo for high-curiosity nodes.
- Force-directed layout settles, never snaps.
- Static surfaces look slightly *expectant* in idle (faint waiting cues), not blank.

**Density.** Lean dense. Information-rich, like a flight ops console. Avoid the "marketing dashboard" trap of huge cards with single numbers. Judges should feel "there is a lot happening here, and I can see it."

**Typography.** Use a clean sans-serif for UI chrome and a monospace for code-like content (frontmatter, trace log, IDs, file paths). One display weight max for hierarchy; rely on size and color, not weight, for emphasis.

---

## 7. State semantics

Every panel must handle these states explicitly. Don't rely on default browser behavior.

**Demo lifecycle states** (visible in the top app bar status pill):
- `Idle` — demo_runtime.mode is idle AND no recent agent cycle detected. Shows when the system is completely at rest.
- `Running` — either demo_runtime.mode is "running" OR `last_cycle_at` is within the last 30 seconds (agent loop is actively processing even if the demo wasn't formally "started" via God Mode). This means the streamer + agent_loop running from CLI also shows "Running".
- `Resetting` — destructive restart in progress.
- `Stopped` — explicitly halted via God Mode.
- `Unreachable` — API didn't respond to the overview poll.

**Workflow stages** (Stage Rail, only meaningful when `Running`):
`waiting_for_note → ingesting_note → reassessing_student → updating_profile → enriching_knowledge → writing_alert → cycle_complete`

**Per-panel states:**
- **Loading:** brief skeleton (no spinning circles — they read as "broken"). Use shimmer or skeleton boxes shaped like the eventual content.
- **Empty:** plain-language explanation of why it's empty + the next operator action ("Try ⚡ God Mode → Inject Note").
- **Error:** *graceful degradation* takes priority over alert toasts. If `/api/demo/overview` returns a degraded payload, the app shows its data with a small "⚠ Data temporarily degraded — last sync 12s ago" banner above the affected panel; everything else continues to work. Full failure (e.g., API unreachable) shows a single non-blocking banner with a "retry" affordance.

---

## 8. Persona reference (who the children are)

The current persona set is five children whose names recur across the demo. UI surfaces should treat them as named entities everywhere on `/wiki/students/` and on the student timeline / chips:

- **Arjun Nair**
- **Diya Malhotra**
- **Kiaan Gupta**
- **Mira Shah**
- **Saanvi Verma**

Each has a hand-authored persona doc at `wiki/personas/<Name>.md` defining temperament, dysfunction flavor, and recurring companions. The God Mode persona cards are ordered to match this list.

**Avatars.** Use first-initial circles tinted by the student's current severity. No photos.

---

## 9. Interaction principles

- **Demo-first defaults.** Every page boots into a state that is interesting to look at within 3 seconds, even before the user does anything. Empty states still convey "this is alive, just waiting."
- **No modals.** God Mode is a slide-in panel, not a modal dialog. The Incident Detail is a slide-in drawer, not a modal. Both dismiss with Esc or backdrop click and never block the underlying surface from updating live.
- **Cross-surface linking.** Wikilink pills in `/wiki` can deep-link to `/` with a node selected. Behavioral pills in incident drawers do the same. The two routes are linked, not siloed.
- **Operator ergonomics.** Sliders snap to 0.1 increments (so the operator can hit "0.7" cleanly during a demo, not "0.694…"). Story presets are large click targets (~48px tall). Inject buttons are within thumb's reach if used on a touchscreen.
- **Keyboard.** `Esc` closes any slide-in. `g` then `1`/`2`/`3` switches routes (Live / Wiki / Console). `?` opens a small keyboard cheatsheet popover.

---

## 10. What NOT to design

The UI agent should **not** design or include any of the following — they are explicitly out of scope:

- Login, sign-up, password reset, account settings.
- Notification center, email digests, push notifications.
- Markdown *editing* (the Wiki Browser is read-only).
- A persona authoring UI (personas are edited as `wiki/personas/*.md` text files directly).
- Vector search, semantic search across the wiki (the existing `index.md` catalog and filename search are sufficient).
- Multi-tenant / team / org switching.
- Slide-deck or PDF export.
- Marketing pages (no landing page, pricing, about, etc.).
- A separate dashboard for educators — that's a different surface (`frontend/`, port 3000) with its own current implementation.
- Onboarding tours or empty-state CTAs that try to "convert" the user. The operator already knows what to do.

---

## 11. Success criteria for a UI design

A UI design is successful if a viewer who has *not* read this document can, within 60 seconds of watching `/`:

1. See that two distinct kinds of knowledge are accumulating (behavioral and per-student).
2. See that the per-student knowledge is named and the behavioral knowledge is anonymized.
3. Notice when a behavioral node thickens / glows because of cross-student reinforcement.
4. Witness at least one curiosity-gate trip + research animation and recognize it as the agent making a decision.
5. Find and use the God Mode affordance without prompting.
6. Switch to `/wiki` and immediately understand "the agent is literally writing markdown files right now."

If the design achieves those six things, the vision is satisfied. Everything else is taste.

---

## 12. Tech stack (for the UI agent)

The current visualizer is built with:
- **Next.js 16** (App Router, Turbopack) + TypeScript + Tailwind CSS v4
- **react-force-graph-2d** for both graph panels (canvas-based, d3-force layout)
- **react-markdown** + remark-gfm for wiki rendering
- **d3-force** (forceX, forceY) for custom force tuning
- **Local SQLite** (`data/monty.db`) — no remote DB dependency
- Dark theme: bg-zinc-950/900 base, white/N opacity text, border-white/10

All components are in `backend_visualizer/app/components/`. API client is `backend_visualizer/app/lib/api.ts` with typed helpers for all 20+ endpoints.

## 13. Pointers for implementation context

- Architecture spec: `docs/superpowers/specs/2026-04-16-decoupled-kgs-and-llm-wiki-design.md`
- LLM-wiki paradigm origin: `llm-wiki.md`
- Project context: `CLAUDE.md`
- Original direction scratch: `Direction.txt`
- Current implementation status: `README.md`
- Playwright screenshots: `screenshots/01-live-page.png` through `screenshots/10-incident-drawer.png`

This vision document and the spec must stay in sync. If the spec changes, this file changes. If a design decision is made in this file that the spec doesn't cover, the spec must be amended.

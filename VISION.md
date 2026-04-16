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
5. **Operator agency.** A "⚡ God Mode" affordance is always one click away. Operators steer personas, force investigations, and trigger story presets without breaking the loop.

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
- Floating bottom-right "⚡ God Mode" trigger (only on `/`; absent on `/wiki` and `/console`).

No left-nav drawer. No user menu. No authentication surfaces. No notification center.

---

## 5. Page-by-page specifications

### 5.1 `/` — Live (default landing)

The stage. Where the agent loop is observed in motion. Layout is **vertically stacked**, full-viewport, with a slim middle stage-rail strip. Left/right rails are reserved for graph overlays — no persistent side panels here (God Mode is a slide-in, not a docked rail).

```
┌────────────────────────────────────────────────────────────────────┐
│  TOP APP BAR  (route nav · Monty wordmark · demo status pill)      │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  BEHAVIORAL KG PANEL  (anonymized, cross-student)         │   │
│   │   force-directed graph canvas                              │   │
│   │   legend chip top-left · controls top-right                │   │
│   │   ~50% viewport height                                     │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                    │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  STAGE RAIL  (waiting → ingesting → … → cycle_complete)   │   │
│   │   slim horizontal strip, ~40px tall                        │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                    │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  PER-STUDENT TIMELINE PANEL                                │   │
│   │   student selector (5 chips, severity-tinted) at top       │   │
│   │   horizontal scroll of incident cards, newest right        │   │
│   │   ~45% viewport height                                     │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                    │
│                                          ┌──────────────────┐     │
│                                          │  ⚡ God Mode      │     │
│                                          └──────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

#### 5.1.A Behavioral KG panel (top, ~50% viewport height)

A force-directed graph of the anonymized cross-student behavioral knowledge.

**What it shows.** Nodes are behavioral concepts. Edges are typed relationships. Both accumulate as the agent ingests notes.

**Visual encoding (must convey):**
- **Node color** = node type. Six core types (SettingEvent, Antecedent, Behavior, Function, BrainState, Response) each get a distinct color. ProtectiveFactor (optional 7th) uses a muted variant. The legend chip top-left lists all visible types with swatches.
- **Node size** = `support_count` (log-scaled, capped). A node observed many times is visibly larger than a node observed once.
- **Node halo** = `curiosity_score`.
  - `< 0.5`: no halo.
  - `≥ 0.5`: yellow halo, subtle and steady.
  - `≥ 0.7`: red halo, *pulsing* at ~1.5 Hz.
  Halo is the agent's "I'm thinking about this" signal.
- **Edge thickness** = edge `support_count`. Default minimum to render = 2 (single co-occurrence is noise; recurrence is signal). Toggle in panel header to show all.
- **Edge color** = relationship label (triggers / serves / occurs_in / reinforces / extinguishes / co-regulates / recurs_with / predisposes / amplifies / gates / follows / evidences / undermines). Color-coded distinctly enough that the viewer can spot reinforcement edges from triggering edges at a glance.

**Live behavior (must animate):**
- New nodes fade in over ~600ms when the agent creates them.
- Existing nodes that get touched (`support_count` incremented) briefly bloom (size pulse + brighter fill) for ~400ms.
- When the **curiosity gate trips** on a node, an animated arrow flies from the node toward a paper icon that spawns at the panel periphery. The paper icon settles into a small "research stack" in a corner, click → opens that paper's `wiki/sources/openalex/<id>.md` in the incident drawer.
- Force-directed layout settles smoothly; no jarring re-layouts when a new node arrives.

**Interactions:**
- **Hover node:** tooltip with node type, title, summary (first sentence of `## Summary` from the markdown), `support_count`, `students_count`, `curiosity_score`, and a one-line breakdown of curiosity factors.
- **Click node:** highlight the node + its 1-hop neighborhood in the top panel; *simultaneously* highlight every incident card in the bottom panel that references this node (cards pulse a thin border and scroll into view). Click outside to clear.
- **Click edge:** small popover with edge type, `support_count`, `students_count`, first/last observed timestamps.

**Empty state:** placeholder copy "Awaiting first note — the agent has not seen any classroom observations yet" + a faint outline of where the graph will appear. Not a spinner; the canvas itself.

#### 5.1.B Stage rail (middle, ~40px tall)

A horizontal strip of seven labeled checkpoints, left to right:

`waiting_for_note → ingesting_note → reassessing_student → updating_profile → enriching_knowledge → writing_alert → cycle_complete`

The currently active stage is highlighted (bright fill + subtle glow). Completed stages show a checkmark. Inactive stages are dim. Resets at each cycle.

When the cycle is `idle`, all stages are dim and the rail shows a faint pulse on `waiting_for_note`.

#### 5.1.C Per-student timeline panel (bottom, ~45% viewport height)

A horizontal timeline of incident cards for one selected student.

**Top of panel:** five **student chips** in a row, each tinted by current severity (green / yellow / red). The active chip has a stronger border + slight elevation. Each chip shows: student avatar (initial in a circle), name, current severity dot, incident count for the session.

**Body of panel:** horizontally scrolling row of **incident cards**, newest on the right. Each card:
- Timestamp (relative — "12s ago" preferred over absolute).
- Severity dot (red / yellow / green).
- One-sentence behavior summary.
- A row of small color-chips at the bottom showing which behavioral node *types* this incident touched (one chip per type referenced — these match the node-color palette in the top panel).

When a new incident arrives, its card slides in from the right with a brief highlight; older cards push leftward.

**Interactions:**
- **Click card:** opens an **Incident Detail Drawer** (slides in from the right, ~720px wide, full height, dismiss with Esc or backdrop click). Drawer renders the incident's markdown:
  - Frontmatter as a key-value card at top (severity, timestamp, peers present, educator).
  - The note text under `## Note`.
  - The agent's interpretation under `## Interpretation` with linked behavioral nodes rendered as colored pills (clicking a pill closes the drawer and selects that node in the top panel).
  - A "Research" section if any OpenAlex papers were linked, rendering paper title + one-sentence relevance.
- **Click student chip:** swaps the timeline content to that student's incidents.

**Empty state:** when a selected student has no incidents yet, show "No observations yet for {Name} — try ⚡ God Mode → Inject Note."

#### 5.1.D God Mode slide-in panel (overlay)

Trigger: floating "⚡ God Mode" button bottom-right of `/`. Click → panel slides in from the right (~420px wide, full height, dark glass aesthetic distinct from the rest of the surface, behind-overlay dim at ~30% opacity to signal modality without losing context). Esc / backdrop click → slides out.

Internal layout, top to bottom:

**1. Story preset row** — large pill buttons in a single row that wrap if needed:
`Calm Morning` · `Escalating Mira` · `Group Conflict` · `Emergency Cascade` · `Reset to Baseline`

One click coordinates all five persona sliders, flavors, and activity weights into a preset configuration.

**2. Per-persona steering cards** — five cards stacked vertically, one per child, no scrolling-to-find. Each card:

- **Header row:** name, age band chip, current severity dot, freshness ("last note 4s ago").
- **Functional ↔ Dysfunctional slider** (`-1.0` … `+1.0`). The visual anchor of each card. Track is gradient from green (left) to red (right). Knob shows current value.
- **Flavor dropdown:** overrides the persona doc's default for this session. Options like `explosive`, `shutdown`, `clingy`, `impulsive`, `scattered`.
- **Activity weight slider** (0 = paused, 1 = normal, 2 = double frequency). Lets operator spotlight one child for a beat.
- **"Inject next note" row:** four small buttons — `Neutral` · `Problematic` · `Emergency` · `Surprise`. One-shot directive applied to the very next generation for this child only, then the slider behavior resumes.
- **"Force interaction with..." mini-dropdown:** pick another persona; the next note for *both* will be conditioned on a shared scene. Drives peer-conflict storylines on demand.

**3. Curiosity Tuning** (collapsed by default) — six sliders for the curiosity weights (`novelty`, `recurrence_gap`, `cross_student`, `surprise`, `severity_weight`, `recency`). Defaults pre-set; expose so the operator can dial up "surprise" for a more contrarian agent or "severity_weight" for safety-first runs.

**4. Manual research trigger** — a search box with autocomplete over all behavioral node names + an `Investigate` button. Forces a curiosity-gate trip on the chosen node, fires the research animation in the live panel below the overlay. Useful when a judge asks "what if you investigated X?"

**5. Demo lifecycle** — three buttons at the bottom: `Start` · `Reset` · `Stop`. (Moved from the top app bar to consolidate operator controls.)

**Live propagation cue.** When a slider is moved, a faint pulse animates from the moved card to the corresponding student chip in the bottom panel *behind the overlay* (visible through the dim) — so the operator can see the nudge land before the next note even fires.

State persists in `agent_runtime_state.god_mode_overrides`. Survives reloads. Quieter operators can collapse God Mode entirely; demo operators keep it pinned open.

---

### 5.2 `/wiki` — Wiki Browser

Obsidian-style three-pane reader for the markdown wiki the agent maintains in `wiki/`.

```
┌─────────────────────────────────────────────────────────────────────┐
│ TOP APP BAR                                                          │
├──────────────┬─────────────────────────────────────┬────────────────┤
│              │                                     │                │
│  FILE TREE   │   RENDERED MARKDOWN                 │  BACKLINKS     │
│  (left, ~280)│   (middle, flexible)                │  (right, ~280) │
│              │                                     │                │
│  search      │   page title                        │  Linked from:  │
│  ▸ behavioral│   frontmatter card                  │   • <page>     │
│  ▸ students  │   body…                             │   • <page>     │
│  ▸ sources   │                                     │                │
│  ▸ personas  │   inline graph thumbnail            │  Links out:    │
│  schema.md   │   (for behavioral nodes only)       │   • <page>     │
│  index.md    │                                     │                │
│  log.md      │                                     │  [raw] toggle  │
│              │                                     │                │
└──────────────┴─────────────────────────────────────┴────────────────┘
```

**Left pane — File tree.**
- Mirrors `wiki/` directory structure exactly. Folders expand/collapse with disclosure triangles.
- Files modified in the last 30s **pulse green** (subtle breathing animation). Files modified in the last 5 minutes show a faint highlight bar. This is the "agent is writing the wiki right now" signal — critical to the surface.
- Search box at top, filters by filename and frontmatter tags as you type.
- Top-level files (`schema.md`, `index.md`, `log.md`) pinned above the folders.

**Middle pane — Rendered markdown.**
- Standard markdown rendering. Headings, lists, code blocks, tables.
- Wikilinks (`[[behavioral/antecedents/peer-takes-material]]`) render as colored pills (color matches the node-type palette from `/`) and are clickable; click navigates within the middle pane.
- Frontmatter rendered as a compact key-value card at the top of the page (collapsible). Numeric fields like `support_count` and `curiosity_score` rendered with subtle progress bars or sparklines where it adds clarity.
- For pages under `wiki/behavioral/`, an **inline graph thumbnail** appears below the frontmatter showing this node's 1-hop neighborhood (~150px tall, rendered the same way as the live KG panel but static).
- For pages under `wiki/students/<Name>/incidents/`, the linked behavioral nodes are highlighted inline; clicking returns to `/` with that node selected.
- `log.md` and `index.md` scroll live as the agent writes new entries — the most-recent entry briefly highlights, then settles.

**Right pane — Backlinks + outgoing links.**
- "Linked from" section: every page in the wiki that links to the currently rendered page. Rendered as clickable list with one-line context snippets where possible.
- "Links out" section: every wikilink in the current page.
- "Raw markdown" toggle button: replaces the middle pane's rendered view with the raw markdown source, for debugging or curiosity.
- For behavioral nodes, an additional "Cross-student stats" mini-card: `support_count`, `students_count`, `curiosity_score` with its factor breakdown.

**Empty state:** if the wiki is brand new (only `schema.md`, `index.md`, `log.md` exist), the file tree shows them and the middle pane defaults to rendering `index.md` ("Welcome — the agent has not yet ingested any observations").

---

### 5.3 `/console` — Console

Diagnostic surface for "what is the agent literally doing right now?" Lower visual priority than `/`. Looks like a developer console, intentionally — text-dense, monospace where appropriate.

Three vertically stacked sections:

**Section 1 — Agent Status header (compact).** Current demo state (idle/running/resetting/stopped), current cycle stage, current student being processed, current note ID, last successful cycle timestamp. Updates live.

**Section 2 — Trace log (large, scrollable).** Every action the agent takes, append-only, newest at the bottom (or top — pick one and stick with it). Each line: timestamp, level (info/warn/error), category (loop/wiki/persona/curiosity/research), message. Auto-scroll toggle. Search/filter box.

**Section 3 — Curiosity Events stream (medium, side-by-side or below the trace).** Every time the curiosity gate is evaluated. Each row: node slug, score, factor breakdown (six small bars summing to the score), `triggered_research` boolean, papers fetched. This makes the "why did the agent decide to investigate" question debuggable in real time.

**No God Mode trigger here** — Console is read-only diagnostic.

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
- `Idle` — agent loop is not running. Live route's empty states are shown. God Mode is available but actions are queued until Start.
- `Running` — loop is active, notes are being generated. Live updates everywhere.
- `Resetting` — destructive restart in progress. Show a brief overlay "Resetting wiki and runtime state…" — recoverable.
- `Stopped` — explicitly halted. Like Idle but distinguishable ("Stopped" pill).

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
5. Find and use the "⚡ God Mode" affordance without prompting.
6. Switch to `/wiki` and immediately understand "the agent is literally writing markdown files right now."

If the design achieves those six things, the vision is satisfied. Everything else is taste.

---

## 12. Pointers for implementation context

- Architecture spec: `docs/superpowers/specs/2026-04-16-decoupled-kgs-and-llm-wiki-design.md`
- LLM-wiki paradigm origin: `llm-wiki.md`
- Project context: `CLAUDE.md`
- Original direction scratch: `Direction.txt`
- Current implementation status: `README.md`

This vision document and the spec must stay in sync. If the spec changes, this file changes. If a design decision is made in this file that the spec doesn't cover, the spec must be amended.

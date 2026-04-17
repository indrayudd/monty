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

**The primary visualization is a live force-directed network graph.** Both the cross-student behavioral KG (top panel on `/`) and the per-student subgraph (bottom panel, Graph tab) render as interactive node-link diagrams where nodes are colored by behavioral type, sized by observation count, and connected by typed edges. These graphs are the product's visual signature — they must look beautiful, dense, and alive. They are not supplementary charts; they ARE the interface.

Five concepts the visualizer must convey at all times:

1. **Two network graphs, one shared agent.** The behavioral graph (top) is anonymized and grows because of *all* students — nodes represent behavioral patterns (triggers, reactions, brain states, etc.) extracted from observations across every child, with NO student names visible. The student graph (bottom, Graph tab) shows one child's personal subgraph — the subset of behavioral nodes their observations touched, sized by their own touch count. They live in different visual regions; the link between them is *one-way and visible* (student → behavioral, never the reverse). Clicking a node in either graph cross-highlights it in the other.
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

## 5. Page-by-page specifications (redesign — locked from screens.pen)

> This section was updated 2026-04-17 from the Pencil design file `screens.pen` (5 frames). It is the canonical spec for the UI redesign. The existing implementation is being rewritten to match these designs.

### 5.1 `/` — Live (default landing)

The operations stage. Layout is a **two-column top zone + full-width bottom zone**.

```
┌──────────────────────────────────────────────────────────────────────┐
│  TOP APP BAR                                                          │
│  MONTY OPS  Live  Wiki  Console  God Mode    14:32:08 UTC  ● Running │
├────────────────────────────────────────────────┬─────────────────────┤
│                                                │  CYCLE STAGE        │
│   BEHAVIORAL KG (force-directed graph)         │  updating_profile   │
│   legend top-left · min-support top-right      │  > Mira Shah        │
│   ~540px tall · fill_container width           │                     │
│                                                │  STUDENT FOCUS      │
│                                                │  🟡 Mira Shah 3-4   │
│                                                │                     │
│                                                │  RESEARCH QUEUE     │
│                                                │  peer-material-grab │
│                                                │  transition-delay   │
│                                                │  (332px fixed)      │
├────────────────────────────────────────────────┴─────────────────────┤
│  ● STARTED ›  INGESTING ›  REASSESSING ›  UPDATING ›  ...  COMPLETE│
│                                                                      │
│  [M Mira] [A Arjun] [D Diya] [K Kiaan] [S Saanvi]   Timeline Graph │
│                                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ red │    │ yel │    │ grn │    │ red │    │ yel │               │
│  │ title   │ │ title   │ │ title   │ │ title   │ │ title   │       │
│  │ desc    │ │ desc    │ │ desc    │ │ desc    │ │ desc    │       │
│  │ chips   │ │ chips   │ │ chips   │ │ chips   │ │ chips   │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
└──────────────────────────────────────────────────────────────────────┘
```

#### 5.1.A Top Zone (two-column, ~540px tall)

**Left: Behavioral KG panel** (`fill_container` width, rounded, `surface-container-low`, padding 10).
- Force-directed graph (react-force-graph-2d) — **preserve existing physics tuning, node identity, structural-diff-only reheating, hover-only labels, ResizeObserver sizing**. Do NOT rewrite the graph internals.
- Legend chip top-left. Min-support control top-right with `{N}n · {N}e` counter.

**Right: Live Ops Column** (332px fixed, rounded, `surface-container-low`, padding 8). Three stacked sections:
1. **CYCLE STAGE** — bold stage name + student name (e.g., "updating_profile > Mira Shah") + keyword list. Polled from `/api/agent/status`.
2. **STUDENT FOCUS** — severity dot + name + age band of the student currently being processed.
3. **RESEARCH QUEUE** — list of recent research queries with paper titles, curiosity scores, status chips.

#### 5.1.B Stage Rail + Bottom Zone

**Stage Rail:** 7 labeled checkpoints (same behavior as current, preserve the component).

**Bottom Zone** contains persona chips + view tabs (Timeline | Graph | Research).

**Timeline cards redesigned:**
- Colored left border (4px) by severity (red/yellow/green).
- Title (bold white) — short behavior summary.
- Description (muted 11px) — 2-3 line excerpt.
- Behavioral type chips at bottom in node-type colors.

**Incident Detail Drawer:** now 280px wide (was 720px), absolute overlay. Shows severity + timestamp metadata, observation body, and behavioral node pills in type-specific colors (Setting=cyan, Antecedent=purple, Behavior=orange, Function=pink, Brain=blue, Response=green).

**Graph view and Research view:** preserve existing — no changes.

#### 5.1.C God Mode (now full-page route: `/god-mode`)

No longer a slide-in overlay. It is a **top-level route** accessible from the nav bar ("God Mode" link, gold when active). Two-column layout:

**Left (480px, gold top border):** story presets + 5 persona steering cards with gradient slider + inject buttons + interact dropdown.

**Right (fill):** live event feed (scrollable monospace log), curiosity weight sliders, manual research trigger with quick-action pills, demo lifecycle buttons (Start/Reset/Stop).

---

### 5.2 `/wiki` — Wiki Browser (redesigned)

Same three-pane structure but with: search bar in top nav, "FILES" header in left pane (300px), "GRAPH LINKS" header in right pane (320px) with backlinks + outgoing + legend sections, anonymization wall callout card on student pages, writing-activity cue, bottom route bar with action buttons.

---

### 5.3 `/console` — Console (redesigned)

- **3 KPI status cards** at top (cycle state, graph state, throughput) with colored left borders.
- **Structured trace log** with color-coded rows by category and filter chips.
- **Curiosity + Research Stream** section.
- **Bottom bar** with route nav + filter + PAUSE STREAM button.

See `screens.pen` frame `kTEh7` for exact layout.

---

_Old § 5 subsections removed — see redesign above._


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

## 10. Screen permutations (every possible view state)

The UI agent must design for every combination of route + tab + overlay. Each row below is a distinct screen state the user can reach.

### `/` Live route

| Bottom tab | Overlay | Description |
|---|---|---|
| **Timeline** (default) | none | Behavioral KG top, stage rail middle, horizontal scroll of incident cards bottom. This is the default landing view. |
| **Timeline** | **Incident Drawer** | Right slide-over (~720px) showing one incident's markdown: frontmatter card + Note + Interpretation + linked behavioral node pills. The live view behind the drawer continues updating. |
| **Timeline** | **God Mode** | Right slide-in (~420px, dark glass) with story presets, 5 persona steering cards (slider + inject buttons + interact dropdown), curiosity tuning, manual research trigger, demo lifecycle, reindex, purge. The behavioral KG and timeline behind the overlay continue updating (dimmed 30%). |
| **Graph** | none | Behavioral KG top, stage rail middle, per-student force-directed subgraph bottom (nodes this student touched, sized by student's touch count, edges from co-occurrence). |
| **Graph** | **God Mode** | Same as above but God Mode overlays the right side. |
| **Research** | none | Behavioral KG top, stage rail middle, scrollable list of OpenAlex papers fetched for this student bottom. |
| **Research** | **God Mode** | Same as above but God Mode overlays the right side. |

> Note: Incident Drawer and God Mode cannot both be open simultaneously — opening one closes the other (both use Esc to dismiss). The drawer only opens from Timeline view (clicking an incident card).

**Cross-highlight state:** clicking a behavioral node in the top panel highlights related incident cards in the Timeline view AND corresponding nodes in the student Graph view (if that tab is active). This is a global selection state, not per-tab.

### `/wiki` Wiki Browser route

| Selected page type | Description |
|---|---|
| **index.md** (default) | Auto-generated catalog with links grouped by: Setting Events, Antecedents, Behaviors, Functions, Brain States, Responses, Protective Factors, Students, Personas, Research Sources. |
| **log.md** | Append-only agent activity log. Newest entry at bottom. |
| **schema.md** | LLM instruction sheet (three layers, anonymization wall, frontmatter conventions, update protocol). |
| **behavioral node** (e.g., `behavioral/functions/desire-for-accuracy.md`) | Frontmatter card (slug, type, support_count, students_count, curiosity_score, _student_hashes) + `## Summary` + `## Evidence` (anonymized bullet list). Backlinks pane shows which index pages and student incident pages reference this node. |
| **behavioral edge** (e.g., `behavioral/_edges/antecedents--peer-disruption--triggers--behaviors--outburst.md`) | Frontmatter (src_slug, rel, dst_slug, support_count, students_count) + `## Evidence` bullets. |
| **student incident** (e.g., `students/Arjun_Nair/incidents/2026-04-17-1752-...md`) | Frontmatter (student, note_id, severity, behavioral_refs list, peers_present, educator, ingested_at) + `## Note` (original observation) + `## Interpretation` (agent's assessment). |
| **student profile** (`students/<Name>/profile.md`) | Current severity, trend, latest summary, patterns, suggestions. |
| **student timeline** (`students/<Name>/timeline.md`) | Chronological list of incident links (clickable, navigate within wiki). |
| **student patterns** (`students/<Name>/patterns.md`) | Behavioral refs ranked by frequency of occurrence for this student. |
| **student relationships** (`students/<Name>/relationships.md`) | Peers and educators seen in this student's incident frontmatter, ranked by co-occurrence count. |
| **persona** (`personas/<Name>.md`) | Frontmatter (name, age_band, temperament_axes, dysfunction_flavor, recurring_companions) + narrative prose. |
| **(no selection)** | Left pane shows file tree, middle pane shows "Select a file from the tree." |
| **page not found** | When a wikilink target doesn't exist: "⚠ page not found" with backlinks still showing which page referenced it. |

### `/console` Console route

| State | Description |
|---|---|
| **Active agent loop** | Agent Status card shows live JSON (current_stage, current_student, last_cycle_at, etc.). Curiosity Events stream shows factor-breakdown bars per event. |
| **Idle / no data** | Agent Status shows `mode: "idle"`. Curiosity Events shows "(no curiosity evaluations yet — the agent will start emitting these once nodes begin attracting attention)" |

### God Mode flow (how to use it)

1. Click the **God Mode** button (bottom-right of `/`).
2. Optionally click a **Story Preset** to coordinate all 5 personas at once (e.g., "Emergency Cascade" pushes all sliders high).
3. For fine control, adjust individual persona cards:
   - **Slider** (-1.0 to +1.0): shifts the persona's next LLM-generated note between calm/normalized and acutely dysregulated.
   - **Flavor dropdown**: changes how this persona decompensates (e.g., "explosive-then-shutdown" vs "scattered").
   - **Activity weight** (0–3): how often the streamer picks this persona. 0 = paused, 2 = double frequency.
   - **Inject buttons** (Neutral / Problematic / Emergency / Surprise): force the very next note for this persona to match that tone. A colored badge ("next: emergency") appears on the card until the streamer consumes it.
   - **Interact dropdown**: pick another persona; both students' next notes will be conditioned on a shared scene.
4. **Curiosity Tuning** (collapsed by default): adjust the 6 weights that determine when the agent gets "curious" enough to fetch research.
5. **Manual research trigger**: type a behavioral node slug, click Investigate to force a curiosity-gate trip.
6. **Start / Reset / Stop**: demo lifecycle controls.
7. **Reindex wiki**: triggers `POST /api/wiki/reindex` to rebuild the Postgres index from markdown files.
8. **Purge everything**: nuclear reset — truncates all tables, wipes wiki-generated content, preserves personas and skeleton. Requires confirmation. Page reloads.

---

## 11. What NOT to design

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

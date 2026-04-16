# Decoupled Knowledge Graphs + LLM-Wiki Paradigm — Design

**Date:** 2026-04-16
**Status:** Approved (awaiting implementation plan)
**Owner:** Indro

## Problem

Monty currently mixes two distinct kinds of knowledge in one substrate:

- **Per-student state** (profile snapshots, personality facets, alerts, literature) — individual, qualitative, must remain queryable down to the level of a single observation.
- **Cross-student behavioral patterns** — the actual reusable knowledge of how toddlers behave, what triggers what, what responses help. Today this is conflated with student-tagged rows in the `knowledge_graph` table and is not anonymized.

Three concrete problems fall out of that conflation:

1. The behavioral KG cannot accumulate value across students because it's stored per-student.
2. The student graph cannot be queried at the granularity the demo needs (specific incident details).
3. The static-corpus note generator (`scripts/generate_notes_corpus.py`) produces low-variety, fragment-permutation observations that don't justify the agent's reassessment work.

This design decouples the two graphs, applies the LLM-wiki paradigm (markdown-first, agent-maintained, persistent-and-compounding), and replaces the static corpus with a live persona-driven note generator.

## Vision document

A new `VISION.md` lives at the repo root (sibling of `README.md`, `CLAUDE.md`, `AGENTS.md`). It is *prescriptive* (here is what the UI must communicate) rather than descriptive (here is what we built). It is the artifact you hand to a UI-generation LLM. Sections:

1. What Monty is — autonomous, self-improving early-childhood support agent, llm-wiki paradigm.
2. The two knowledge graphs (decoupled) — what each is for, the wall between them.
3. Behavioral KG node schema — the 6-node taxonomy + edges, framed as design surfaces.
4. Per-student wiki structure — folder layout, what each page is for.
5. Live runtime story — note generated → ingested → behavioral KG node updates → student wiki updates → research-on-demand.
6. Persona control panel (God Mode) — what the operator can steer, what each control means.
7. Visualizer surfaces — three views (live linked panels, wiki browser, console) and the visual cues each must convey.
8. Design principles for UI — live-feel, anonymization legible, cross-graph linking obvious, agent-as-author visible.

`Direction.txt` is preserved as the original hand-written scratch. `VISION.md` becomes the canonical current vision.

## Architecture overview

Three substrates, mirroring the LLM-wiki three-layer model:

- **Raw / immutable inputs:** `wiki/personas/<Name>.md` (hand-authored persona docs), `ingested_observations` table (live note stream), `wiki/sources/openalex/<id>.md` (cached papers).
- **LLM-maintained wiki body:** `wiki/behavioral/` (anonymized cross-student KG) + `wiki/students/<Name>/` (per-student graphs).
- **Schema:** `wiki/schema.md` — the LLM's instruction sheet for how to write/maintain pages, frontmatter conventions, link rules, anonymization rules.

Source of truth = markdown in `wiki/`. Postgres is a derived index updated synchronously by the wiki-writer for fast graph queries. The Wiki Browser viz reads markdown directly.

```
personas/<Name>.md  ────►  persona_engine.py (LLM)  ────►  ingested_observations
                                                                  │
                                                                  ▼
                                                       self_improve.py (LLM)
                                                                  │
                                                                  ▼
                                                       wiki_writer.py
                                                       ├─► wiki/students/<Name>/incidents/<ts>.md
                                                       ├─► wiki/students/<Name>/{profile,patterns,...}.md
                                                       ├─► wiki/behavioral/<type>/<slug>.md  (anonymized)
                                                       └─► wiki/behavioral/_edges/<...>.md
                                                                  │
                                                                  ▼
                                                       wiki_indexer.py  ──►  Postgres index tables
                                                                  │
                                                       (curiosity gate trips when score ≥ 0.70)
                                                                  │
                                                                  ▼
                                                       kg_agent.py  ────►  wiki/sources/openalex/<id>.md
                                                                                │
                                                                                ▼
                                                                  wiki/students/<Name>/literature.md
```

## Behavioral KG — node schema (research-grounded)

Six node types, drawn from established early-childhood / behavioral-support frameworks (ABC model, SEAT functions, Conscious Discipline brain states, Pyramid Model). Optional 7th for slow-moving longitudinal layer.

| # | Node type | Definition | Source framework |
|---|---|---|---|
| 1 | **SettingEvent** | Distal/contextual condition that raises behavior probability | ABA setting events |
| 2 | **Antecedent** | Immediate proximal trigger right before the behavior | ABC model |
| 3 | **Behavior** | Observable action; includes positive Montessori work-cycle states | ABC model + Montessori normalization |
| 4 | **Function** | Hypothesized purpose: Sensory / Escape / Attention / Tangible | SEAT taxonomy |
| 5 | **BrainState** | Survival / Emotional / Executive + Montessori "normalized/concentrated" | Conscious Discipline |
| 6 | **Response** | Adult or environmental response that followed | Pyramid Model tiers / PBIS |
| 7 (optional) | **ProtectiveFactor** | DECA Initiative / Self-Regulation / Attachment | DECA framework |

**Typed edges:**
- `SettingEvent --predisposes--> Behavior`
- `SettingEvent --amplifies--> Antecedent`
- `Antecedent --triggers--> Behavior`
- `Behavior --serves--> Function`
- `Behavior --occurs_in--> BrainState`
- `BrainState --gates--> Function`
- `Response --follows--> Behavior`
- `Response --reinforces | extinguishes | co-regulates--> Behavior`
- `Behavior --evidences | undermines--> ProtectiveFactor`
- `Antecedent --recurs_with--> Antecedent` (cross-student reinforcement edge)

**Why these specifically:** ABC is the lingua franca every framework uses. Function is what makes cross-student reinforcement *interesting* — "escape" recurring across 4 students with different antecedents is a real signal. BrainState lets the same schema cover positive observations (Executive / Normalized work cycles), not just challenging behavior — important because half the corpus is neutral.

**Considered and dropped:** Pyramid Tier (it's a Response property), CLASS domains (adult quality, not child observation), Sensitive Period (too slow for per-observation), separate Emotion (collapsed into BrainState).

## Wiki layout

```
wiki/
  schema.md            ← LLM's instruction sheet
  index.md             ← catalog: every page with one-line summary, grouped by section
  log.md               ← chronological agent activity, append-only

  behavioral/          ← anonymized cross-student KG
    setting_events/<slug>.md
    antecedents/<slug>.md
    behaviors/<slug>.md
    functions/<slug>.md
    brain_states/<slug>.md
    responses/<slug>.md
    protective_factors/<slug>.md
    _edges/<src-slug>--<rel>--<dst-slug>.md
    _index.md          ← per-section catalog with reinforcement counts

  students/
    <Name>/
      profile.md                ← rolling summary, severity, trend, latest summary
      patterns.md               ← per-student emergent patterns
      protective_factors.md     ← DECA-style strengths
      relationships.md          ← peers and educators
      timeline.md               ← chronological index of incidents
      alerts.md                 ← open alerts
      literature.md             ← OpenAlex papers matched to this student
      log.md                    ← agent actions specific to this child
      incidents/
        YYYY-MM-DD-HHMM-<slug>.md   ← one page per ingested observation

  personas/            ← raw persona definitions (immutable input)
    <Name>.md

  sources/
    openalex/<openalex-id>.md
```

### Anonymization wall (hard rule, encoded in `schema.md` and enforced in code)

- Pages under `behavioral/` MUST NOT contain student names, ages, dates, educator names, peer names, or tokens identifying a specific child.
- Reinforcement is tracked as integer counts in frontmatter (`support_count`, `students_count`) — never as backlinks to student pages.
- Pages under `students/` MAY link OUT to `behavioral/` via wikilinks. Behavioral pages NEVER contain inverse links to student pages.
- Lint: every write to `wiki/behavioral/**` is scanned for known student names, educator names, and date regexes; rejected + logged on violation.

## Frontmatter contracts

**Behavioral node** (e.g., `wiki/behavioral/antecedents/peer-takes-material.md`):
```yaml
---
type: antecedent
slug: peer-takes-material
support_count: 7
students_count: 4
literature_refs: 1
curiosity_score: 0.62
last_curiosity_factors:
  novelty: 0.50
  recurrence_gap: 0.71
  cross_student: 0.88
  surprise: 0.30
  severity_weight: 0.65
  recency: 0.92
last_observed_at: 2026-04-16T10:32:14Z
last_research_fetched_at: null
created_at: 2026-04-12T08:11:09Z
related_nodes:
  - rel: triggers
    target: behaviors/drops-material-and-flees
  - rel: recurs_with
    target: setting_events/short-nap
---
```

**Edge file** (`wiki/behavioral/_edges/<src>--<rel>--<dst>.md`):
```yaml
---
src_slug: antecedents/peer-takes-material
rel: triggers
dst_slug: behaviors/drops-material-and-flees
support_count: 4
students_count: 3
first_observed_at: 2026-04-12T09:11:00Z
last_observed_at: 2026-04-16T10:32:14Z
---

## Evidence
- a 3-4 year old, peer takes pink-tower cylinder mid-carry
- a 4-5 year old, peer reaches for chosen practical-life material
- ...
```
Evidence stubs are anonymized prose; no names, no dates.

**Student incident** (`wiki/students/Mira_Shah/incidents/2026-04-16-1032-snack-denial.md`):
```yaml
---
student: Mira Shah
note_id: 318
severity: yellow
behavioral_refs:
  - behavioral/setting_events/short-nap
  - behavioral/antecedents/peer-takes-material
  - behavioral/behaviors/drops-material-and-flees
  - behavioral/functions/escape
  - behavioral/brain_states/emotional-flooded
  - behavioral/responses/co-regulation-breathing-card
peers_present: [Arjun Nair]
educator: Sajitha Kandathil
ingested_at: 2026-04-16T10:32:14Z
---

## Note
<original observation text>

## Interpretation
<LLM-generated interpretation referencing linked behavioral nodes>
```

## Live runtime: persona engine + agent loop

### Personas

Five personas hand-authored as `wiki/personas/<Name>.md`, immutable during a session. Frontmatter:
```yaml
---
name: Mira Shah
age_band: "3-4"
temperament_axes:
  sensory_reactivity: high
  social_orientation: peer-seeking
  frustration_tolerance: low
dysfunction_flavor: "explosive-then-shutdown"
recurring_companions: [Arjun Nair, Diya Malhotra]
---
```
Body: 1-2 paragraph persona narrative (what this child looks like in the room, what they love, what derails them).

### Persona engine (`notes_streamer/persona_engine.py`)

Endpoint: `POST /api/persona/next-note { student_name }` → returns one observation note matching the existing `Name: ...\n\n<body>` format.

LLM context per call:
1. Persona doc.
2. Student's last 3 incident pages (own narrative arc).
3. Last 3 incidents involving any `recurring_companions` (cross-student awareness).
4. Current control-panel state for that persona (functional ↔ dysfunctional dial position, flavor override, activity weight, any one-shot inject directive).
5. Cycle-counter / time-of-day token so notes don't all read like 10am.

Output is inserted into `ingested_observations` exactly like a streamed note from the static corpus today.

### Streamer (`notes_streamer/streamer.py`)

- Cadence: 2-8s randomized between insertions.
- On each tick, picks a persona weighted by activity-weight × random jitter, calls `next-note`, inserts result.
- Static-corpus mode (`scripts/generate_notes_corpus.py`) is removed.

### Agent loop (per cycle)

1. Persona engine produces a note.
2. Streamer inserts into `ingested_observations`.
3. `self_improve.py` cumulatively reassesses the affected student.
4. `wiki_writer` writes:
   - `students/<Name>/incidents/<ts>-<slug>.md` with `behavioral_refs` frontmatter.
   - Updates `students/<Name>/{profile,timeline,patterns,protective_factors,relationships,log}.md` rollups.
   - Resolves or creates behavioral nodes; updates edge `support_count`; appends anonymized evidence stubs; updates `behavioral/_index.md`.
   - Appends to `wiki/log.md` and `students/<Name>/log.md`.
5. `kg_agent.py` evaluates curiosity gate; fires research only when triggered. Paper pages written to `sources/openalex/<id>.md`, linked from `students/<Name>/literature.md`.
6. Postgres index updated incrementally inside the wiki-writer's same transaction.

Latency budget: persona note (~1s) + assessment (~1.5s) + wiki writes (~200ms) + curiosity-triggered research (~3s, async) → fits the 2-8s cadence.

## Curiosity gate (quantifiable)

Each behavioral node carries `curiosity_score: 0.0..1.0` recomputed on every touch. Six independent signals from wiki state:

| Signal | Formula | Why curious |
|---|---|---|
| novelty | `1 / (1 + literature_refs)` | Under-researched |
| recurrence_gap | `sigmoid(support_count − k·literature_refs)` with `k = 3` (default) | Recurring but unexplained |
| cross_student_emergence | `sigmoid(students_count − 2)` with `+0.20` one-time bump on the cycle that first crosses `students_count == 3`, decayed back over 6 hours | Just generalized |
| surprise | LLM judgment OR embedding distance between new incident text and node's current `## Summary` | Existing model is wrong |
| severity_weight | Max severity (red=1.0, yellow=0.5, green=0.0) of recent incidents touching node | Bias toward what hurts |
| recency | `exp(−hours_since_last_observed / τ)`, τ ≈ 24h | Settled-and-quiet nodes don't keep firing |

Composite:
```
curiosity = 0.20·novelty + 0.20·recurrence_gap + 0.20·cross_student
          + 0.15·surprise + 0.15·severity_weight + 0.10·recency
```

Weights tunable via `PATCH /api/runtime/curiosity-weights`, exposed as a collapsible "Tuning" pane in God Mode.

**Gate condition:**
```
fire_research(node) := curiosity(node) >= 0.70
                   AND (now − node.last_research_fetched_at) >= 30 minutes
```

Composes with existing triggers (thin patterns, red severity) as logical OR with cooldown.

**Persisted:** behavioral node frontmatter (`curiosity_score`, `last_research_fetched_at`, `last_curiosity_factors`) + a `curiosity_events` row in Postgres each time the gate trips.

## Visualizer (D — stacked panels + wiki browser + God Mode)

### Routes
- `/` — Live (default landing): stacked linked panels.
- `/wiki` — Wiki Browser: three-pane Obsidian-style.
- `/console` — existing trace + agent status, lightly refreshed with curiosity-events stream.

### `/` — Live, stacked linked panels

**Top panel: Behavioral KG (anonymized).**
- Force-directed graph. Node color = type. 6 distinct colors for the core types, plus a 7th muted color for `ProtectiveFactor` if/when it's enabled. Legend chip lives top-left of the panel.
- Node size = `support_count` (log-scaled, capped).
- Node halo = `curiosity_score` (yellow halo ≥0.5, pulsing red halo ≥0.7).
- When `fire_research` trips, animated arrow flies from node → paper icon spawning at periphery.
- Edge thickness = edge `support_count`. Edges below threshold (default 2) hidden; toggle in panel header.
- Edge color = relationship label.
- Click node: highlights 1-hop neighborhood; simultaneously highlights bottom-panel incident cards referencing this node.

**Bottom panel: Per-student incident timeline.**
- Student selector (5 chips, color-coded by current severity).
- Horizontal timeline of incident cards for selected student, newest right.
- Each card: timestamp, severity dot, behavior summary, color-chip row showing which behavioral node types this incident touched.
- Card click: slide-over drawer renders the markdown, shows linked behavioral nodes (clickable → highlights top panel), shows OpenAlex papers if any.
- Top-panel-node click → bottom cards referencing it pulse a thin border and scroll into view.

A slim **stage-rail strip** between the two panels: `waiting → ingesting → reassessing → updating_profile → enriching_knowledge → writing_alert → cycle_complete`, lit live as the loop progresses.

### `/wiki` — Wiki Browser

Three-pane Obsidian-style:
- **Left:** file tree mirroring `wiki/`. Files modified in last 30s pulse green; last 5min faintly highlighted.
- **Middle:** rendered markdown. Wikilinks clickable, navigate within pane. Frontmatter rendered as key-value card. Behavioral pages show inline 1-hop graph thumbnail. Incident pages highlight linked behavioral nodes.
- **Right:** backlinks ("Linked from"), outgoing links ("Links out"), raw markdown toggle.

### God Mode slide-in panel (on `/`)

Trigger: floating "⚡ God Mode" button bottom-right of live view. Slides in from the right (overlay, dim live view). Esc / backdrop click → slides out.

Contents top to bottom:
1. **Story preset row** — large pills: `Calm Morning` · `Escalating Mira` · `Group Conflict` · `Emergency Cascade` · `Reset to Baseline`.
2. **Per-persona steering cards** — one expanded card per child:
   - Header: name, age, current severity dot, "last note 4s ago" freshness.
   - Functional ↔ Dysfunctional slider (`-1.0` … `+1.0`).
   - Flavor dropdown (overrides persona doc default for session).
   - Activity weight (0 = pause, 1 = normal, 2 = double).
   - "Inject next note" quick-action row: `Neutral` · `Problematic` · `Emergency` · `Surprise`. One-shot directive for next generation only.
   - "Force interaction with..." mini-dropdown — pick another persona; next note for both conditioned on shared scene.
3. **Curiosity tuning** (collapsed default) — six weight sliders.
4. **Manual research trigger** — search box for any behavioral node, `Investigate` button forces curiosity gate trip.
5. **Demo lifecycle** — `Start / Reset / Stop`.

Visual language: dark glass panel, ~420px wide, full-height. Slider movement pulses a faint indicator from the card to the corresponding student chip in the bottom panel behind the overlay.

State persists in `agent_runtime_state.god_mode_overrides` JSONB.

## Postgres index tables

Replace deprecated `knowledge_graph` and `student_personality_graph` with:

```sql
behavioral_nodes (
  slug TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT,
  support_count INT DEFAULT 0,
  students_count INT DEFAULT 0,
  literature_refs INT DEFAULT 0,
  curiosity_score REAL DEFAULT 0,
  curiosity_factors JSONB,
  last_observed_at TIMESTAMPTZ,
  last_research_fetched_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  file_path TEXT NOT NULL,
  file_mtime TIMESTAMPTZ NOT NULL
)

behavioral_edges (
  src_slug TEXT NOT NULL,
  rel TEXT NOT NULL,
  dst_slug TEXT NOT NULL,
  support_count INT DEFAULT 0,
  students_count INT DEFAULT 0,
  first_observed_at TIMESTAMPTZ,
  last_observed_at TIMESTAMPTZ,
  file_path TEXT NOT NULL,
  PRIMARY KEY (src_slug, rel, dst_slug)
)

student_incidents (
  id BIGSERIAL PRIMARY KEY,
  student_name TEXT NOT NULL,
  note_id INT,
  severity TEXT,
  ingested_at TIMESTAMPTZ,
  file_path TEXT NOT NULL,
  file_mtime TIMESTAMPTZ NOT NULL,
  behavioral_ref_slugs TEXT[]
)

student_profiles_index (
  student_name TEXT PRIMARY KEY,
  current_severity TEXT,
  trend TEXT,
  incident_count INT,
  patterns_summary TEXT,
  file_path TEXT NOT NULL,
  file_mtime TIMESTAMPTZ NOT NULL
)

curiosity_events (
  id BIGSERIAL PRIMARY KEY,
  node_slug TEXT NOT NULL,
  fired_at TIMESTAMPTZ NOT NULL,
  curiosity_score REAL,
  factors JSONB,
  triggered_research BOOLEAN,
  paper_count INT
)
```

Kept unchanged: `ingested_observations`, `student_alerts`, `agent_actions`. `agent_runtime_state` gains a `god_mode_overrides JSONB` column.

### Reindex strategy

1. **Incremental (default):** wiki-writer is the only thing writing markdown; every write also calls `index_*(path)` synchronously. No watcher needed.
2. **Full rebuild:** `POST /api/wiki/reindex` walks `wiki/`, drops index tables, replays. Used after manual edits, after migration, in CI.

Wiki Browser serves markdown directly from disk, so index drift doesn't break the wiki view — only the graph view.

## API surface

**Kept (unchanged):** `GET /api/health` · `GET /api/flags[/{name}]` · `GET /api/insights/{name}` · `GET /api/suggestions/{name}` · `GET /api/literature/{name}` · `GET /api/alerts[/{name}]` · `GET /api/agent/status` · `POST /api/agent/run-cycle` · `GET /api/demo/overview` · `POST /api/demo/{start,reset,stop,bootstrap}` · `POST /api/kg/query`.

**Replaced:**
- `GET /api/personality-graph/{name}` → `GET /api/student-graph/{name}`
- `GET /api/knowledge-graph/{name}` → split into `GET /api/behavioral-graph` (anonymized cross-student) and `GET /api/student-graph/{name}/research` (per-student literature)

**New:**
- `POST /api/persona/next-note` — request next note for a named student.
- `GET /api/personas` — current persona state including God Mode overrides.
- `PATCH /api/personas/{name}` — slider, flavor, activity-weight.
- `POST /api/personas/{name}/inject` — `{flavor: "neutral|problematic|emergency|surprise"}` for next note only.
- `POST /api/personas/interact` — `{a, b, scene_hint}` for shared next-note context.
- `POST /api/curiosity/recompute/{slug}` — manual recomputation.
- `POST /api/curiosity/investigate/{slug}` — manual curiosity-gate fire (God Mode).
- `GET /api/curiosity/events` — recent curiosity events stream.
- `GET /api/wiki/tree` — file tree for Wiki Browser.
- `GET /api/wiki/page?path=...` — rendered markdown + frontmatter + computed backlinks.
- `POST /api/wiki/reindex` — full rebuild.
- `PATCH /api/runtime/curiosity-weights` — six weights for curiosity score.

KG agent server (`agents/server.py`, port 5001) stays — its `POST /api/kg-agent/query` is the path the wiki-writer calls when the curiosity gate trips.

## Service layout (Python)

New / changed files:

```
intelligence/api/services/
  wiki_writer.py          ← NEW
  wiki_indexer.py         ← NEW
  curiosity.py            ← NEW
  self_improve.py         ← CHANGED: emits incident pages via wiki_writer
  kg_agent.py             ← CHANGED: writes paper pages to wiki/sources/openalex/, updates literature_refs
  ghost_client.py         ← CHANGED: drops legacy graph tables, adds new index tables, runtime overrides

notes_streamer/
  persona_engine.py       ← NEW (called from intelligence API; lives here because notes are this layer's concern)
  streamer.py             ← CHANGED: pulls from persona engine instead of static .txt files

scripts/
  migrate_to_wiki.py      ← NEW: one-shot migration
  generate_notes_corpus.py ← REMOVED
```

## Implementation phasing (six phases, demo never breaks)

**Phase 0 — Scaffolding (additive, no behavior change).**
- `wiki/` skeleton: `schema.md`, `index.md`, `log.md`, empty subfolders, 5 hand-authored `personas/<Name>.md`.
- Stub `wiki_writer.py`, `wiki_indexer.py`, `curiosity.py`, `persona_engine.py` with public interfaces only.
- New Postgres index tables alongside legacy ones — both populated, no reads switched yet.
- New API endpoints returning empty payloads (so new viz can be developed in parallel).
- **Validation:** `python3 -m py_compile` clean; existing demo still runs unchanged.

**Phase 1 — Persona engine.**
- `persona_engine.py` with full LLM context (persona + own incidents + companion incidents + slider state + cycle token).
- `POST /api/persona/next-note`, `GET/PATCH /api/personas`, `POST /api/personas/{name}/inject`, `POST /api/personas/interact`.
- Modify `streamer.py` to pull from persona engine on 2-8s tick.
- Minimal God Mode panel (sliders + inject + activity + story presets).
- **Validation:** start demo → 5 distinct persona voices in `ingested_observations`; slider biases next note within 1 cycle; inject overrides exactly once.

**Phase 2 — Wiki writer.**
- `wiki_writer.py`: incident page write, behavioral node create/update, edge update with anonymized evidence stub, student rollup pages.
- Anonymization lint scans every behavioral write for known student names + dates + educator names.
- Wire `self_improve.py` to call `wiki_writer` instead of writing legacy graph tables.
- `wiki_indexer.py`: synchronous incremental indexing on every write; `POST /api/wiki/reindex` for full rebuild.
- **Validation:** ingest a note → `students/<name>/incidents/<ts>.md` exists with frontmatter `behavioral_refs`; matching behavioral files exist or have updated `support_count`; anonymization lint passes; index tables match filesystem.

**Phase 3 — Curiosity gate.**
- `curiosity.py`: 6-signal formula, recompute on every node touch, frontmatter + index update.
- `kg_agent.py`: curiosity as third trigger (OR with thin-patterns and red-severity), 30-min per-node cooldown.
- Paper pages written to `sources/openalex/<id>.md`, linked from `students/<name>/literature.md`.
- `POST /api/curiosity/investigate/{slug}` for God Mode.
- `GET /api/curiosity/events` stream.
- `PATCH /api/runtime/curiosity-weights`.
- **Validation:** forced investigate → curiosity event row written; curiosity scores update visibly in node frontmatter.

**Phase 4 — Visualizer rebuild.**
- New `/` route: stacked linked panels with cross-highlighting, curiosity glow, research-fire animation.
- New `/wiki` route: three-pane browser with file tree (live-pulse), rendered page, backlinks.
- God Mode slide-in panel finalized.
- `/console` refresh with curiosity events stream.
- **Validation:** click behavioral node → student incidents highlight; click incident card → drawer renders markdown; God Mode slider visibly lands in next cycle; curiosity gate trip animates a paper into existence.

**Phase 5 — Migration & cleanup.**
- Run `scripts/migrate_to_wiki.py` once.
- Drop `knowledge_graph` and `student_personality_graph` tables.
- Remove `scripts/generate_notes_corpus.py`.
- Update `CLAUDE.md`, `README.md`, write final `VISION.md`.
- **Validation:** clean cold start with only `wiki/personas/` as input; legacy tables gone; build commands clean.

### Phase parallelism (for subagent dispatch)

- Phase 1 (persona engine) and Phase 2 (wiki writer) share no files — fully parallel.
- Phase 4's `/wiki` route is parallelizable with Phase 4's `/` route — different components.
- Phase 4 viz can be built against stub Phase 0 endpoints in parallel with Phases 1-3 backend work.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| LLM latency breaks 2-8s cadence | Independent LLM calls (persona, assessment, curiosity-surprise) parallel. 1.5s timeout each → fall back to cached/heuristic. Streamer cadence widens to 4-12s if observed latency stays high. |
| Filesystem races on the same node | One `WikiWriter` singleton per process. Per-node `asyncio.Lock`. Edge evidence sections append-only. |
| Anonymization leak into behavioral pages | Lint pass on every behavioral write: scans for known student names, dates, educator names; rejects + logs to `wiki/log.md` and surfaces in `/console`. CI test exercises this. |
| Demo fragility from LLM unpredictability | God Mode `Inject` and `Interact` give narrative override at any moment. Story presets give one-click recovery. |
| LLM cost at demo cadence | ~225-900 GPT-4o-mini calls per 30-min demo. Acceptable; flagged. |
| Migration loses fidelity | `migrate_to_wiki.py` one-shot, idempotent on re-run, dry-run flag, prints diffs before writing. Legacy tables dropped only after explicit confirmation. |
| Wiki growing too large for `index.md` | At 5 students × 30-min demos × ~50 incidents = ~250 incident pages + ~100 behavioral nodes — well under llm-wiki's "moderate scale". Index is sufficient. |

## Out of scope (this iteration)

- Editing markdown via Wiki Browser (read-only).
- Persona authoring UI (text-edit `wiki/personas/*.md` directly).
- Embedding/vector search over the wiki (`index.md` is sufficient at this scale).
- Auth, multi-tenant, account model.
- Slide-deck / PDF export from wiki.
- Replacing the `frontend/` dashboard (work is all in `backend_visualizer/`; dashboard may show stale data until reads are repointed in a follow-up).

## Success criteria

1. Cold start with only `wiki/personas/*.md` and an empty `wiki/` body produces a self-extending wiki within 5 minutes of demo time.
2. `wiki/behavioral/` contains zero student names, educator names, or dates after a full demo run (lint exit code 0).
3. Cross-student reinforcement is visible: at least one behavioral node ends a 30-min demo with `students_count >= 3` and `support_count >= 5`.
4. Curiosity gate fires at least once during the demo without manual intervention, producing a new `wiki/sources/openalex/<id>.md`.
5. God Mode `Inject Emergency` button on any persona produces an emergency-flavored note within one cycle.
6. Wiki Browser shows file-tree pulses synced to wiki-writer activity (visible "agent is writing live" feel).
7. `VISION.md` is sufficient for an external UI-generation LLM to produce a coherent dashboard mockup without reading code.
